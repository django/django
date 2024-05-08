from __future__ import annotations

import contextvars
import queue as stdlib_queue
import re
import sys
import threading
import time
import weakref
from functools import partial
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Awaitable,
    Callable,
    List,
    NoReturn,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import pytest
import sniffio

from .. import (
    CancelScope,
    CapacityLimiter,
    Event,
    TrioDeprecationWarning,
    _core,
    fail_after,
    move_on_after,
    sleep,
    sleep_forever,
)
from .._core._tests.test_ki import ki_self
from .._core._tests.tutil import slow
from .._threads import (
    active_thread_count,
    current_default_thread_limiter,
    from_thread_check_cancelled,
    from_thread_run,
    from_thread_run_sync,
    to_thread_run_sync,
    wait_all_threads_completed,
)
from ..testing import wait_all_tasks_blocked

if TYPE_CHECKING:
    from outcome import Outcome

    from ..lowlevel import Task

RecordType = List[Tuple[str, Union[threading.Thread, Type[BaseException]]]]
T = TypeVar("T")


async def test_do_in_trio_thread() -> None:
    trio_thread = threading.current_thread()

    async def check_case(
        do_in_trio_thread: Callable[..., threading.Thread],
        fn: Callable[..., T | Awaitable[T]],
        expected: tuple[str, T],
        trio_token: _core.TrioToken | None = None,
    ) -> None:
        record: RecordType = []

        def threadfn() -> None:
            try:
                record.append(("start", threading.current_thread()))
                x = do_in_trio_thread(fn, record, trio_token=trio_token)
                record.append(("got", x))
            except BaseException as exc:
                print(exc)
                record.append(("error", type(exc)))

        child_thread = threading.Thread(target=threadfn, daemon=True)
        child_thread.start()
        while child_thread.is_alive():
            print("yawn")
            await sleep(0.01)
        assert record == [("start", child_thread), ("f", trio_thread), expected]

    token = _core.current_trio_token()

    def f1(record: RecordType) -> int:
        assert not _core.currently_ki_protected()
        record.append(("f", threading.current_thread()))
        return 2

    await check_case(from_thread_run_sync, f1, ("got", 2), trio_token=token)

    def f2(record: RecordType) -> NoReturn:
        assert not _core.currently_ki_protected()
        record.append(("f", threading.current_thread()))
        raise ValueError

    await check_case(from_thread_run_sync, f2, ("error", ValueError), trio_token=token)

    async def f3(record: RecordType) -> int:
        assert not _core.currently_ki_protected()
        await _core.checkpoint()
        record.append(("f", threading.current_thread()))
        return 3

    await check_case(from_thread_run, f3, ("got", 3), trio_token=token)

    async def f4(record: RecordType) -> NoReturn:
        assert not _core.currently_ki_protected()
        await _core.checkpoint()
        record.append(("f", threading.current_thread()))
        raise KeyError

    await check_case(from_thread_run, f4, ("error", KeyError), trio_token=token)


async def test_do_in_trio_thread_from_trio_thread() -> None:
    with pytest.raises(RuntimeError):
        from_thread_run_sync(lambda: None)  # pragma: no branch

    async def foo() -> None:  # pragma: no cover
        pass

    with pytest.raises(RuntimeError):
        from_thread_run(foo)


def test_run_in_trio_thread_ki() -> None:
    # if we get a control-C during a run_in_trio_thread, then it propagates
    # back to the caller (slick!)
    record = set()

    async def check_run_in_trio_thread() -> None:
        token = _core.current_trio_token()

        def trio_thread_fn() -> None:
            print("in Trio thread")
            assert not _core.currently_ki_protected()
            print("ki_self")
            try:
                ki_self()
            finally:
                import sys

                print("finally", sys.exc_info())

        async def trio_thread_afn() -> None:
            trio_thread_fn()

        def external_thread_fn() -> None:
            try:
                print("running")
                from_thread_run_sync(trio_thread_fn, trio_token=token)
            except KeyboardInterrupt:
                print("ok1")
                record.add("ok1")
            try:
                from_thread_run(trio_thread_afn, trio_token=token)
            except KeyboardInterrupt:
                print("ok2")
                record.add("ok2")

        thread = threading.Thread(target=external_thread_fn)
        thread.start()
        print("waiting")
        while thread.is_alive():
            await sleep(0.01)
        print("waited, joining")
        thread.join()
        print("done")

    _core.run(check_run_in_trio_thread)
    assert record == {"ok1", "ok2"}


