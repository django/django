from __future__ import annotations

import asyncio
import contextlib
import queue
import signal
import socket
import sys
import threading
import time
import traceback
import warnings
import weakref
from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from functools import partial
from math import inf
from typing import (
    TYPE_CHECKING,
    NoReturn,
    TypeAlias,
    TypeVar,
    cast,
)

import pytest
import sniffio
from outcome import Outcome

import trio
import trio.testing
from trio.abc import Clock, Instrument

from .tutil import gc_collect_harder, restore_unraisablehook

if TYPE_CHECKING:
    from trio._channel import MemorySendChannel

T = TypeVar("T")
InHost: TypeAlias = Callable[[Callable[[], object]], None]


# The simplest possible "host" loop.
# Nice features:
# - we can run code "outside" of trio using the schedule function passed to
#   our main
# - final result is returned
# - any unhandled exceptions cause an immediate crash
def trivial_guest_run(
    trio_fn: Callable[[InHost], Awaitable[T]],
    *,
    in_host_after_start: Callable[[], None] | None = None,
    host_uses_signal_set_wakeup_fd: bool = False,
    clock: Clock | None = None,
    instruments: Sequence[Instrument] = (),
    restrict_keyboard_interrupt_to_checkpoints: bool = False,
    strict_exception_groups: bool = True,
) -> T:
    todo: queue.Queue[tuple[str, Outcome[T] | Callable[[], object]]] = queue.Queue()

    host_thread = threading.current_thread()

    def run_sync_soon_threadsafe(fn: Callable[[], object]) -> None:
        nonlocal todo
        if host_thread is threading.current_thread():  # pragma: no cover
            crash = partial(
                pytest.fail,
                "run_sync_soon_threadsafe called from host thread",
            )
            todo.put(("run", crash))
        todo.put(("run", fn))

    def run_sync_soon_not_threadsafe(fn: Callable[[], object]) -> None:
        nonlocal todo
        if host_thread is not threading.current_thread():  # pragma: no cover
            crash = partial(
                pytest.fail,
                "run_sync_soon_not_threadsafe called from worker thread",
            )
            todo.put(("run", crash))
        todo.put(("run", fn))

    def done_callback(outcome: Outcome[T]) -> None:
        nonlocal todo
        todo.put(("unwrap", outcome))

    trio.lowlevel.start_guest_run(
        trio_fn,
        run_sync_soon_not_threadsafe,
        run_sync_soon_threadsafe=run_sync_soon_threadsafe,
        run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
        done_callback=done_callback,
        host_uses_signal_set_wakeup_fd=host_uses_signal_set_wakeup_fd,
        clock=clock,
        instruments=instruments,
        restrict_keyboard_interrupt_to_checkpoints=restrict_keyboard_interrupt_to_checkpoints,
        strict_exception_groups=strict_exception_groups,
    )
    if in_host_after_start is not None:
        in_host_after_start()

    try:
        while True:
            op, obj = todo.get()
            if op == "run":
                assert not isinstance(obj, Outcome)
                obj()
            elif op == "unwrap":
                assert isinstance(obj, Outcome)
                return obj.unwrap()
            else:  # pragma: no cover
                raise NotImplementedError(f"{op!r} not handled")
    finally:
        # Make sure that exceptions raised here don't capture these, so that
        # if an exception does cause us to abandon a run then the Trio state
        # has a chance to be GC'ed and warn about it.
        del todo, run_sync_soon_threadsafe, done_callback


def test_guest_trivial() -> None:
    async def trio_return(in_host: InHost) -> str:
        await trio.lowlevel.checkpoint()
        return "ok"

    assert trivial_guest_run(trio_return) == "ok"

    async def trio_fail(in_host: InHost) -> NoReturn:
        raise KeyError("whoopsiedaisy")

    with pytest.raises(KeyError, match="whoopsiedaisy"):
        trivial_guest_run(trio_fail)


