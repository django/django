from __future__ import annotations

import contextlib
import inspect
import signal
import sys
import threading
import weakref
from collections.abc import AsyncIterator, Callable, Iterator
from typing import TYPE_CHECKING, TypeVar

import outcome
import pytest

from .tutil import gc_collect_harder

try:
    from async_generator import async_generator, yield_
except ImportError:  # pragma: no cover
    async_generator = yield_ = None

from ... import _core
from ..._abc import Instrument
from ..._core import _ki
from ..._timeouts import sleep
from ...testing import wait_all_tasks_blocked

if TYPE_CHECKING:
    from collections.abc import (
        AsyncGenerator,
        AsyncIterator,
        Callable,
        Generator,
        Iterator,
    )

    from ..._core import Abort, RaiseCancelT


def ki_self() -> None:
    signal.raise_signal(signal.SIGINT)


def test_ki_self() -> None:
    with pytest.raises(KeyboardInterrupt):
        ki_self()


async def test_ki_enabled() -> None:
    # Regular tasks aren't KI-protected
    assert not _core.currently_ki_protected()

    # Low-level call-soon callbacks are KI-protected
    token = _core.current_trio_token()
    record = []

    def check() -> None:
        record.append(_core.currently_ki_protected())

    token.run_sync_soon(check)
    await wait_all_tasks_blocked()
    assert record == [True]

    @_core.enable_ki_protection
    def protected() -> None:
        assert _core.currently_ki_protected()
        unprotected()

    @_core.disable_ki_protection
    def unprotected() -> None:
        assert not _core.currently_ki_protected()

    protected()

    @_core.enable_ki_protection
    async def aprotected() -> None:
        assert _core.currently_ki_protected()
        await aunprotected()

    @_core.disable_ki_protection
    async def aunprotected() -> None:
        assert not _core.currently_ki_protected()

    await aprotected()

    # make sure that the decorator here overrides the automatic manipulation
    # that start_soon() does:
    async with _core.open_nursery() as nursery:
        nursery.start_soon(aprotected)
        nursery.start_soon(aunprotected)

    @_core.enable_ki_protection
    def gen_protected() -> Iterator[None]:
        assert _core.currently_ki_protected()
        yield

    for _ in gen_protected():
        pass

    @_core.disable_ki_protection
    def gen_unprotected() -> Iterator[None]:
        assert not _core.currently_ki_protected()
        yield

    for _ in gen_unprotected():
        pass


# This used to be broken due to
#
#   https://bugs.python.org/issue29590
#
# Specifically, after a coroutine is resumed with .throw(), then the stack
# makes it look like the immediate caller is the function that called
# .throw(), not the actual caller. So child() here would have a caller deep in
# the guts of the run loop, and always be protected, even when it shouldn't
# have been. (Solution: we don't use .throw() anymore.)
async def test_ki_enabled_after_yield_briefly() -> None:
    @_core.enable_ki_protection
    async def protected() -> None:
        await child(True)

    @_core.disable_ki_protection
    async def unprotected() -> None:
        await child(False)

    async def child(expected: bool) -> None:
        import traceback

        traceback.print_stack()
        assert _core.currently_ki_protected() == expected
        await _core.checkpoint()
        traceback.print_stack()
        assert _core.currently_ki_protected() == expected

    await protected()
    await unprotected()


# This also used to be broken due to
#   https://bugs.python.org/issue29590
async def test_generator_based_context_manager_throw() -> None:
    @contextlib.contextmanager
    @_core.enable_ki_protection
    def protected_manager() -> Iterator[None]:
        assert _core.currently_ki_protected()
        try:
            yield
        finally:
            assert _core.currently_ki_protected()

    with protected_manager():
        assert not _core.currently_ki_protected()

    with pytest.raises(KeyError):
        # This is the one that used to fail
        with protected_manager():
            raise KeyError