def test_await_in_trio_thread_while_main_exits() -> None:
    record = []
    ev = Event()

    async def trio_fn() -> None:
        record.append("sleeping")
        ev.set()
        await _core.wait_task_rescheduled(lambda _: _core.Abort.SUCCEEDED)

    def thread_fn(token: _core.TrioToken) -> None:
        try:
            from_thread_run(trio_fn, trio_token=token)
        except _core.Cancelled:
            record.append("cancelled")

    async def main() -> threading.Thread:
        token = _core.current_trio_token()
        thread = threading.Thread(target=thread_fn, args=(token,))
        thread.start()
        await ev.wait()
        assert record == ["sleeping"]
        return thread

    thread = _core.run(main)
    thread.join()
    assert record == ["sleeping", "cancelled"]


async def test_named_thread() -> None:
    ending = " from trio._tests.test_threads.test_named_thread"

    def inner(name: str = "inner" + ending) -> threading.Thread:
        assert threading.current_thread().name == name
        return threading.current_thread()

    def f(name: str) -> Callable[[None], threading.Thread]:
        return partial(inner, name)

    # test defaults
    await to_thread_run_sync(inner)
    await to_thread_run_sync(inner, thread_name=None)

    # functools.partial doesn't have __name__, so defaults to None
    await to_thread_run_sync(f("None" + ending))

    # test that you can set a custom name, and that it's reset afterwards
    async def test_thread_name(name: str) -> None:
        thread = await to_thread_run_sync(f(name), thread_name=name)
        assert re.match("Trio thread [0-9]*", thread.name)

    await test_thread_name("")
    await test_thread_name("fobiedoo")
    await test_thread_name("name_longer_than_15_characters")

    await test_thread_name("💙")


def _get_thread_name(ident: int | None = None) -> str | None:
    import ctypes
    import ctypes.util

    libpthread_path = ctypes.util.find_library("pthread")
    if not libpthread_path:
        # musl includes pthread functions directly in libc.so
        # (but note that find_library("c") does not work on musl,
        #  see: https://github.com/python/cpython/issues/65821)
        # so try that library instead
        # if it doesn't exist, CDLL() will fail below
        libpthread_path = "libc.so"
    try:
        libpthread = ctypes.CDLL(libpthread_path)
    except Exception:
        print(f"no pthread on {sys.platform}")
        return None

    pthread_getname_np = getattr(libpthread, "pthread_getname_np", None)

    # this should never fail on any platforms afaik
    assert pthread_getname_np

    # thankfully getname signature doesn't differ between platforms
    pthread_getname_np.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    pthread_getname_np.restype = ctypes.c_int

    name_buffer = ctypes.create_string_buffer(b"", size=16)
    if ident is None:
        ident = threading.get_ident()
    assert pthread_getname_np(ident, name_buffer, 16) == 0
    try:
        return name_buffer.value.decode()
    except UnicodeDecodeError as e:  # pragma: no cover
        # used for debugging when testing via CI
        pytest.fail(f"value: {name_buffer.value!r}, exception: {e}")


# test os thread naming
# this depends on pthread being available, which is the case on 99.9% of linux machines
# and most mac machines. So unless the platform is linux it will just skip
# in case it fails to fetch the os thread name.
async def test_named_thread_os() -> None:
    def inner(name: str) -> threading.Thread:
        os_thread_name = _get_thread_name()
        if os_thread_name is None and sys.platform != "linux":
            pytest.skip(f"no pthread OS support on {sys.platform}")
        else:
            assert os_thread_name == name[:15]

        return threading.current_thread()

    def f(name: str) -> Callable[[None], threading.Thread]:
        return partial(inner, name)

    # test defaults
    default = "None from trio._tests.test_threads.test_named_thread"
    await to_thread_run_sync(f(default))
    await to_thread_run_sync(f(default), thread_name=None)

    # test that you can set a custom name, and that it's reset afterwards
    async def test_thread_name(name: str, expected: str | None = None) -> None:
        if expected is None:
            expected = name
        thread = await to_thread_run_sync(f(expected), thread_name=name)

        os_thread_name = _get_thread_name(thread.ident)
        assert os_thread_name is not None, "should skip earlier if this is the case"
        assert re.match("Trio thread [0-9]*", os_thread_name)

    await test_thread_name("")
    await test_thread_name("fobiedoo")
    await test_thread_name("name_longer_than_15_characters")

    await test_thread_name("💙", expected="?")