def test_guest_can_do_io() -> None:
    async def trio_main(in_host: InHost) -> None:
        record = []
        a, b = trio.socket.socketpair()
        with a, b:
            async with trio.open_nursery() as nursery:

                async def do_receive() -> None:
                    record.append(await a.recv(1))

                nursery.start_soon(do_receive)
                await trio.testing.wait_all_tasks_blocked()

                await b.send(b"x")

        assert record == [b"x"]

    trivial_guest_run(trio_main)


def test_guest_is_initialized_when_start_returns() -> None:
    trio_token = None
    record = []

    async def trio_main(in_host: InHost) -> str:
        record.append("main task ran")
        await trio.lowlevel.checkpoint()
        assert trio.lowlevel.current_trio_token() is trio_token
        return "ok"

    def after_start() -> None:
        # We should get control back before the main task executes any code
        assert record == []

        nonlocal trio_token
        trio_token = trio.lowlevel.current_trio_token()
        trio_token.run_sync_soon(record.append, "run_sync_soon cb ran")

        @trio.lowlevel.spawn_system_task
        async def early_task() -> None:
            record.append("system task ran")
            await trio.lowlevel.checkpoint()

    res = trivial_guest_run(trio_main, in_host_after_start=after_start)
    assert res == "ok"
    assert set(record) == {"system task ran", "main task ran", "run_sync_soon cb ran"}

    class BadClock(Clock):
        def start_clock(self) -> NoReturn:
            raise ValueError("whoops")

        def current_time(self) -> float:
            raise NotImplementedError()

        def deadline_to_sleep_time(self, deadline: float) -> float:
            raise NotImplementedError()

    def after_start_never_runs() -> None:  # pragma: no cover
        pytest.fail("shouldn't get here")

    # Errors during initialization (which can only be TrioInternalErrors)
    # are raised out of start_guest_run, not out of the done_callback
    with pytest.raises(trio.TrioInternalError):
        trivial_guest_run(
            trio_main,
            clock=BadClock(),
            in_host_after_start=after_start_never_runs,
        )


def test_host_can_directly_wake_trio_task() -> None:
    async def trio_main(in_host: InHost) -> str:
        ev = trio.Event()
        in_host(ev.set)
        await ev.wait()
        return "ok"

    assert trivial_guest_run(trio_main) == "ok"


def test_host_altering_deadlines_wakes_trio_up() -> None:
    def set_deadline(cscope: trio.CancelScope, new_deadline: float) -> None:
        cscope.deadline = new_deadline

    async def trio_main(in_host: InHost) -> str:
        with trio.CancelScope() as cscope:
            in_host(lambda: set_deadline(cscope, -inf))
            await trio.sleep_forever()
        assert cscope.cancelled_caught

        with trio.CancelScope() as cscope:
            # also do a change that doesn't affect the next deadline, just to
            # exercise that path
            in_host(lambda: set_deadline(cscope, 1e6))
            in_host(lambda: set_deadline(cscope, -inf))
            await trio.sleep(999)
        assert cscope.cancelled_caught

        return "ok"

    assert trivial_guest_run(trio_main) == "ok"


def test_guest_mode_sniffio_integration() -> None:
    current_async_library = sniffio.current_async_library
    sniffio_library = sniffio.thread_local

    async def trio_main(in_host: InHost) -> str:
        async def synchronize() -> None:
            """Wait for all in_host() calls issued so far to complete."""
            evt = trio.Event()
            in_host(evt.set)
            await evt.wait()

        # Host and guest have separate sniffio_library contexts
        in_host(partial(setattr, sniffio_library, "name", "nullio"))
        await synchronize()
        assert current_async_library() == "trio"

        record = []
        in_host(lambda: record.append(current_async_library()))
        await synchronize()
        assert record == ["nullio"]
        assert current_async_library() == "trio"

        return "ok"

    try:
        assert trivial_guest_run(trio_main) == "ok"
    finally:
        sniffio_library.name = None