# the async_generator package isn't typed, hence all the type: ignores
@pytest.mark.skipif(async_generator is None, reason="async_generator not installed")
async def test_async_generator_agen_protection() -> None:
    @_core.enable_ki_protection
    @async_generator  # type: ignore[untyped-decorator]
    async def agen_protected1() -> None:  # type: ignore[misc] # untyped generator
        assert _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert _core.currently_ki_protected()

    @_core.disable_ki_protection
    @async_generator  # type: ignore[untyped-decorator]
    async def agen_unprotected1() -> None:  # type: ignore[misc] # untyped generator
        assert not _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert not _core.currently_ki_protected()

    # Swap the order of the decorators:
    @async_generator  # type: ignore[untyped-decorator]
    @_core.enable_ki_protection
    async def agen_protected2() -> None:  # type: ignore[misc] # untyped generator
        assert _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert _core.currently_ki_protected()

    @async_generator  # type: ignore[untyped-decorator]
    @_core.disable_ki_protection
    async def agen_unprotected2() -> None:  # type: ignore[misc] # untyped generator
        assert not _core.currently_ki_protected()
        try:
            await yield_()
        finally:
            assert not _core.currently_ki_protected()

    await _check_agen(agen_protected1)
    await _check_agen(agen_protected2)
    await _check_agen(agen_unprotected1)
    await _check_agen(agen_unprotected2)


async def test_native_agen_protection() -> None:
    # Native async generators
    @_core.enable_ki_protection
    async def agen_protected() -> AsyncIterator[None]:
        assert _core.currently_ki_protected()
        try:
            yield
        finally:
            assert _core.currently_ki_protected()

    @_core.disable_ki_protection
    async def agen_unprotected() -> AsyncIterator[None]:
        assert not _core.currently_ki_protected()
        try:
            yield
        finally:
            assert not _core.currently_ki_protected()

    await _check_agen(agen_protected)
    await _check_agen(agen_unprotected)


async def _check_agen(agen_fn: Callable[[], AsyncIterator[None]]) -> None:
    async for _ in agen_fn():
        assert not _core.currently_ki_protected()

    # asynccontextmanager insists that the function passed must itself be an
    # async gen function, not a wrapper around one
    if inspect.isasyncgenfunction(agen_fn):
        async with contextlib.asynccontextmanager(agen_fn)():
            assert not _core.currently_ki_protected()

        # Another case that's tricky due to:
        #   https://bugs.python.org/issue29590
        with pytest.raises(KeyError):
            async with contextlib.asynccontextmanager(agen_fn)():
                raise KeyError


# Test the case where there's no magic local anywhere in the call stack
def test_ki_disabled_out_of_context() -> None:
    assert _core.currently_ki_protected()


def test_ki_disabled_in_del() -> None:
    def nestedfunction() -> bool:
        return _core.currently_ki_protected()

    def __del__() -> None:
        assert _core.currently_ki_protected()
        assert nestedfunction()

    @_core.disable_ki_protection
    def outerfunction() -> None:
        assert not _core.currently_ki_protected()
        assert not nestedfunction()
        __del__()

    __del__()
    outerfunction()
    assert nestedfunction()