async def test_has_pthread_setname_np() -> None:
    from trio._core._thread_cache import get_os_thread_name_func

    k = get_os_thread_name_func()
    if k is None:
        assert sys.platform != "linux"
        pytest.skip(f"no pthread_setname_np on {sys.platform}")


async def test_run_in_worker_thread() -> None:
    trio_thread = threading.current_thread()

    def f(x: T) -> tuple[T, threading.Thread]:
        return (x, threading.current_thread())

    x, child_thread = await to_thread_run_sync(f, 1)
    assert x == 1
    assert child_thread != trio_thread

    def g() -> NoReturn:
        raise ValueError(threading.current_thread())

    with pytest.raises(
        ValueError, match=r"^<Thread\(Trio thread \d+, started daemon \d+\)>$"
    ) as excinfo:
        await to_thread_run_sync(g)
    print(excinfo.value.args)
    assert excinfo.value.args[0] != trio_thread


async def test_run_in_worker_thread_cancellation() -> None:
    register: list[str | None] = [None]

    def f(q: stdlib_queue.Queue[str]) -> None:
        # Make the thread block for a controlled amount of time
        register[0] = "blocking"
        q.get()
        register[0] = "finished"

    async def child(q: stdlib_queue.Queue[None], abandon_on_cancel: bool) -> None:
        record.append("start")
        try:
            return await to_thread_run_sync(f, q, abandon_on_cancel=abandon_on_cancel)
        finally:
            record.append("exit")

    record: list[str] = []
    q: stdlib_queue.Queue[None] = stdlib_queue.Queue()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, q, True)
        # Give it a chance to get started. (This is important because
        # to_thread_run_sync does a checkpoint_if_cancelled before
        # blocking on the thread, and we don't want to trigger this.)
        await wait_all_tasks_blocked()
        assert record == ["start"]
        # Then cancel it.
        nursery.cancel_scope.cancel()
    # The task exited, but the thread didn't:
    assert register[0] != "finished"
    # Put the thread out of its misery:
    q.put(None)
    while register[0] != "finished":
        time.sleep(0.01)  # noqa: ASYNC101  # Need to wait for OS thread

    # This one can't be cancelled
    record = []
    register[0] = None
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, q, False)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
        with _core.CancelScope(shield=True):
            for _ in range(10):
                await _core.checkpoint()
        # It's still running
        assert record == ["start"]
        q.put(None)
        # Now it exits

    # But if we cancel *before* it enters, the entry is itself a cancellation
    # point
    with _core.CancelScope() as scope:
        scope.cancel()
        await child(q, False)
    assert scope.cancelled_caught