def test_guest_mode_trio_context_detection() -> None:
    def check(thing: bool) -> None:
        assert thing

    assert not trio.lowlevel.in_trio_run()
    assert not trio.lowlevel.in_trio_task()

    async def trio_main(in_host: InHost) -> None:
        for _ in range(2):
            assert trio.lowlevel.in_trio_run()
            assert trio.lowlevel.in_trio_task()

            in_host(lambda: check(trio.lowlevel.in_trio_run()))
            in_host(lambda: check(not trio.lowlevel.in_trio_task()))

    trivial_guest_run(trio_main)
    assert not trio.lowlevel.in_trio_run()
    assert not trio.lowlevel.in_trio_task()


def test_warn_set_wakeup_fd_overwrite() -> None:
    assert signal.set_wakeup_fd(-1) == -1

    async def trio_main(in_host: InHost) -> str:
        return "ok"

    a, b = socket.socketpair()
    with a, b:
        a.setblocking(False)

        # Warn if there's already a wakeup fd
        signal.set_wakeup_fd(a.fileno())
        try:
            with pytest.warns(RuntimeWarning, match="signal handling code.*collided"):
                assert trivial_guest_run(trio_main) == "ok"
        finally:
            assert signal.set_wakeup_fd(-1) == a.fileno()

        signal.set_wakeup_fd(a.fileno())
        try:
            with pytest.warns(RuntimeWarning, match="signal handling code.*collided"):
                assert (
                    trivial_guest_run(trio_main, host_uses_signal_set_wakeup_fd=False)
                    == "ok"
                )
        finally:
            assert signal.set_wakeup_fd(-1) == a.fileno()

        # Don't warn if there isn't already a wakeup fd
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert trivial_guest_run(trio_main) == "ok"

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            assert (
                trivial_guest_run(trio_main, host_uses_signal_set_wakeup_fd=True)
                == "ok"
            )

        # If there's already a wakeup fd, but we've been told to trust it,
        # then it's left alone and there's no warning
        signal.set_wakeup_fd(a.fileno())
        try:

            async def trio_check_wakeup_fd_unaltered(in_host: InHost) -> str:
                fd = signal.set_wakeup_fd(-1)
                assert fd == a.fileno()
                signal.set_wakeup_fd(fd)
                return "ok"

            with warnings.catch_warnings():
                warnings.simplefilter("error")
                assert (
                    trivial_guest_run(
                        trio_check_wakeup_fd_unaltered,
                        host_uses_signal_set_wakeup_fd=True,
                    )
                    == "ok"
                )
        finally:
            assert signal.set_wakeup_fd(-1) == a.fileno()


def test_host_wakeup_doesnt_trigger_wait_all_tasks_blocked() -> None:
    # This is designed to hit the branch in unrolled_run where:
    #   idle_primed=True
    #   runner.runq is empty
    #   events is Truth-y
    # ...and confirm that in this case, wait_all_tasks_blocked does not get
    # triggered.
    def set_deadline(cscope: trio.CancelScope, new_deadline: float) -> None:
        print(f"setting deadline {new_deadline}")
        cscope.deadline = new_deadline

    async def trio_main(in_host: InHost) -> str:
        async def sit_in_wait_all_tasks_blocked(watb_cscope: trio.CancelScope) -> None:
            with watb_cscope:
                # Overall point of this test is that this
                # wait_all_tasks_blocked should *not* return normally, but
                # only by cancellation.
                await trio.testing.wait_all_tasks_blocked(cushion=9999)
                raise AssertionError(  # pragma: no cover
                    "wait_all_tasks_blocked should *not* return normally, "
                    "only by cancellation.",
                )
            assert watb_cscope.cancelled_caught

        async def get_woken_by_host_deadline(watb_cscope: trio.CancelScope) -> None:
            with trio.CancelScope() as cscope:
                print("scheduling stuff to happen")

                # Altering the deadline from the host, to something in the
                # future, will cause the run loop to wake up, but then
                # discover that there is nothing to do and go back to sleep.
                # This should *not* trigger wait_all_tasks_blocked.
                #
                # So the 'before_io_wait' here will wait until we're blocking
                # with the wait_all_tasks_blocked primed, and then schedule a
                # deadline change. The critical test is that this should *not*
                # wake up 'sit_in_wait_all_tasks_blocked'.
                #
                # The after we've had a chance to wake up
                # 'sit_in_wait_all_tasks_blocked', we want the test to
                # actually end. So in after_io_wait we schedule a second host
                # call to tear things down.
                class InstrumentHelper(Instrument):
                    def __init__(self) -> None:
                        self.primed = False

                    def before_io_wait(self, timeout: float) -> None:
                        print(f"before_io_wait({timeout})")
                        if timeout == 9999:  # pragma: no branch
                            assert not self.primed
                            in_host(lambda: set_deadline(cscope, 1e9))
                            self.primed = True

                    def after_io_wait(self, timeout: float) -> None:
                        if self.primed:  # pragma: no branch
                            print("instrument triggered")
                            in_host(lambda: cscope.cancel())
                            trio.lowlevel.remove_instrument(self)

                trio.lowlevel.add_instrument(InstrumentHelper())
                await trio.sleep_forever()
            assert cscope.cancelled_caught
            watb_cscope.cancel()

        async with trio.open_nursery() as nursery:
            watb_cscope = trio.CancelScope()
            nursery.start_soon(sit_in_wait_all_tasks_blocked, watb_cscope)
            await trio.testing.wait_all_tasks_blocked()
            nursery.start_soon(get_woken_by_host_deadline, watb_cscope)

        return "ok"

    assert trivial_guest_run(trio_main) == "ok"