def test_ki_protection_works() -> None:
    async def sleeper(name: str, record: set[str]) -> None:
        try:
            while True:
                await _core.checkpoint()
        except _core.Cancelled:
            record.add(name + " ok")

    async def raiser(name: str, record: set[str]) -> None:
        try:
            # os.kill runs signal handlers before returning, so we don't need
            # to worry that the handler will be delayed
            print("killing, protection =", _core.currently_ki_protected())
            ki_self()
        except KeyboardInterrupt:
            print("raised!")
            # Make sure we aren't getting cancelled as well as siginted
            await _core.checkpoint()
            record.add(name + " raise ok")
            raise
        else:
            print("didn't raise!")
            # If we didn't raise (b/c protected), then we *should* get
            # cancelled at the next opportunity
            try:
                await _core.wait_task_rescheduled(lambda _: _core.Abort.SUCCEEDED)
            except _core.Cancelled:
                record.add(name + " cancel ok")

    # simulated control-C during raiser, which is *unprotected*
    print("check 1")
    record_set: set[str] = set()

    async def check_unprotected_kill() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleeper, "s1", record_set)
            nursery.start_soon(sleeper, "s2", record_set)
            nursery.start_soon(raiser, "r1", record_set)

    # raises inside a nursery, so the KeyboardInterrupt is wrapped in an ExceptionGroup
    with pytest.RaisesGroup(KeyboardInterrupt):
        _core.run(check_unprotected_kill)
    assert record_set == {"s1 ok", "s2 ok", "r1 raise ok"}

    # simulated control-C during raiser, which is *protected*, so the KI gets
    # delivered to the main task instead
    print("check 2")
    record_set = set()

    async def check_protected_kill() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleeper, "s1", record_set)
            nursery.start_soon(sleeper, "s2", record_set)
            nursery.start_soon(_core.enable_ki_protection(raiser), "r1", record_set)
            # __aexit__ blocks, and then receives the KI

    # raises inside a nursery, so the KeyboardInterrupt is wrapped in an ExceptionGroup
    with pytest.RaisesGroup(KeyboardInterrupt):
        _core.run(check_protected_kill)
    assert record_set == {"s1 ok", "s2 ok", "r1 cancel ok"}

    # kill at last moment still raises (run_sync_soon until it raises an
    # error, then kill)
    print("check 3")

    async def check_kill_during_shutdown() -> None:
        token = _core.current_trio_token()

        def kill_during_shutdown() -> None:
            assert _core.currently_ki_protected()
            try:
                token.run_sync_soon(kill_during_shutdown)
            except _core.RunFinishedError:
                # it's too late for regular handling! handle this!
                print("kill! kill!")
                ki_self()

        token.run_sync_soon(kill_during_shutdown)

    # no nurseries involved, so the KeyboardInterrupt isn't wrapped
    with pytest.raises(KeyboardInterrupt):
        _core.run(check_kill_during_shutdown)

    # KI arrives very early, before main is even spawned
    print("check 4")

    class InstrumentOfDeath(Instrument):
        def before_run(self) -> None:
            ki_self()

    async def main_1() -> None:
        await _core.checkpoint()

    # no nurseries involved, so the KeyboardInterrupt isn't wrapped
    with pytest.raises(KeyboardInterrupt):
        _core.run(main_1, instruments=[InstrumentOfDeath()])

    # checkpoint_if_cancelled notices pending KI
    print("check 5")

    @_core.enable_ki_protection
    async def main_2() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        with pytest.raises(KeyboardInterrupt):
            await _core.checkpoint_if_cancelled()

    _core.run(main_2)

    # KI arrives while main task is not abortable, b/c already scheduled
    print("check 6")

    @_core.enable_ki_protection
    async def main_3() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        await _core.cancel_shielded_checkpoint()
        await _core.cancel_shielded_checkpoint()
        await _core.cancel_shielded_checkpoint()
        with pytest.raises(KeyboardInterrupt):
            await _core.checkpoint()

    _core.run(main_3)

    # KI arrives while main task is not abortable, b/c refuses to be aborted
    print("check 7")

    @_core.enable_ki_protection
    async def main_4() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        task = _core.current_task()

        def abort(_: RaiseCancelT) -> Abort:
            _core.reschedule(task, outcome.Value(1))
            return _core.Abort.FAILED

        assert await _core.wait_task_rescheduled(abort) == 1
        with pytest.raises(KeyboardInterrupt):
            await _core.checkpoint()

    _core.run(main_4)

    # KI delivered via slow abort
    print("check 8")

    @_core.enable_ki_protection
    async def main_5() -> None:
        assert _core.currently_ki_protected()
        ki_self()
        task = _core.current_task()

        def abort(raise_cancel: RaiseCancelT) -> Abort:
            result = outcome.capture(raise_cancel)
            _core.reschedule(task, result)
            return _core.Abort.FAILED

        with pytest.raises(KeyboardInterrupt):
            assert await _core.wait_task_rescheduled(abort)
        await _core.checkpoint()

    _core.run(main_5)

    # KI arrives just before main task exits, so the run_sync_soon machinery
    # is still functioning and will accept the callback to deliver the KI, but
    # by the time the callback is actually run, main has exited and can't be
    # aborted.
    print("check 9")

    @_core.enable_ki_protection
    async def main_6() -> None:
        ki_self()

    with pytest.raises(KeyboardInterrupt):
        _core.run(main_6)

    print("check 10")
    # KI in unprotected code, with
    # restrict_keyboard_interrupt_to_checkpoints=True
    record_list = []

    async def main_7() -> None:
        # We're not KI protected...
        assert not _core.currently_ki_protected()
        ki_self()
        # ...but even after the KI, we keep running uninterrupted...
        record_list.append("ok")
        # ...until we hit a checkpoint:
        with pytest.raises(KeyboardInterrupt):
            await sleep(10)

    _core.run(main_7, restrict_keyboard_interrupt_to_checkpoints=True)
    assert record_list == ["ok"]
    record_list = []
    # Exact same code raises KI early if we leave off the argument, doesn't
    # even reach the record.append call:
    with pytest.raises(KeyboardInterrupt):
        _core.run(main_7)
    assert record_list == []

    # KI arrives while main task is inside a cancelled cancellation scope
    # the KeyboardInterrupt should take priority
    print("check 11")

    @_core.enable_ki_protection
    async def main_8() -> None:
        assert _core.currently_ki_protected()
        with _core.CancelScope() as cancel_scope:
            cancel_scope.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            ki_self()
            with pytest.raises(KeyboardInterrupt):
                await _core.checkpoint()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

    _core.run(main_8)