# Make sure that if trio.run exits, and then the thread finishes, then that's
# handled gracefully. (Requires that the thread result machinery be prepared
# for call_soon to raise RunFinishedError.)
def test_run_in_worker_thread_abandoned(
    capfd: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(_core._thread_cache, "IDLE_TIMEOUT", 0.01)

    q1: stdlib_queue.Queue[None] = stdlib_queue.Queue()
    q2: stdlib_queue.Queue[threading.Thread] = stdlib_queue.Queue()

    def thread_fn() -> None:
        q1.get()
        q2.put(threading.current_thread())

    async def main() -> None:
        async def child() -> None:
            await to_thread_run_sync(thread_fn, abandon_on_cancel=True)

        async with _core.open_nursery() as nursery:
            nursery.start_soon(child)
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    _core.run(main)

    q1.put(None)
    # This makes sure:
    # - the thread actually ran
    # - that thread has finished before we check for its output
    thread = q2.get()
    while thread.is_alive():
        time.sleep(0.01)  # pragma: no cover

    # Make sure we don't have a "Exception in thread ..." dump to the console:
    out, err = capfd.readouterr()
    assert "Exception in thread" not in out
    assert "Exception in thread" not in err


@pytest.mark.parametrize("MAX", [3, 5, 10])
@pytest.mark.parametrize("cancel", [False, True])
@pytest.mark.parametrize("use_default_limiter", [False, True])
async def test_run_in_worker_thread_limiter(
    MAX: int, cancel: bool, use_default_limiter: bool
) -> None:
    # This test is a bit tricky. The goal is to make sure that if we set
    # limiter=CapacityLimiter(MAX), then in fact only MAX threads are ever
    # running at a time, even if there are more concurrent calls to
    # to_thread_run_sync, and even if some of those are cancelled. And
    # also to make sure that the default limiter actually limits.
    COUNT = 2 * MAX
    gate = threading.Event()
    lock = threading.Lock()
    if use_default_limiter:
        c = current_default_thread_limiter()
        orig_total_tokens = c.total_tokens
        c.total_tokens = MAX
        limiter_arg = None
    else:
        c = CapacityLimiter(MAX)
        orig_total_tokens = MAX
        limiter_arg = c
    try:
        # We used to use regular variables and 'nonlocal' here, but it turns
        # out that it's not safe to assign to closed-over variables that are
        # visible in multiple threads, at least as of CPython 3.10 and PyPy
        # 7.3:
        #
        #   https://bugs.python.org/issue30744
        #   https://bitbucket.org/pypy/pypy/issues/2591/
        #
        # Mutating them in-place is OK though (as long as you use proper
        # locking etc.).
        class state:
            ran: int
            high_water: int
            running: int
            parked: int

        state.ran = 0
        state.high_water = 0
        state.running = 0
        state.parked = 0

        token = _core.current_trio_token()

        def thread_fn(cancel_scope: CancelScope) -> None:
            print("thread_fn start")
            from_thread_run_sync(cancel_scope.cancel, trio_token=token)
            with lock:
                state.ran += 1
                state.running += 1
                state.high_water = max(state.high_water, state.running)
                # The Trio thread below watches this value and uses it as a
                # signal that all the stats calculations have finished.
                state.parked += 1
            gate.wait()
            with lock:
                state.parked -= 1
                state.running -= 1
            print("thread_fn exiting")

        async def run_thread(event: Event) -> None:
            with _core.CancelScope() as cancel_scope:
                await to_thread_run_sync(
                    thread_fn,
                    cancel_scope,
                    abandon_on_cancel=cancel,
                    limiter=limiter_arg,
                )
            print("run_thread finished, cancelled:", cancel_scope.cancelled_caught)
            event.set()

        async with _core.open_nursery() as nursery:
            print("spawning")
            events = []
            for _ in range(COUNT):
                events.append(Event())
                nursery.start_soon(run_thread, events[-1])
                await wait_all_tasks_blocked()
            # In the cancel case, we in particular want to make sure that the
            # cancelled tasks don't release the semaphore. So let's wait until
            # at least one of them has exited, and that everything has had a
            # chance to settle down from this, before we check that everyone
            # who's supposed to be waiting is waiting:
            if cancel:
                print("waiting for first cancellation to clear")
                await events[0].wait()
                await wait_all_tasks_blocked()
            # Then wait until the first MAX threads are parked in gate.wait(),
            # and the next MAX threads are parked on the semaphore, to make
            # sure no-one is sneaking past, and to make sure the high_water
            # check below won't fail due to scheduling issues. (It could still
            # fail if too many threads are let through here.)
            while state.parked != MAX or c.statistics().tasks_waiting != MAX:
                await sleep(0.01)  # pragma: no cover
            # Then release the threads
            gate.set()

        assert state.high_water == MAX

        if cancel:
            # Some threads might still be running; need to wait to them to
            # finish before checking that all threads ran. We can do this
            # using the CapacityLimiter.
            while c.borrowed_tokens > 0:
                await sleep(0.01)  # pragma: no cover

        assert state.ran == COUNT
        assert state.running == 0
    finally:
        c.total_tokens = orig_total_tokens


async def test_run_in_worker_thread_custom_limiter() -> None:
    # Basically just checking that we only call acquire_on_behalf_of and
    # release_on_behalf_of, since that's part of our documented API.
    record = []

    class CustomLimiter:
        async def acquire_on_behalf_of(self, borrower: Task) -> None:
            record.append("acquire")
            self._borrower = borrower

        def release_on_behalf_of(self, borrower: Task) -> None:
            record.append("release")
            assert borrower == self._borrower

    # TODO: should CapacityLimiter have an abc or protocol so users can modify it?
    # because currently it's `final` so writing code like this is not allowed.
    await to_thread_run_sync(lambda: None, limiter=CustomLimiter())  # type: ignore[call-overload]
    assert record == ["acquire", "release"]


async def test_run_in_worker_thread_limiter_error() -> None:
    record = []

    class BadCapacityLimiter:
        async def acquire_on_behalf_of(self, borrower: Task) -> None:
            record.append("acquire")

        def release_on_behalf_of(self, borrower: Task) -> NoReturn:
            record.append("release")
            raise ValueError("release on behalf")

    bs = BadCapacityLimiter()

    with pytest.raises(ValueError, match="^release on behalf$") as excinfo:
        await to_thread_run_sync(lambda: None, limiter=bs)  # type: ignore[call-overload]
    assert excinfo.value.__context__ is None
    assert record == ["acquire", "release"]
    record = []

    # If the original function raised an error, then the semaphore error
    # chains with it
    d: dict[str, object] = {}
    with pytest.raises(ValueError, match="^release on behalf$") as excinfo:
        await to_thread_run_sync(lambda: d["x"], limiter=bs)  # type: ignore[call-overload]
    assert isinstance(excinfo.value.__context__, KeyError)
    assert record == ["acquire", "release"]


async def test_run_in_worker_thread_fail_to_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Test the unlikely but possible case where trying to spawn a thread fails
    def bad_start(self: object, *args: object) -> NoReturn:
        raise RuntimeError("the engines canna take it captain")

    monkeypatch.setattr(_core._thread_cache.ThreadCache, "start_thread_soon", bad_start)

    limiter = current_default_thread_limiter()
    assert limiter.borrowed_tokens == 0

    # We get an appropriate error, and the limiter is cleanly released
    with pytest.raises(RuntimeError) as excinfo:
        await to_thread_run_sync(lambda: None)  # pragma: no cover
    assert "engines" in str(excinfo.value)

    assert limiter.borrowed_tokens == 0


async def test_trio_to_thread_run_sync_token() -> None:
    # Test that to_thread_run_sync automatically injects the current trio token
    # into a spawned thread
    def thread_fn() -> _core.TrioToken:
        callee_token = from_thread_run_sync(_core.current_trio_token)
        return callee_token

    caller_token = _core.current_trio_token()
    callee_token = await to_thread_run_sync(thread_fn)
    assert callee_token == caller_token


async def test_trio_to_thread_run_sync_expected_error() -> None:
    # Test correct error when passed async function
    async def async_fn() -> None:  # pragma: no cover
        pass

    with pytest.raises(TypeError, match="expected a sync function"):
        await to_thread_run_sync(async_fn)  # type: ignore[unused-coroutine]


trio_test_contextvar: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trio_test_contextvar"
)