@restore_unraisablehook()
def test_guest_warns_if_abandoned() -> None:
    # This warning is emitted from the garbage collector. So we have to make
    # sure that our abandoned run is garbage. The easiest way to do this is to
    # put it into a function, so that we're sure all the local state,
    # traceback frames, etc. are garbage once it returns.
    def do_abandoned_guest_run() -> None:
        async def abandoned_main(in_host: InHost) -> None:
            in_host(lambda: 1 / 0)
            while True:
                await trio.lowlevel.checkpoint()

        with pytest.raises(ZeroDivisionError):
            trivial_guest_run(abandoned_main)

    with pytest.warns(  # noqa: PT031
        RuntimeWarning,
        match="Trio guest run got abandoned",
    ):
        do_abandoned_guest_run()
        gc_collect_harder()

    # If you have problems some day figuring out what's holding onto a
    # reference to the unrolled_run generator and making this test fail,
    # then this might be useful to help track it down. (It assumes you
    # also hack start_guest_run so that it does 'global W; W =
    # weakref(unrolled_run_gen)'.)
    #
    # import gc
    # print(trio._core._run.W)
    # targets = [trio._core._run.W()]
    # for i in range(15):
    #     new_targets = []
    #     for target in targets:
    #         new_targets += gc.get_referrers(target)
    #         new_targets.remove(targets)
    #     print("#####################")
    #     print(f"depth {i}: {len(new_targets)}")
    #     print(new_targets)
    #     targets = new_targets

    with pytest.raises(RuntimeError):
        trio.current_time()


def aiotrio_run(
    trio_fn: Callable[[], Awaitable[T]],
    *,
    pass_not_threadsafe: bool = True,
    run_sync_soon_not_threadsafe: InHost | None = None,
    host_uses_signal_set_wakeup_fd: bool = False,
    clock: Clock | None = None,
    instruments: Sequence[Instrument] = (),
    restrict_keyboard_interrupt_to_checkpoints: bool = False,
    strict_exception_groups: bool = True,
) -> T:
    loop = asyncio.new_event_loop()

    async def aio_main() -> T:
        nonlocal run_sync_soon_not_threadsafe
        trio_done_fut: asyncio.Future[Outcome[T]] = loop.create_future()

        def trio_done_callback(main_outcome: Outcome[T]) -> None:
            print(f"trio_fn finished: {main_outcome!r}")
            trio_done_fut.set_result(main_outcome)

        if pass_not_threadsafe:
            run_sync_soon_not_threadsafe = cast("InHost", loop.call_soon)

        trio.lowlevel.start_guest_run(
            trio_fn,
            run_sync_soon_threadsafe=loop.call_soon_threadsafe,
            done_callback=trio_done_callback,
            run_sync_soon_not_threadsafe=run_sync_soon_not_threadsafe,
            host_uses_signal_set_wakeup_fd=host_uses_signal_set_wakeup_fd,
            clock=clock,
            instruments=instruments,
            restrict_keyboard_interrupt_to_checkpoints=restrict_keyboard_interrupt_to_checkpoints,
            strict_exception_groups=strict_exception_groups,
        )

        return (await trio_done_fut).unwrap()

    try:
        # can't use asyncio.run because that fails on Windows (3.10, x64, with
        # Komodia LSP)
        return loop.run_until_complete(aio_main())
    finally:
        loop.close()