def test_ki_is_good_neighbor() -> None:
    # in the unlikely event someone overwrites our signal handler, we leave
    # the overwritten one be
    try:
        orig = signal.getsignal(signal.SIGINT)

        def my_handler(signum: object, frame: object) -> None:  # pragma: no cover
            pass

        async def main() -> None:
            signal.signal(signal.SIGINT, my_handler)

        _core.run(main)

        assert signal.getsignal(signal.SIGINT) is my_handler
    finally:
        signal.signal(signal.SIGINT, orig)


# Regression test for #461
# don't know if _active not being visible is a problem
def test_ki_with_broken_threads() -> None:
    thread = threading.main_thread()

    # scary!
    original = threading._active[thread.ident]  # type: ignore[attr-defined]

    # put this in a try finally so we don't have a chance of cascading a
    # breakage down to everything else
    try:
        del threading._active[thread.ident]  # type: ignore[attr-defined]

        @_core.enable_ki_protection
        async def inner() -> None:
            assert signal.getsignal(signal.SIGINT) != signal.default_int_handler

        _core.run(inner)
    finally:
        threading._active[thread.ident] = original  # type: ignore[attr-defined]


_T = TypeVar("_T")


def _identity(v: _T) -> _T:
    return v


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "it was decided not to protect against this case, see discussion in: "
        "https://github.com/python-trio/trio/pull/3110#discussion_r1802123644"
    ),
)
async def test_ki_does_not_leak_across_different_calls_to_inner_functions() -> None:
    assert not _core.currently_ki_protected()

    def factory(enabled: bool) -> Callable[[], bool]:
        @_core.enable_ki_protection if enabled else _identity
        def decorated() -> bool:
            return _core.currently_ki_protected()

        return decorated

    decorated_enabled = factory(True)
    decorated_disabled = factory(False)
    assert decorated_enabled()
    assert not decorated_disabled()