async def test_trio_to_thread_run_sync_contextvars() -> None:
    trio_thread = threading.current_thread()
    trio_test_contextvar.set("main")

    def f() -> tuple[str, threading.Thread]:
        value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (value, threading.current_thread())

    value, child_thread = await to_thread_run_sync(f)
    assert value == "main"
    assert child_thread != trio_thread

    def g() -> tuple[str, str, threading.Thread]:
        parent_value = trio_test_contextvar.get()
        trio_test_contextvar.set("worker")
        inner_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (
            parent_value,
            inner_value,
            threading.current_thread(),
        )

    parent_value, inner_value, child_thread = await to_thread_run_sync(g)
    current_value = trio_test_contextvar.get()
    assert parent_value == "main"
    assert inner_value == "worker"
    assert current_value == "main", (
        "The contextvar value set on the worker would not propagate back to the main"
        " thread"
    )
    assert sniffio.current_async_library() == "trio"


async def test_trio_from_thread_run_sync() -> None:
    # Test that to_thread_run_sync correctly "hands off" the trio token to
    # trio.from_thread.run_sync()
    def thread_fn_1() -> float:
        trio_time = from_thread_run_sync(_core.current_time)
        return trio_time

    trio_time = await to_thread_run_sync(thread_fn_1)
    assert isinstance(trio_time, float)

    # Test correct error when passed async function
    async def async_fn() -> None:  # pragma: no cover
        pass

    def thread_fn_2() -> None:
        from_thread_run_sync(async_fn)  # type: ignore[unused-coroutine]

    with pytest.raises(TypeError, match="expected a synchronous function"):
        await to_thread_run_sync(thread_fn_2)


async def test_trio_from_thread_run() -> None:
    # Test that to_thread_run_sync correctly "hands off" the trio token to
    # trio.from_thread.run()
    record = []

    async def back_in_trio_fn() -> None:
        _core.current_time()  # implicitly checks that we're in trio
        record.append("back in trio")

    def thread_fn() -> None:
        record.append("in thread")
        from_thread_run(back_in_trio_fn)

    await to_thread_run_sync(thread_fn)
    assert record == ["in thread", "back in trio"]

    # Test correct error when passed sync function
    def sync_fn() -> None:  # pragma: no cover
        pass

    with pytest.raises(TypeError, match="appears to be synchronous"):
        await to_thread_run_sync(from_thread_run, sync_fn)