def test_guest_mode_on_asyncio() -> None:
    async def trio_main() -> str:
        print("trio_main!")

        to_trio, from_aio = trio.open_memory_channel[int](float("inf"))
        from_trio: asyncio.Queue[int] = asyncio.Queue()

        aio_task = asyncio.ensure_future(aio_pingpong(from_trio, to_trio))

        # Make sure we have at least one tick where we don't need to go into
        # the thread
        await trio.lowlevel.checkpoint()

        from_trio.put_nowait(0)

        async for n in from_aio:
            print(f"trio got: {n}")
            from_trio.put_nowait(n + 1)
            if n >= 10:
                aio_task.cancel()
                return "trio-main-done"

        raise AssertionError("should never be reached")  # pragma: no cover

    async def aio_pingpong(
        from_trio: asyncio.Queue[int],
        to_trio: MemorySendChannel[int],
    ) -> None:
        print("aio_pingpong!")

        try:
            while True:
                n = await from_trio.get()
                print(f"aio got: {n}")
                to_trio.send_nowait(n + 1)
        except asyncio.CancelledError:
            raise
        except:  # pragma: no cover
            traceback.print_exc()
            raise

    assert (
        aiotrio_run(
            trio_main,
            # Not all versions of asyncio we test on can actually be trusted,
            # but this test doesn't care about signal handling, and it's
            # easier to just avoid the warnings.
            host_uses_signal_set_wakeup_fd=True,
        )
        == "trio-main-done"
    )

    assert (
        aiotrio_run(
            trio_main,
            # Also check that passing only call_soon_threadsafe works, via the
            # fallback path where we use it for everything.
            pass_not_threadsafe=False,
            host_uses_signal_set_wakeup_fd=True,
        )
        == "trio-main-done"
    )


def test_guest_mode_internal_errors(
    monkeypatch: pytest.MonkeyPatch,
    recwarn: pytest.WarningsRecorder,
) -> None:
    with monkeypatch.context() as m:

        async def crash_in_run_loop(in_host: InHost) -> None:
            m.setattr("trio._core._run.GLOBAL_RUN_CONTEXT.runner.runq", "HI")
            await trio.sleep(1)

        with pytest.raises(trio.TrioInternalError):
            trivial_guest_run(crash_in_run_loop)

    with monkeypatch.context() as m:

        async def crash_in_io(in_host: InHost) -> None:
            m.setattr("trio._core._run.TheIOManager.get_events", None)
            await trio.lowlevel.checkpoint()

        with pytest.raises(trio.TrioInternalError):
            trivial_guest_run(crash_in_io)

    with monkeypatch.context() as m:

        async def crash_in_worker_thread_io(in_host: InHost) -> None:
            t = threading.current_thread()
            old_get_events = trio._core._run.TheIOManager.get_events

            def bad_get_events(
                self: trio._core._run.TheIOManager,
                timeout: float,
            ) -> trio._core._run.EventResult:
                if threading.current_thread() is not t:
                    raise ValueError("oh no!")
                else:
                    return old_get_events(self, timeout)

            m.setattr("trio._core._run.TheIOManager.get_events", bad_get_events)

            await trio.sleep(1)

        with pytest.raises(trio.TrioInternalError):
            trivial_guest_run(crash_in_worker_thread_io)

    gc_collect_harder()