async def test_ki_protection_check_does_not_freeze_locals() -> None:
    class A:
        pass

    a = A()
    wr_a = weakref.ref(a)
    assert not _core.currently_ki_protected()
    del a
    if sys.implementation.name == "pypy":
        gc_collect_harder()
    assert wr_a() is None


def test_identity_weakref_internals() -> None:
    """To cover the parts WeakKeyIdentityDictionary won't ever reach."""

    class A:
        def __eq__(self, other: object) -> bool:
            return False

    a = A()
    assert a != a
    wr = _ki._IdRef(a)
    wr_other_is_self = wr

    # dict always checks identity before equality so we need to do it here
    # to cover `if self is other`
    assert wr == wr_other_is_self

    # we want to cover __ne__ and `return NotImplemented`
    assert wr != object()


def test_weak_key_identity_dict_remove_callback_keyerror() -> None:
    """We need to cover the KeyError in self._remove."""

    class A:
        def __eq__(self, other: object) -> bool:
            return False

    a = A()
    assert a != a
    d: _ki.WeakKeyIdentityDictionary[A, bool] = _ki.WeakKeyIdentityDictionary()

    d[a] = True

    data_copy = d._data.copy()
    d._data.clear()
    del a

    gc_collect_harder()  # would call sys.unraisablehook if there's a problem
    assert data_copy


def test_weak_key_identity_dict_remove_callback_selfref_expired() -> None:
    """We need to cover the KeyError in self._remove."""

    class A:
        def __eq__(self, other: object) -> bool:
            return False

    a = A()
    assert a != a
    d: _ki.WeakKeyIdentityDictionary[A, bool] = _ki.WeakKeyIdentityDictionary()

    d[a] = True

    data_copy = d._data.copy()
    wr_d = weakref.ref(d)
    del d
    gc_collect_harder()  # would call sys.unraisablehook if there's a problem
    assert wr_d() is None
    del a
    gc_collect_harder()
    assert data_copy


@_core.enable_ki_protection
async def _protected_async_gen_fn() -> AsyncGenerator[None, None]:
    yield


@_core.enable_ki_protection
async def _protected_async_fn() -> None:
    pass


@_core.enable_ki_protection
def _protected_gen_fn() -> Generator[None, None, None]:
    yield


@_core.disable_ki_protection
async def _unprotected_async_gen_fn() -> AsyncGenerator[None, None]:
    yield


@_core.disable_ki_protection
async def _unprotected_async_fn() -> None:
    pass


@_core.disable_ki_protection
def _unprotected_gen_fn() -> Generator[None, None, None]:
    yield


async def _consume_async_generator(agen: AsyncGenerator[None, None]) -> None:
    try:
        with pytest.raises(StopAsyncIteration):
            while True:
                await agen.asend(None)
    finally:
        await agen.aclose()


def _consume_function_for_coverage(
    fn: Callable[[], object],
) -> None:
    result = fn()
    if inspect.isasyncgen(result):
        result = _consume_async_generator(result)

    assert inspect.isgenerator(result) or inspect.iscoroutine(result)
    with pytest.raises(StopIteration):
        while True:
            result.send(None)


def test_enable_disable_ki_protection_passes_on_inspect_flags() -> None:
    assert inspect.isasyncgenfunction(_protected_async_gen_fn)
    _consume_function_for_coverage(_protected_async_gen_fn)
    assert inspect.iscoroutinefunction(_protected_async_fn)
    _consume_function_for_coverage(_protected_async_fn)
    assert inspect.isgeneratorfunction(_protected_gen_fn)
    _consume_function_for_coverage(_protected_gen_fn)
    assert inspect.isasyncgenfunction(_unprotected_async_gen_fn)
    _consume_function_for_coverage(_unprotected_async_gen_fn)
    assert inspect.iscoroutinefunction(_unprotected_async_fn)
    _consume_function_for_coverage(_unprotected_async_fn)
    assert inspect.isgeneratorfunction(_unprotected_gen_fn)
    _consume_function_for_coverage(_unprotected_gen_fn)