async def test_trio_from_thread_token() -> None:
    # Test that to_thread_run_sync and spawned trio.from_thread.run_sync()
    # share the same Trio token
    def thread_fn() -> _core.TrioToken:
        callee_token = from_thread_run_sync(_core.current_trio_token)
        return callee_token

    caller_token = _core.current_trio_token()
    callee_token = await to_thread_run_sync(thread_fn)
    assert callee_token == caller_token


async def test_trio_from_thread_token_kwarg() -> None:
    # Test that to_thread_run_sync and spawned trio.from_thread.run_sync() can
    # use an explicitly defined token
    def thread_fn(token: _core.TrioToken) -> _core.TrioToken:
        callee_token = from_thread_run_sync(_core.current_trio_token, trio_token=token)
        return callee_token

    caller_token = _core.current_trio_token()
    callee_token = await to_thread_run_sync(thread_fn, caller_token)
    assert callee_token == caller_token


async def test_from_thread_no_token() -> None:
    # Test that a "raw call" to trio.from_thread.run() fails because no token
    # has been provided

    with pytest.raises(RuntimeError):
        from_thread_run_sync(_core.current_time)


async def test_trio_from_thread_run_sync_contextvars() -> None:
    trio_test_contextvar.set("main")

    def thread_fn() -> tuple[str, str, str, str, str]:
        thread_parent_value = trio_test_contextvar.get()
        trio_test_contextvar.set("worker")
        thread_current_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()

        def back_in_main() -> tuple[str, str]:
            back_parent_value = trio_test_contextvar.get()
            trio_test_contextvar.set("back_in_main")
            back_current_value = trio_test_contextvar.get()
            assert sniffio.current_async_library() == "trio"
            return back_parent_value, back_current_value

        back_parent_value, back_current_value = from_thread_run_sync(back_in_main)
        thread_after_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (
            thread_parent_value,
            thread_current_value,
            thread_after_value,
            back_parent_value,
            back_current_value,
        )

    (
        thread_parent_value,
        thread_current_value,
        thread_after_value,
        back_parent_value,
        back_current_value,
    ) = await to_thread_run_sync(thread_fn)
    current_value = trio_test_contextvar.get()
    assert current_value == thread_parent_value == "main"
    assert thread_current_value == back_parent_value == thread_after_value == "worker"
    assert sniffio.current_async_library() == "trio"
    assert back_current_value == "back_in_main"


async def test_trio_from_thread_run_contextvars() -> None:
    trio_test_contextvar.set("main")

    def thread_fn() -> tuple[str, str, str, str, str]:
        thread_parent_value = trio_test_contextvar.get()
        trio_test_contextvar.set("worker")
        thread_current_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()

        async def async_back_in_main() -> tuple[str, str]:
            back_parent_value = trio_test_contextvar.get()
            trio_test_contextvar.set("back_in_main")
            back_current_value = trio_test_contextvar.get()
            assert sniffio.current_async_library() == "trio"
            return back_parent_value, back_current_value

        back_parent_value, back_current_value = from_thread_run(async_back_in_main)
        thread_after_value = trio_test_contextvar.get()
        with pytest.raises(sniffio.AsyncLibraryNotFoundError):
            sniffio.current_async_library()
        return (
            thread_parent_value,
            thread_current_value,
            thread_after_value,
            back_parent_value,
            back_current_value,
        )

    (
        thread_parent_value,
        thread_current_value,
        thread_after_value,
        back_parent_value,
        back_current_value,
    ) = await to_thread_run_sync(thread_fn)
    current_value = trio_test_contextvar.get()
    assert current_value == thread_parent_value == "main"
    assert thread_current_value == back_parent_value == thread_after_value == "worker"
    assert back_current_value == "back_in_main"
    assert sniffio.current_async_library() == "trio"


def test_run_fn_as_system_task_catched_badly_typed_token() -> None:
    with pytest.raises(RuntimeError):
        from_thread_run_sync(
            _core.current_time,
            trio_token="Not TrioTokentype",  # type: ignore[arg-type]
        )


async def test_from_thread_inside_trio_thread() -> None:
    def not_called() -> None:  # pragma: no cover
        raise AssertionError()

    trio_token = _core.current_trio_token()
    with pytest.raises(RuntimeError):
        from_thread_run_sync(not_called, trio_token=trio_token)