def test_guest_mode_ki() -> None:
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler

    # Check SIGINT in Trio func and in host func
    async def trio_main(in_host: InHost) -> None:
        with pytest.raises(KeyboardInterrupt):
            signal.raise_signal(signal.SIGINT)

        # Host SIGINT should get injected into Trio
        in_host(partial(signal.raise_signal, signal.SIGINT))
        await trio.sleep(10)

    with pytest.raises(KeyboardInterrupt) as excinfo:
        trivial_guest_run(trio_main)
    assert excinfo.value.__context__ is None
    # Signal handler should be restored properly on exit
    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler

    # Also check chaining in the case where KI is injected after main exits
    final_exc = KeyError("whoa")

    async def trio_main_raising(in_host: InHost) -> NoReturn:
        in_host(partial(signal.raise_signal, signal.SIGINT))
        raise final_exc

    with pytest.raises(KeyboardInterrupt) as excinfo:
        trivial_guest_run(trio_main_raising)
    assert excinfo.value.__context__ is final_exc

    assert signal.getsignal(signal.SIGINT) is signal.default_int_handler


def test_guest_mode_autojump_clock_threshold_changing() -> None:
    # This is super obscure and probably no-one will ever notice, but
    # technically mutating the MockClock.autojump_threshold from the host
    # should wake up the guest, so let's test it.

    clock = trio.testing.MockClock()

    DURATION = 120

    async def trio_main(in_host: InHost) -> None:
        assert trio.current_time() == 0
        in_host(lambda: setattr(clock, "autojump_threshold", 0))
        await trio.sleep(DURATION)
        assert trio.current_time() == DURATION

    start = time.monotonic()
    trivial_guest_run(trio_main, clock=clock)
    end = time.monotonic()
    # Should be basically instantaneous, but we'll leave a generous buffer to
    # account for any CI weirdness
    assert end - start < DURATION / 2


@restore_unraisablehook()
def test_guest_mode_asyncgens() -> None:
    record = set()

    async def agen(label: str) -> AsyncGenerator[int, None]:
        assert sniffio.current_async_library() == label
        try:
            yield 1
        finally:
            library = sniffio.current_async_library()
            with contextlib.suppress(trio.Cancelled):
                await sys.modules[library].sleep(0)
            record.add((label, library))

    async def iterate_in_aio() -> None:
        await agen("asyncio").asend(None)

    async def trio_main() -> None:
        task = asyncio.ensure_future(iterate_in_aio())
        done_evt = trio.Event()
        task.add_done_callback(lambda _: done_evt.set())
        with trio.fail_after(1):
            await done_evt.wait()

        await agen("trio").asend(None)

        gc_collect_harder()

    aiotrio_run(trio_main, host_uses_signal_set_wakeup_fd=True)

    assert record == {("asyncio", "asyncio"), ("trio", "trio")}


@restore_unraisablehook()
def test_guest_mode_asyncgens_garbage_collection() -> None:
    record: set[tuple[str, str, bool]] = set()

    async def agen(label: str) -> AsyncGenerator[int, None]:
        class A:
            pass

        a = A()
        a_wr = weakref.ref(a)
        assert sniffio.current_async_library() == label
        try:
            yield 1
        finally:
            library = sniffio.current_async_library()
            with contextlib.suppress(trio.Cancelled):
                await sys.modules[library].sleep(0)

            del a
            if sys.implementation.name == "pypy":
                gc_collect_harder()

            record.add((label, library, a_wr() is None))

    async def iterate_in_aio() -> None:
        await agen("asyncio").asend(None)

    async def trio_main() -> None:
        task = asyncio.ensure_future(iterate_in_aio())
        done_evt = trio.Event()
        task.add_done_callback(lambda _: done_evt.set())
        with trio.fail_after(1):
            await done_evt.wait()

        await agen("trio").asend(None)

        gc_collect_harder()

    aiotrio_run(trio_main, host_uses_signal_set_wakeup_fd=True)

    assert record == {("asyncio", "asyncio", True), ("trio", "trio", True)}