def test_from_thread_run_during_shutdown() -> None:
    save = []
    record = []

    async def agen(token: _core.TrioToken | None) -> AsyncGenerator[None, None]:
        try:
            yield
        finally:
            with _core.CancelScope(shield=True):
                try:
                    await to_thread_run_sync(
                        partial(from_thread_run, sleep, 0, trio_token=token)
                    )
                except _core.RunFinishedError:
                    record.append("finished")
                else:
                    record.append("clean")

    async def main(use_system_task: bool) -> None:
        save.append(agen(_core.current_trio_token() if use_system_task else None))
        await save[-1].asend(None)

    _core.run(main, True)  # System nursery will be closed and raise RunFinishedError
    _core.run(main, False)  # host task will be rescheduled as normal
    assert record == ["finished", "clean"]


async def test_trio_token_weak_referenceable() -> None:
    token = _core.current_trio_token()
    assert isinstance(token, _core.TrioToken)
    weak_reference = weakref.ref(token)
    assert token is weak_reference()


async def test_unsafe_abandon_on_cancel_kwarg() -> None:
    # This is a stand in for a numpy ndarray or other objects
    # that (maybe surprisingly) lack a notion of truthiness
    class BadBool:
        def __bool__(self) -> bool:
            raise NotImplementedError

    with pytest.raises(NotImplementedError):
        await to_thread_run_sync(int, abandon_on_cancel=BadBool())  # type: ignore[call-overload]


async def test_from_thread_reuses_task() -> None:
    task = _core.current_task()

    async def async_current_task() -> _core.Task:
        return _core.current_task()

    assert task is await to_thread_run_sync(from_thread_run_sync, _core.current_task)
    assert task is await to_thread_run_sync(from_thread_run, async_current_task)


async def test_recursive_to_thread() -> None:
    tid = None

    def get_tid_then_reenter() -> int:
        nonlocal tid
        tid = threading.get_ident()
        # The nesting of wrapper functions loses the return value of threading.get_ident
        return from_thread_run(to_thread_run_sync, threading.get_ident)  # type: ignore[no-any-return]

    assert tid != await to_thread_run_sync(get_tid_then_reenter)


async def test_from_thread_host_cancelled() -> None:
    queue: stdlib_queue.Queue[bool] = stdlib_queue.Queue()

    def sync_check() -> None:
        from_thread_run_sync(cancel_scope.cancel)
        try:
            from_thread_run_sync(bool)
        except _core.Cancelled:  # pragma: no cover
            queue.put(True)  # sync functions don't raise Cancelled
        else:
            queue.put(False)

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(sync_check)

    assert not cancel_scope.cancelled_caught
    assert not queue.get_nowait()

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(sync_check, abandon_on_cancel=True)

    assert cancel_scope.cancelled_caught
    assert not await to_thread_run_sync(partial(queue.get, timeout=1))

    async def no_checkpoint() -> bool:
        return True

    def async_check() -> None:
        from_thread_run_sync(cancel_scope.cancel)
        try:
            assert from_thread_run(no_checkpoint)
        except _core.Cancelled:  # pragma: no cover
            queue.put(True)  # async functions raise Cancelled at checkpoints
        else:
            queue.put(False)

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(async_check)

    assert not cancel_scope.cancelled_caught
    assert not queue.get_nowait()

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(async_check, abandon_on_cancel=True)

    assert cancel_scope.cancelled_caught
    assert not await to_thread_run_sync(partial(queue.get, timeout=1))

    async def async_time_bomb() -> None:
        cancel_scope.cancel()
        with fail_after(10):
            await sleep_forever()

    with _core.CancelScope() as cancel_scope:
        await to_thread_run_sync(from_thread_run, async_time_bomb)

    assert cancel_scope.cancelled_caught


async def test_from_thread_check_cancelled() -> None:
    q: stdlib_queue.Queue[str] = stdlib_queue.Queue()

    async def child(abandon_on_cancel: bool, scope: CancelScope) -> None:
        with scope:
            record.append("start")
            try:
                return await to_thread_run_sync(f, abandon_on_cancel=abandon_on_cancel)
            except _core.Cancelled:
                record.append("cancel")
                raise
            finally:
                record.append("exit")

    def f() -> None:
        try:
            from_thread_check_cancelled()
        except _core.Cancelled:  # pragma: no cover, test failure path
            q.put("Cancelled")
        else:
            q.put("Not Cancelled")
        ev.wait()
        return from_thread_check_cancelled()

    # Base case: nothing cancelled so we shouldn't see cancels anywhere
    record: list[str] = []
    ev = threading.Event()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, False, _core.CancelScope())
        await wait_all_tasks_blocked()
        assert record[0] == "start"
        assert q.get(timeout=1) == "Not Cancelled"
        ev.set()
    # implicit assertion, Cancelled not raised via nursery
    assert record[1] == "exit"

    # abandon_on_cancel=False case: a cancel will pop out but be handled by
    # the appropriate cancel scope
    record = []
    ev = threading.Event()
    scope = _core.CancelScope()  # Nursery cancel scope gives false positives
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, False, scope)
        await wait_all_tasks_blocked()
        assert record[0] == "start"
        assert q.get(timeout=1) == "Not Cancelled"
        scope.cancel()
        ev.set()
    assert scope.cancelled_caught
    assert "cancel" in record
    assert record[-1] == "exit"

    # abandon_on_cancel=True case: slightly different thread behavior needed
    # check thread is cancelled "soon" after abandonment
    def f() -> None:  # type: ignore[no-redef] # noqa: F811
        ev.wait()
        try:
            from_thread_check_cancelled()
        except _core.Cancelled:
            q.put("Cancelled")
        else:  # pragma: no cover, test failure path
            q.put("Not Cancelled")

    record = []
    ev = threading.Event()
    scope = _core.CancelScope()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(child, True, scope)
        await wait_all_tasks_blocked()
        assert record[0] == "start"
        scope.cancel()
        ev.set()
    assert scope.cancelled_caught
    assert "cancel" in record
    assert record[-1] == "exit"
    assert q.get(timeout=1) == "Cancelled"


async def test_from_thread_check_cancelled_raises_in_foreign_threads() -> None:
    with pytest.raises(RuntimeError):
        from_thread_check_cancelled()
    q: stdlib_queue.Queue[Outcome[object]] = stdlib_queue.Queue()
    _core.start_thread_soon(from_thread_check_cancelled, lambda _: q.put(_))
    with pytest.raises(RuntimeError):
        q.get(timeout=1).unwrap()


@slow
async def test_reentry_doesnt_deadlock() -> None:
    # Regression test for issue noticed in GH-2827
    # The failure mode is to hang the whole test suite, unfortunately.
    # XXX consider running this in a subprocess with a timeout, if it comes up again!

    async def child() -> None:
        while True:
            await to_thread_run_sync(from_thread_run, sleep, 0, abandon_on_cancel=False)

    with move_on_after(2):
        async with _core.open_nursery() as nursery:
            for _ in range(4):
                nursery.start_soon(child)


async def test_cancellable_and_abandon_raises() -> None:
    with pytest.raises(
        ValueError,
        match=r"^Cannot set `cancellable` and `abandon_on_cancel` simultaneously\.$",
    ):
        await to_thread_run_sync(bool, cancellable=True, abandon_on_cancel=False)  # type: ignore[call-overload]

    with pytest.raises(
        ValueError,
        match=r"^Cannot set `cancellable` and `abandon_on_cancel` simultaneously\.$",
    ):
        await to_thread_run_sync(bool, cancellable=True, abandon_on_cancel=True)  # type: ignore[call-overload]


async def test_cancellable_warns() -> None:
    with pytest.warns(TrioDeprecationWarning):
        await to_thread_run_sync(bool, cancellable=False)

    with pytest.warns(TrioDeprecationWarning):
        await to_thread_run_sync(bool, cancellable=True)


async def test_wait_all_threads_completed() -> None:
    no_threads_left = False
    e1 = Event()
    e2 = Event()

    e1_exited = Event()
    e2_exited = Event()

    async def wait_event(e: Event, e_exit: Event) -> None:
        def thread() -> None:
            from_thread_run(e.wait)

        await to_thread_run_sync(thread)
        e_exit.set()

    async def wait_no_threads_left() -> None:
        nonlocal no_threads_left
        await wait_all_threads_completed()
        no_threads_left = True

    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_event, e1, e1_exited)
        nursery.start_soon(wait_event, e2, e2_exited)
        await wait_all_tasks_blocked()
        nursery.start_soon(wait_no_threads_left)
        await wait_all_tasks_blocked()
        assert not no_threads_left
        assert active_thread_count() == 2

        e1.set()
        await e1_exited.wait()
        await wait_all_tasks_blocked()
        assert not no_threads_left
        assert active_thread_count() == 1

        e2.set()
        await e2_exited.wait()
        await wait_all_tasks_blocked()
        assert no_threads_left
        assert active_thread_count() == 0


async def test_wait_all_threads_completed_no_threads() -> None:
    await wait_all_threads_completed()
    assert active_thread_count() == 0
