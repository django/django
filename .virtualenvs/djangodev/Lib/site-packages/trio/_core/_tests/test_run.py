from __future__ import annotations

import contextvars
import functools
import gc
import sys
import threading
import time
import types
import weakref
from contextlib import ExitStack, contextmanager, suppress
from math import inf
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar, cast

import outcome
import pytest
import sniffio

from ... import _core
from ..._threads import to_thread_run_sync
from ..._timeouts import fail_after, sleep
from ...testing import (
    Matcher,
    RaisesGroup,
    Sequencer,
    assert_checkpoints,
    wait_all_tasks_blocked,
)
from .._run import DEADLINE_HEAP_MIN_PRUNE_THRESHOLD
from .tutil import (
    check_sequence_matches,
    create_asyncio_future_in_new_loop,
    gc_collect_harder,
    ignore_coroutine_never_awaited_warnings,
    restore_unraisablehook,
    slow,
)

if TYPE_CHECKING:
    from collections.abc import (
        AsyncGenerator,
        AsyncIterator,
        Awaitable,
        Callable,
        Generator,
    )

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup, ExceptionGroup


T = TypeVar("T")


# slightly different from _timeouts.sleep_forever because it returns the value
# its rescheduled with, which is really only useful for tests of
# rescheduling...
async def sleep_forever() -> object:
    return await _core.wait_task_rescheduled(lambda _: _core.Abort.SUCCEEDED)


def not_none(x: T | None) -> T:
    """Assert that this object is not None.

    This is just to satisfy type checkers, if this ever fails the test is broken.
    """
    assert x is not None
    return x


def test_basic() -> None:
    async def trivial(x: T) -> T:
        return x

    assert _core.run(trivial, 8) == 8

    with pytest.raises(TypeError):
        # Missing an argument
        _core.run(trivial)

    with pytest.raises(TypeError):
        # Not an async function
        _core.run(lambda: None)  # type: ignore

    async def trivial2(x: T) -> T:
        await _core.checkpoint()
        return x

    assert _core.run(trivial2, 1) == 1


def test_initial_task_error() -> None:
    async def main(x: object) -> NoReturn:
        raise ValueError(x)

    with pytest.raises(ValueError, match="^17$") as excinfo:
        _core.run(main, 17)
    assert excinfo.value.args == (17,)


def test_run_nesting() -> None:
    async def inception() -> None:
        async def main() -> None:  # pragma: no cover
            pass

        return _core.run(main)

    with pytest.raises(RuntimeError) as excinfo:
        _core.run(inception)
    assert "from inside" in str(excinfo.value)


async def test_nursery_warn_use_async_with() -> None:
    on = _core.open_nursery()
    with pytest.raises(RuntimeError) as excinfo:
        with on:  # type: ignore
            pass  # pragma: no cover
    excinfo.match(
        r"use 'async with open_nursery\(...\)', not 'with open_nursery\(...\)'"
    )

    # avoid unawaited coro.
    async with on:
        pass


async def test_nursery_main_block_error_basic() -> None:
    exc = ValueError("whoops")

    with RaisesGroup(Matcher(check=lambda e: e is exc)):
        async with _core.open_nursery():
            raise exc


async def test_child_crash_basic() -> None:
    my_exc = ValueError("uh oh")

    async def erroring() -> NoReturn:
        raise my_exc

    with RaisesGroup(Matcher(check=lambda e: e is my_exc)):
        # nursery.__aexit__ propagates exception from child back to parent
        async with _core.open_nursery() as nursery:
            nursery.start_soon(erroring)


async def test_basic_interleave() -> None:
    async def looper(whoami: str, record: list[tuple[str, int]]) -> None:
        for i in range(3):
            record.append((whoami, i))
            await _core.checkpoint()

    record: list[tuple[str, int]] = []
    async with _core.open_nursery() as nursery:
        nursery.start_soon(looper, "a", record)
        nursery.start_soon(looper, "b", record)

    check_sequence_matches(
        record, [{("a", 0), ("b", 0)}, {("a", 1), ("b", 1)}, {("a", 2), ("b", 2)}]
    )


def test_task_crash_propagation() -> None:
    looper_record: list[str] = []

    async def looper() -> None:
        try:
            while True:
                await _core.checkpoint()
        except _core.Cancelled:
            print("looper cancelled")
            looper_record.append("cancelled")

    async def crasher() -> NoReturn:
        raise ValueError("argh")

    async def main() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(looper)
            nursery.start_soon(crasher)

    with RaisesGroup(Matcher(ValueError, "^argh$")):
        _core.run(main)

    assert looper_record == ["cancelled"]


def test_main_and_task_both_crash() -> None:
    # If main crashes and there's also a task crash, then we get both in an
    # ExceptionGroup
    async def crasher() -> NoReturn:
        raise ValueError

    async def main() -> NoReturn:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(crasher)
            raise KeyError

    with RaisesGroup(ValueError, KeyError):
        _core.run(main)


def test_two_child_crashes() -> None:
    async def crasher(etype: type[Exception]) -> NoReturn:
        raise etype

    async def main() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(crasher, KeyError)
            nursery.start_soon(crasher, ValueError)

    with RaisesGroup(ValueError, KeyError):
        _core.run(main)


async def test_child_crash_wakes_parent() -> None:
    async def crasher() -> NoReturn:
        raise ValueError("this is a crash")

    with RaisesGroup(Matcher(ValueError, "^this is a crash$")):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(crasher)
            await sleep_forever()


async def test_reschedule() -> None:
    t1: _core.Task | None = None
    t2: _core.Task | None = None

    async def child1() -> None:
        nonlocal t1, t2
        t1 = _core.current_task()
        print("child1 start")
        x = await sleep_forever()
        print("child1 woke")
        assert x == 0
        print("child1 rescheduling t2")
        _core.reschedule(not_none(t2), outcome.Error(ValueError("error message")))
        print("child1 exit")

    async def child2() -> None:
        nonlocal t1, t2
        print("child2 start")
        t2 = _core.current_task()
        _core.reschedule(not_none(t1), outcome.Value(0))
        print("child2 sleep")
        with pytest.raises(ValueError, match="^error message$"):
            await sleep_forever()
        print("child2 successful exit")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child1)
        # let t1 run and fall asleep
        await _core.checkpoint()
        nursery.start_soon(child2)


async def test_current_time() -> None:
    t1 = _core.current_time()
    # Windows clock is pretty low-resolution -- appveyor tests fail unless we
    # sleep for a bit here.
    time.sleep(time.get_clock_info("perf_counter").resolution)  # noqa: ASYNC101
    t2 = _core.current_time()
    assert t1 < t2


async def test_current_time_with_mock_clock(mock_clock: _core.MockClock) -> None:
    start = mock_clock.current_time()
    assert mock_clock.current_time() == _core.current_time()
    assert mock_clock.current_time() == _core.current_time()
    mock_clock.jump(3.14)
    assert start + 3.14 == mock_clock.current_time() == _core.current_time()


async def test_current_clock(mock_clock: _core.MockClock) -> None:
    assert mock_clock is _core.current_clock()


async def test_current_task() -> None:
    parent_task = _core.current_task()

    async def child() -> None:
        assert not_none(_core.current_task().parent_nursery).parent_task is parent_task

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child)


async def test_root_task() -> None:
    root = not_none(_core.current_root_task())
    assert root.parent_nursery is root.eventual_parent_nursery is None


def test_out_of_context() -> None:
    with pytest.raises(RuntimeError):
        _core.current_task()
    with pytest.raises(RuntimeError):
        _core.current_time()


async def test_current_statistics(mock_clock: _core.MockClock) -> None:
    # Make sure all the early startup stuff has settled down
    await wait_all_tasks_blocked()

    # A child that sticks around to make some interesting stats:
    async def child() -> None:
        with suppress(_core.Cancelled):
            await sleep_forever()

    stats = _core.current_statistics()
    print(stats)
    # 2 system tasks + us
    assert stats.tasks_living == 3
    assert stats.run_sync_soon_queue_size == 0

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child)
        await wait_all_tasks_blocked()
        token = _core.current_trio_token()
        token.run_sync_soon(lambda: None)
        token.run_sync_soon(lambda: None, idempotent=True)
        stats = _core.current_statistics()
        print(stats)
        # 2 system tasks + us + child
        assert stats.tasks_living == 4
        # the exact value here might shift if we change how we do accounting
        # (currently it only counts tasks that we already know will be
        # runnable on the next pass), but still useful to at least test the
        # difference between now and after we wake up the child:
        assert stats.tasks_runnable == 0
        assert stats.run_sync_soon_queue_size == 2

        nursery.cancel_scope.cancel()
        stats = _core.current_statistics()
        print(stats)
        assert stats.tasks_runnable == 1

    # Give the child a chance to die and the run_sync_soon a chance to clear
    await _core.checkpoint()
    await _core.checkpoint()

    with _core.CancelScope(deadline=_core.current_time() + 5):
        stats = _core.current_statistics()
        print(stats)
        assert stats.seconds_to_next_deadline == 5
    stats = _core.current_statistics()
    print(stats)
    assert stats.seconds_to_next_deadline == inf


async def test_cancel_scope_repr(mock_clock: _core.MockClock) -> None:
    scope = _core.CancelScope()
    assert "unbound" in repr(scope)
    with scope:
        assert "active" in repr(scope)
        scope.deadline = _core.current_time() - 1
        assert "deadline is 1.00 seconds ago" in repr(scope)
        scope.deadline = _core.current_time() + 10
        assert "deadline is 10.00 seconds from now" in repr(scope)
        # when not in async context, can't get the current time
        assert "deadline" not in await to_thread_run_sync(repr, scope)
        scope.cancel()
        assert "cancelled" in repr(scope)
    assert "exited" in repr(scope)


def test_cancel_points() -> None:
    async def main1() -> None:
        with _core.CancelScope() as scope:
            await _core.checkpoint_if_cancelled()
            scope.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint_if_cancelled()

    _core.run(main1)

    async def main2() -> None:
        with _core.CancelScope() as scope:
            await _core.checkpoint()
            scope.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

    _core.run(main2)

    async def main3() -> None:
        with _core.CancelScope() as scope:
            scope.cancel()
            with pytest.raises(_core.Cancelled):
                await sleep_forever()

    _core.run(main3)

    async def main4() -> None:
        with _core.CancelScope() as scope:
            scope.cancel()
            await _core.cancel_shielded_checkpoint()
            await _core.cancel_shielded_checkpoint()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

    _core.run(main4)


async def test_cancel_edge_cases() -> None:
    with _core.CancelScope() as scope:
        # Two cancels in a row -- idempotent
        scope.cancel()
        scope.cancel()
        await _core.checkpoint()
    assert scope.cancel_called
    assert scope.cancelled_caught

    with _core.CancelScope() as scope:
        # Check level-triggering
        scope.cancel()
        with pytest.raises(_core.Cancelled):
            await sleep_forever()
        with pytest.raises(_core.Cancelled):
            await sleep_forever()


async def test_cancel_scope_exceptiongroup_filtering() -> None:
    async def crasher() -> NoReturn:
        raise KeyError

    # This is outside the outer scope, so all the Cancelled
    # exceptions should have been absorbed, leaving just a regular
    # KeyError from crasher(), wrapped in an ExceptionGroup
    with RaisesGroup(KeyError):
        with _core.CancelScope() as outer:
            # Since the outer scope became cancelled before the
            # nursery block exited, all cancellations inside the
            # nursery block continue propagating to reach the
            # outer scope.
            with RaisesGroup(
                _core.Cancelled, _core.Cancelled, _core.Cancelled, KeyError
            ) as excinfo:
                async with _core.open_nursery() as nursery:
                    # Two children that get cancelled by the nursery scope
                    nursery.start_soon(sleep_forever)  # t1
                    nursery.start_soon(sleep_forever)  # t2
                    nursery.cancel_scope.cancel()
                    with _core.CancelScope(shield=True):
                        await wait_all_tasks_blocked()
                    # One child that gets cancelled by the outer scope
                    nursery.start_soon(sleep_forever)  # t3
                    outer.cancel()
                    # And one that raises a different error
                    nursery.start_soon(crasher)  # t4
                # and then our __aexit__ also receives an outer Cancelled
            # reraise the exception caught by RaisesGroup for the
            # CancelScope to handle
            raise excinfo.value


async def test_precancelled_task() -> None:
    # a task that gets spawned into an already-cancelled nursery should begin
    # execution (https://github.com/python-trio/trio/issues/41), but get a
    # cancelled error at its first blocking call.
    record: list[str] = []

    async def blocker() -> None:
        record.append("started")
        await sleep_forever()

    async with _core.open_nursery() as nursery:
        nursery.cancel_scope.cancel()
        nursery.start_soon(blocker)
    assert record == ["started"]


async def test_cancel_shielding() -> None:
    with _core.CancelScope() as outer:
        with _core.CancelScope() as inner:
            await _core.checkpoint()
            outer.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

            assert inner.shield is False
            with pytest.raises(TypeError):
                inner.shield = "hello"  # type: ignore
            assert inner.shield is False

            inner.shield = True
            assert inner.shield is True
            # shield protects us from 'outer'
            await _core.checkpoint()

            with _core.CancelScope() as innerest:
                innerest.cancel()
                # but it doesn't protect us from scope inside inner
                with pytest.raises(_core.Cancelled):
                    await _core.checkpoint()
            await _core.checkpoint()

            inner.shield = False
            # can disable shield again
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

            # re-enable shield
            inner.shield = True
            await _core.checkpoint()
            # shield doesn't protect us from inner itself
            inner.cancel()
            # This should now raise, but be absorbed by the inner scope
            await _core.checkpoint()
        assert inner.cancelled_caught


# make sure that cancellation propagates immediately to all children
async def test_cancel_inheritance() -> None:
    record: set[str] = set()

    async def leaf(ident: str) -> None:
        try:
            await sleep_forever()
        except _core.Cancelled:
            record.add(ident)

    async def worker(ident: str) -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(leaf, ident + "-l1")
            nursery.start_soon(leaf, ident + "-l2")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(worker, "w1")
        nursery.start_soon(worker, "w2")
        nursery.cancel_scope.cancel()

    assert record == {"w1-l1", "w1-l2", "w2-l1", "w2-l2"}


async def test_cancel_shield_abort() -> None:
    with _core.CancelScope() as outer:
        async with _core.open_nursery() as nursery:
            outer.cancel()
            nursery.cancel_scope.shield = True
            # The outer scope is cancelled, but this task is protected by the
            # shield, so it manages to get to sleep
            record = []

            async def sleeper() -> None:
                record.append("sleeping")
                try:
                    await sleep_forever()
                except _core.Cancelled:
                    record.append("cancelled")

            nursery.start_soon(sleeper)
            await wait_all_tasks_blocked()
            assert record == ["sleeping"]
            # now when we unshield, it should abort the sleep.
            nursery.cancel_scope.shield = False
            # wait for the task to finish before entering the nursery
            # __aexit__, because __aexit__ could make it spuriously look like
            # this worked by cancelling the nursery scope. (When originally
            # written, without these last few lines, the test spuriously
            # passed, even though shield assignment was buggy.)
            with _core.CancelScope(shield=True):
                await wait_all_tasks_blocked()
                assert record == ["sleeping", "cancelled"]


async def test_basic_timeout(mock_clock: _core.MockClock) -> None:
    start = _core.current_time()
    with _core.CancelScope() as scope:
        assert scope.deadline == inf
        scope.deadline = start + 1
        assert scope.deadline == start + 1
    assert not scope.cancel_called
    mock_clock.jump(2)
    await _core.checkpoint()
    await _core.checkpoint()
    await _core.checkpoint()
    assert not scope.cancel_called

    start = _core.current_time()
    with _core.CancelScope(deadline=start + 1) as scope:
        mock_clock.jump(2)
        await sleep_forever()
    # But then the scope swallowed the exception... but we can still see it
    # here:
    assert scope.cancel_called
    assert scope.cancelled_caught

    # changing deadline
    start = _core.current_time()
    with _core.CancelScope() as scope:
        await _core.checkpoint()
        scope.deadline = start + 10
        await _core.checkpoint()
        mock_clock.jump(5)
        await _core.checkpoint()
        scope.deadline = start + 1
        with pytest.raises(_core.Cancelled):
            await _core.checkpoint()
        with pytest.raises(_core.Cancelled):
            await _core.checkpoint()


async def test_cancel_scope_nesting() -> None:
    # Nested scopes: if two triggering at once, the outer one wins
    with _core.CancelScope() as scope1:
        with _core.CancelScope() as scope2:
            with _core.CancelScope() as scope3:
                scope3.cancel()
                scope2.cancel()
                await sleep_forever()
    assert scope3.cancel_called
    assert not scope3.cancelled_caught
    assert scope2.cancel_called
    assert scope2.cancelled_caught
    assert not scope1.cancel_called
    assert not scope1.cancelled_caught

    # shielding
    with _core.CancelScope() as scope1:
        with _core.CancelScope() as scope2:
            scope1.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()
            scope2.shield = True
            await _core.checkpoint()
            scope2.cancel()
            with pytest.raises(_core.Cancelled):
                await _core.checkpoint()

    # if a scope is pending, but then gets popped off the stack, then it
    # isn't delivered
    with _core.CancelScope() as scope:
        scope.cancel()
        await _core.cancel_shielded_checkpoint()
    await _core.checkpoint()
    assert not scope.cancelled_caught


# Regression test for https://github.com/python-trio/trio/issues/1175
async def test_unshield_while_cancel_propagating() -> None:
    with _core.CancelScope() as outer:
        with _core.CancelScope() as inner:
            outer.cancel()
            try:
                await _core.checkpoint()
            finally:
                inner.shield = True
    assert outer.cancelled_caught
    assert not inner.cancelled_caught


async def test_cancel_unbound() -> None:
    async def sleep_until_cancelled(scope: _core.CancelScope) -> None:
        with scope, fail_after(1):
            await sleep_forever()

    # Cancel before entry
    scope = _core.CancelScope()
    scope.cancel()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(sleep_until_cancelled, scope)

    # Cancel after entry
    scope = _core.CancelScope()
    async with _core.open_nursery() as nursery:
        nursery.start_soon(sleep_until_cancelled, scope)
        await wait_all_tasks_blocked()
        scope.cancel()

    # Shield before entry
    scope = _core.CancelScope()
    scope.shield = True
    with _core.CancelScope() as outer, scope:
        outer.cancel()
        await _core.checkpoint()
        scope.shield = False
        with pytest.raises(_core.Cancelled):
            await _core.checkpoint()

    # Can't reuse
    with _core.CancelScope() as scope:
        await _core.checkpoint()
    scope.cancel()
    await _core.checkpoint()
    assert scope.cancel_called
    assert not scope.cancelled_caught
    with pytest.raises(RuntimeError) as exc_info:
        with scope:
            pass  # pragma: no cover
    assert "single 'with' block" in str(exc_info.value)

    # Can't reenter
    with _core.CancelScope() as scope:
        with pytest.raises(RuntimeError) as exc_info:
            with scope:
                pass  # pragma: no cover
        assert "single 'with' block" in str(exc_info.value)

    # Can't enter from multiple tasks simultaneously
    scope = _core.CancelScope()

    async def enter_scope() -> None:
        with scope:
            await sleep_forever()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(enter_scope, name="this one")
        await wait_all_tasks_blocked()

        with pytest.raises(RuntimeError) as exc_info:
            with scope:
                pass  # pragma: no cover
        assert "single 'with' block" in str(exc_info.value)
        nursery.cancel_scope.cancel()

    # If not yet entered, cancel_called is true when the deadline has passed
    # even if cancel() hasn't been called yet
    scope = _core.CancelScope(deadline=_core.current_time() + 1)
    assert not scope.cancel_called
    scope.deadline -= 1
    assert scope.cancel_called
    scope.deadline += 1
    assert scope.cancel_called  # never become un-cancelled


async def test_cancel_scope_misnesting() -> None:
    outer = _core.CancelScope()
    inner = _core.CancelScope()
    with ExitStack() as stack:
        stack.enter_context(outer)
        with inner:
            with pytest.raises(RuntimeError, match="still within its child"):
                stack.close()
        # No further error is raised when exiting the inner context

    # If there are other tasks inside the abandoned part of the cancel tree,
    # they get cancelled when the misnesting is detected
    async def task1() -> None:
        with pytest.raises(_core.Cancelled):
            await sleep_forever()

    # Even if inside another cancel scope
    async def task2() -> None:
        with _core.CancelScope():
            with pytest.raises(_core.Cancelled):
                await sleep_forever()

    with ExitStack() as stack:
        stack.enter_context(_core.CancelScope())
        async with _core.open_nursery() as nursery:
            nursery.start_soon(task1)
            nursery.start_soon(task2)
            await wait_all_tasks_blocked()
            with pytest.raises(RuntimeError, match="still within its child"):
                stack.close()

    # Variant that makes the child tasks direct children of the scope
    # that noticed the misnesting:
    nursery_mgr = _core.open_nursery()
    nursery = await nursery_mgr.__aenter__()
    try:
        nursery.start_soon(task1)
        nursery.start_soon(task2)
        nursery.start_soon(sleep_forever)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.__exit__(None, None, None)
    finally:
        with pytest.raises(
            RuntimeError, match="which had already been exited"
        ) as exc_info:
            await nursery_mgr.__aexit__(*sys.exc_info())

    def no_context(exc: RuntimeError) -> bool:
        return exc.__context__ is None

    msg = "closed before the task exited"
    group = RaisesGroup(
        Matcher(RuntimeError, match=msg, check=no_context),
        Matcher(RuntimeError, match=msg, check=no_context),
        # sleep_forever
        Matcher(
            RuntimeError,
            match=msg,
            check=lambda x: isinstance(x.__context__, _core.Cancelled),
        ),
    )
    assert group.matches(exc_info.value.__context__)

    # Trying to exit a cancel scope from an unrelated task raises an error
    # without affecting any state
    async def task3(task_status: _core.TaskStatus[_core.CancelScope]) -> None:
        with _core.CancelScope() as scope:
            task_status.started(scope)
            await sleep_forever()

    async with _core.open_nursery() as nursery:
        scope: _core.CancelScope = await nursery.start(task3)
        with pytest.raises(RuntimeError, match="from unrelated"):
            scope.__exit__(None, None, None)
        scope.cancel()


@slow
async def test_timekeeping() -> None:
    # probably a good idea to use a real clock for *one* test anyway...
    TARGET = 1.0
    # give it a few tries in case of random CI server flakiness
    for _ in range(4):
        real_start = time.perf_counter()
        with _core.CancelScope() as scope:
            scope.deadline = _core.current_time() + TARGET
            await sleep_forever()
        real_duration = time.perf_counter() - real_start
        accuracy = real_duration / TARGET
        print(accuracy)
        # Actual time elapsed should always be >= target time
        # (== is possible depending on system behavior for time.perf_counter resolution
        if 1.0 <= accuracy < 2:  # pragma: no branch
            break
    else:  # pragma: no cover
        raise AssertionError()


async def test_failed_abort() -> None:
    stubborn_task: _core.Task | None = None
    stubborn_scope: _core.CancelScope | None = None
    record: list[str] = []

    async def stubborn_sleeper() -> None:
        nonlocal stubborn_task, stubborn_scope
        stubborn_task = _core.current_task()
        with _core.CancelScope() as scope:
            stubborn_scope = scope
            record.append("sleep")
            x = await _core.wait_task_rescheduled(lambda _: _core.Abort.FAILED)
            assert x == 1
            record.append("woke")
            try:
                await _core.checkpoint_if_cancelled()
            except _core.Cancelled:
                record.append("cancelled")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(stubborn_sleeper)
        await wait_all_tasks_blocked()
        assert record == ["sleep"]
        not_none(stubborn_scope).cancel()
        await wait_all_tasks_blocked()
        # cancel didn't wake it up
        assert record == ["sleep"]
        # wake it up again by hand
        _core.reschedule(not_none(stubborn_task), outcome.Value(1))
    assert record == ["sleep", "woke", "cancelled"]


@restore_unraisablehook()
def test_broken_abort() -> None:
    async def main() -> None:
        # These yields are here to work around an annoying warning -- we're
        # going to crash the main loop, and if we (by chance) do this before
        # the run_sync_soon task runs for the first time, then Python gives us
        # a spurious warning about it not being awaited. (I mean, the warning
        # is correct, but here we're testing our ability to deliver a
        # semi-meaningful error after things have gone totally pear-shaped, so
        # it's not relevant.) By letting the run_sync_soon_task run first, we
        # avoid the warning.
        await _core.checkpoint()
        await _core.checkpoint()
        with _core.CancelScope() as scope:
            scope.cancel()
            # None is not a legal return value here
            await _core.wait_task_rescheduled(lambda _: None)  # type: ignore

    with pytest.raises(_core.TrioInternalError):
        _core.run(main)

    # Because this crashes, various __del__ methods print complaints on
    # stderr. Make sure that they get run now, so the output is attached to
    # this test.
    gc_collect_harder()


@restore_unraisablehook()
def test_error_in_run_loop() -> None:
    # Blow stuff up real good to check we at least get a TrioInternalError
    async def main() -> None:
        task = _core.current_task()
        task._schedule_points = "hello!"  # type: ignore
        await _core.checkpoint()

    with ignore_coroutine_never_awaited_warnings():
        with pytest.raises(_core.TrioInternalError):
            _core.run(main)


async def test_spawn_system_task() -> None:
    record: list[tuple[str, int]] = []

    async def system_task(x: int) -> None:
        record.append(("x", x))
        record.append(("ki", _core.currently_ki_protected()))
        await _core.checkpoint()

    _core.spawn_system_task(system_task, 1)
    await wait_all_tasks_blocked()
    assert record == [("x", 1), ("ki", True)]


# intentionally make a system task crash
def test_system_task_crash() -> None:
    async def crasher() -> NoReturn:
        raise KeyError

    async def main() -> None:
        _core.spawn_system_task(crasher)
        await sleep_forever()

    with pytest.raises(_core.TrioInternalError):
        _core.run(main)


def test_system_task_crash_ExceptionGroup() -> None:
    async def crasher1() -> NoReturn:
        raise KeyError

    async def crasher2() -> NoReturn:
        raise ValueError

    async def system_task() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(crasher1)
            nursery.start_soon(crasher2)

    async def main() -> None:
        _core.spawn_system_task(system_task)
        await sleep_forever()

    # TrioInternalError is not wrapped
    with pytest.raises(_core.TrioInternalError) as excinfo:
        _core.run(main)

    # the first exceptiongroup is from the first nursery opened in Runner.init()
    # the second exceptiongroup is from the second nursery opened in Runner.init()
    # the third exceptongroup is from the nursery defined in `system_task` above
    assert RaisesGroup(RaisesGroup(RaisesGroup(KeyError, ValueError))).matches(
        excinfo.value.__cause__
    )


def test_system_task_crash_plus_Cancelled() -> None:
    # Set up a situation where a system task crashes with a
    # ExceptionGroup([Cancelled, ValueError])
    async def crasher() -> None:
        try:
            await sleep_forever()
        except _core.Cancelled:
            raise ValueError from None

    async def cancelme() -> None:
        await sleep_forever()

    async def system_task() -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(crasher)
            nursery.start_soon(cancelme)

    async def main() -> None:
        _core.spawn_system_task(system_task)
        # then we exit, triggering a cancellation

    with pytest.raises(_core.TrioInternalError) as excinfo:
        _core.run(main)

    # See explanation for triple-wrap in test_system_task_crash_ExceptionGroup
    assert RaisesGroup(RaisesGroup(RaisesGroup(ValueError))).matches(
        excinfo.value.__cause__
    )


def test_system_task_crash_KeyboardInterrupt() -> None:
    async def ki() -> NoReturn:
        raise KeyboardInterrupt

    async def main() -> None:
        _core.spawn_system_task(ki)
        await sleep_forever()

    with pytest.raises(_core.TrioInternalError) as excinfo:
        _core.run(main)
    # "Only" double-wrapped since ki() doesn't create an exceptiongroup
    assert RaisesGroup(RaisesGroup(KeyboardInterrupt)).matches(excinfo.value.__cause__)


# This used to fail because checkpoint was a yield followed by an immediate
# reschedule. So we had:
# 1) this task yields
# 2) this task is rescheduled
# ...
# 3) next iteration of event loop starts, runs timeouts
# 4) this task has timed out
# 5) ...but it's on the run queue, so the timeout is queued to be delivered
#    the next time that it's blocked.
async def test_yield_briefly_checks_for_timeout(mock_clock: _core.MockClock) -> None:
    with _core.CancelScope(deadline=_core.current_time() + 5):
        await _core.checkpoint()
        mock_clock.jump(10)
        with pytest.raises(_core.Cancelled):
            await _core.checkpoint()


# This tests that sys.exc_info is properly saved/restored as we swap between
# tasks. It turns out that the interpreter automagically handles this for us
# so there's no special code in Trio required to pass this test, but it's
# still nice to know that it works :-).
#
# Update: it turns out I was right to be nervous! see the next test...
async def test_exc_info() -> None:
    record: list[str] = []
    seq = Sequencer()

    async def child1() -> None:
        async with seq(0):
            pass  # we don't yield until seq(2) below
        record.append("child1 raise")
        with pytest.raises(ValueError, match="^child1$") as excinfo:
            try:
                raise ValueError("child1")
            except ValueError:
                record.append("child1 sleep")
                async with seq(2):
                    pass
                assert "child2 wake" in record
                record.append("child1 re-raise")
                raise
        assert excinfo.value.__context__ is None
        record.append("child1 success")

    async def child2() -> None:
        async with seq(1):
            pass  # we don't yield until seq(3) below
        assert "child1 sleep" in record
        record.append("child2 wake")
        assert sys.exc_info() == (None, None, None)
        with pytest.raises(KeyError) as excinfo:
            try:
                raise KeyError("child2")
            except KeyError:
                record.append("child2 sleep again")
                async with seq(3):
                    pass
                assert "child1 re-raise" in record
                record.append("child2 re-raise")
                raise
        assert excinfo.value.__context__ is None
        record.append("child2 success")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child1)
        nursery.start_soon(child2)

    assert record == [
        "child1 raise",
        "child1 sleep",
        "child2 wake",
        "child2 sleep again",
        "child1 re-raise",
        "child1 success",
        "child2 re-raise",
        "child2 success",
    ]


# On all CPython versions (at time of writing), using .throw() to raise an
# exception inside a coroutine/generator can cause the original `exc_info` state
# to be lost, so things like re-raising and exception chaining are broken unless
# Trio implements its workaround. At time of writing, CPython main (3.13-dev)
# and every CPython release (excluding releases for old Python versions not
# supported by Trio) is affected (albeit in differing ways).
#
# If the `ValueError()` gets sent in via `throw` and is suppressed, then CPython
# loses track of the original `exc_info`:
#   https://bugs.python.org/issue25612 (Example 1)
#   https://bugs.python.org/issue29587 (Example 2)
# This is fixed in CPython >= 3.7.
async def test_exc_info_after_throw_suppressed() -> None:
    child_task: _core.Task | None = None

    async def child() -> None:
        nonlocal child_task
        child_task = _core.current_task()

        try:
            raise KeyError
        except KeyError:
            with suppress(ValueError):
                await sleep_forever()
            raise

    with RaisesGroup(Matcher(KeyError, check=lambda e: e.__context__ is None)):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(child)
            await wait_all_tasks_blocked()
            _core.reschedule(not_none(child_task), outcome.Error(ValueError()))


# Similar to previous test -- if the `ValueError()` gets sent in via 'throw' and
# propagates out, then CPython doesn't set its `__context__` so normal implicit
# exception chaining is broken:
#   https://bugs.python.org/issue25612 (Example 2)
#   https://bugs.python.org/issue25683
#   https://bugs.python.org/issue29587 (Example 1)
# This is fixed in CPython >= 3.9.
async def test_exception_chaining_after_throw() -> None:
    child_task: _core.Task | None = None

    async def child() -> None:
        nonlocal child_task
        child_task = _core.current_task()

        try:
            raise KeyError
        except KeyError:
            await sleep_forever()

    with RaisesGroup(
        Matcher(ValueError, "error text", lambda e: isinstance(e.__context__, KeyError))
    ):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(child)
            await wait_all_tasks_blocked()
            _core.reschedule(
                not_none(child_task), outcome.Error(ValueError("error text"))
            )


# Similar to previous tests -- if the `ValueError()` gets sent into an inner
# `await` via 'throw' and is suppressed there, then CPython loses track of
# `exc_info` in the inner coroutine:
#   https://github.com/python/cpython/issues/108668
# This is unfixed in CPython at time of writing.
async def test_exc_info_after_throw_to_inner_suppressed() -> None:
    child_task: _core.Task | None = None

    async def child() -> None:
        nonlocal child_task
        child_task = _core.current_task()

        try:
            raise KeyError
        except KeyError as exc:
            await inner(exc)
            raise

    async def inner(exc: BaseException) -> None:
        with suppress(ValueError):
            await sleep_forever()
        assert not_none(sys.exc_info()[1]) is exc

    with RaisesGroup(Matcher(KeyError, check=lambda e: e.__context__ is None)):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(child)
            await wait_all_tasks_blocked()
            _core.reschedule(not_none(child_task), outcome.Error(ValueError()))


# Similar to previous tests -- if the `ValueError()` gets sent into an inner
# `await` via `throw` and propagates out, then CPython incorrectly sets its
# `__context__` so normal implicit exception chaining is broken:
#   https://bugs.python.org/issue40694
# This is unfixed in CPython at time of writing.
async def test_exception_chaining_after_throw_to_inner() -> None:
    child_task: _core.Task | None = None

    async def child() -> None:
        nonlocal child_task
        child_task = _core.current_task()

        try:
            raise KeyError
        except KeyError:
            await inner()

    async def inner() -> None:
        try:
            raise IndexError
        except IndexError:
            await sleep_forever()

    with RaisesGroup(
        Matcher(
            ValueError,
            "^Unique Text$",
            lambda e: isinstance(e.__context__, IndexError)
            and isinstance(e.__context__.__context__, KeyError),
        )
    ):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(child)
            await wait_all_tasks_blocked()
            _core.reschedule(
                not_none(child_task), outcome.Error(ValueError("Unique Text"))
            )


async def test_nursery_exception_chaining_doesnt_make_context_loops() -> None:
    async def crasher() -> NoReturn:
        raise KeyError

    # the ExceptionGroup should not have the KeyError or ValueError as context
    with RaisesGroup(ValueError, KeyError, check=lambda x: x.__context__ is None):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(crasher)
            raise ValueError


def test_TrioToken_identity() -> None:
    async def get_and_check_token() -> _core.TrioToken:
        token = _core.current_trio_token()
        # Two calls in the same run give the same object
        assert token is _core.current_trio_token()
        return token

    t1 = _core.run(get_and_check_token)
    t2 = _core.run(get_and_check_token)
    assert t1 is not t2
    assert t1 != t2
    assert hash(t1) != hash(t2)


async def test_TrioToken_run_sync_soon_basic() -> None:
    record: list[tuple[str, int]] = []

    def cb(x: int) -> None:
        record.append(("cb", x))

    token = _core.current_trio_token()
    token.run_sync_soon(cb, 1)
    assert not record
    await wait_all_tasks_blocked()
    assert record == [("cb", 1)]


def test_TrioToken_run_sync_soon_too_late() -> None:
    token: _core.TrioToken | None = None

    async def main() -> None:
        nonlocal token
        token = _core.current_trio_token()

    _core.run(main)
    with pytest.raises(_core.RunFinishedError):
        not_none(token).run_sync_soon(lambda: None)  # pragma: no branch


async def test_TrioToken_run_sync_soon_idempotent() -> None:
    record: list[int] = []

    def cb(x: int) -> None:
        record.append(x)

    token = _core.current_trio_token()
    token.run_sync_soon(cb, 1)
    token.run_sync_soon(cb, 1, idempotent=True)
    token.run_sync_soon(cb, 1, idempotent=True)
    token.run_sync_soon(cb, 1, idempotent=True)
    token.run_sync_soon(cb, 2, idempotent=True)
    token.run_sync_soon(cb, 2, idempotent=True)
    await wait_all_tasks_blocked()
    assert len(record) == 3
    assert sorted(record) == [1, 1, 2]

    # ordering test
    record = []
    for _ in range(3):
        for i in range(100):
            token.run_sync_soon(cb, i, idempotent=True)
    await wait_all_tasks_blocked()
    # We guarantee FIFO
    assert record == list(range(100))


def test_TrioToken_run_sync_soon_idempotent_requeue() -> None:
    # We guarantee that if a call has finished, queueing it again will call it
    # again. Due to the lack of synchronization, this effectively means that
    # we have to guarantee that once a call has *started*, queueing it again
    # will call it again. Also this is much easier to test :-)
    record: list[None] = []

    def redo(token: _core.TrioToken) -> None:
        record.append(None)
        with suppress(_core.RunFinishedError):
            token.run_sync_soon(redo, token, idempotent=True)

    async def main() -> None:
        token = _core.current_trio_token()
        token.run_sync_soon(redo, token, idempotent=True)
        await _core.checkpoint()
        await _core.checkpoint()
        await _core.checkpoint()

    _core.run(main)

    assert len(record) >= 2


def test_TrioToken_run_sync_soon_after_main_crash() -> None:
    record: list[str] = []

    async def main() -> None:
        token = _core.current_trio_token()
        # After main exits but before finally cleaning up, callback processed
        # normally
        token.run_sync_soon(lambda: record.append("sync-cb"))
        raise ValueError("error text")

    with pytest.raises(ValueError, match="^error text$"):
        _core.run(main)

    assert record == ["sync-cb"]


def test_TrioToken_run_sync_soon_crashes() -> None:
    record: set[str] = set()

    async def main() -> None:
        token = _core.current_trio_token()
        token.run_sync_soon(lambda: {}["nope"])  # type: ignore[index]
        # check that a crashing run_sync_soon callback doesn't stop further
        # calls to run_sync_soon
        token.run_sync_soon(lambda: record.add("2nd run_sync_soon ran"))
        try:
            await sleep_forever()
        except _core.Cancelled:
            record.add("cancelled!")

    with pytest.raises(_core.TrioInternalError) as excinfo:
        _core.run(main)
    # the first exceptiongroup is from the first nursery opened in Runner.init()
    # the second exceptiongroup is from the second nursery opened in Runner.init()
    assert RaisesGroup(RaisesGroup(KeyError)).matches(excinfo.value.__cause__)
    assert record == {"2nd run_sync_soon ran", "cancelled!"}


async def test_TrioToken_run_sync_soon_FIFO() -> None:
    N = 100
    record = []
    token = _core.current_trio_token()
    for i in range(N):
        token.run_sync_soon(lambda j: record.append(j), i)
    await wait_all_tasks_blocked()
    assert record == list(range(N))


def test_TrioToken_run_sync_soon_starvation_resistance() -> None:
    # Even if we push callbacks in from callbacks, so that the callback queue
    # never empties out, then we still can't starve out other tasks from
    # running.
    token: _core.TrioToken | None = None
    record: list[tuple[str, int]] = []

    def naughty_cb(i: int) -> None:
        try:
            not_none(token).run_sync_soon(naughty_cb, i + 1)
        except _core.RunFinishedError:
            record.append(("run finished", i))

    async def main() -> None:
        nonlocal token
        token = _core.current_trio_token()
        token.run_sync_soon(naughty_cb, 0)
        record.append(("starting", 0))
        for _ in range(20):
            await _core.checkpoint()

    _core.run(main)
    assert len(record) == 2
    assert record[0] == ("starting", 0)
    assert record[1][0] == "run finished"
    assert record[1][1] >= 19


def test_TrioToken_run_sync_soon_threaded_stress_test() -> None:
    cb_counter = 0

    def cb() -> None:
        nonlocal cb_counter
        cb_counter += 1

    def stress_thread(token: _core.TrioToken) -> None:
        try:
            while True:
                token.run_sync_soon(cb)
                time.sleep(0)
        except _core.RunFinishedError:
            pass

    async def main() -> None:
        token = _core.current_trio_token()
        thread = threading.Thread(target=stress_thread, args=(token,))
        thread.start()
        for _ in range(10):
            start_value = cb_counter
            while cb_counter == start_value:
                await sleep(0.01)

    _core.run(main)
    print(cb_counter)


async def test_TrioToken_run_sync_soon_massive_queue() -> None:
    # There are edge cases in the wakeup fd code when the wakeup fd overflows,
    # so let's try to make that happen. This is also just a good stress test
    # in general. (With the current-as-of-2017-02-14 code using a socketpair
    # with minimal buffer, Linux takes 6 wakeups to fill the buffer and macOS
    # takes 1 wakeup. So 1000 is overkill if anything. Windows OTOH takes
    # ~600,000 wakeups, but has the same code paths...)
    COUNT = 1000
    token = _core.current_trio_token()
    counter = [0]

    def cb(i: int) -> None:
        # This also tests FIFO ordering of callbacks
        assert counter[0] == i
        counter[0] += 1

    for i in range(COUNT):
        token.run_sync_soon(cb, i)
    await wait_all_tasks_blocked()
    assert counter[0] == COUNT


def test_TrioToken_run_sync_soon_late_crash() -> None:
    # Crash after system nursery is closed -- easiest way to do that is
    # from an async generator finalizer.
    record: list[str] = []
    saved: list[AsyncGenerator[int, None]] = []

    async def agen() -> AsyncGenerator[int, None]:
        token = _core.current_trio_token()
        try:
            yield 1
        finally:
            token.run_sync_soon(lambda: {}["nope"])  # type: ignore[index]
            token.run_sync_soon(lambda: record.append("2nd ran"))

    async def main() -> None:
        saved.append(agen())
        await saved[-1].asend(None)
        record.append("main exiting")

    with pytest.raises(_core.TrioInternalError) as excinfo:
        _core.run(main)

    assert RaisesGroup(KeyError).matches(excinfo.value.__cause__)
    assert record == ["main exiting", "2nd ran"]


async def test_slow_abort_basic() -> None:
    with _core.CancelScope() as scope:
        scope.cancel()

        task = _core.current_task()
        token = _core.current_trio_token()

        def slow_abort(raise_cancel: _core.RaiseCancelT) -> _core.Abort:
            result = outcome.capture(raise_cancel)
            token.run_sync_soon(_core.reschedule, task, result)
            return _core.Abort.FAILED

        with pytest.raises(_core.Cancelled):
            await _core.wait_task_rescheduled(slow_abort)


async def test_slow_abort_edge_cases() -> None:
    record: list[str] = []

    async def slow_aborter() -> None:
        task = _core.current_task()
        token = _core.current_trio_token()

        def slow_abort(raise_cancel: _core.RaiseCancelT) -> _core.Abort:
            record.append("abort-called")
            result = outcome.capture(raise_cancel)
            token.run_sync_soon(_core.reschedule, task, result)
            return _core.Abort.FAILED

        record.append("sleeping")
        with pytest.raises(_core.Cancelled):
            await _core.wait_task_rescheduled(slow_abort)
        record.append("cancelled")
        # blocking again, this time it's okay, because we're shielded
        await _core.checkpoint()
        record.append("done")

    with _core.CancelScope() as outer1:
        with _core.CancelScope() as outer2:
            async with _core.open_nursery() as nursery:
                # So we have a task blocked on an operation that can't be
                # aborted immediately
                nursery.start_soon(slow_aborter)
                await wait_all_tasks_blocked()
                assert record == ["sleeping"]
                # And then we cancel it, so the abort callback gets run
                outer1.cancel()
                assert record == ["sleeping", "abort-called"]
                # In fact that happens twice! (This used to cause the abort
                # callback to be run twice)
                outer2.cancel()
                assert record == ["sleeping", "abort-called"]
                # But then before the abort finishes, the task gets shielded!
                nursery.cancel_scope.shield = True
                # Now we wait for the task to finish...
            # The cancellation was delivered, even though it was shielded
            assert record == ["sleeping", "abort-called", "cancelled", "done"]


async def test_task_tree_introspection() -> None:
    tasks: dict[str, _core.Task] = {}
    nurseries: dict[str, _core.Nursery] = {}

    async def parent(
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        tasks["parent"] = _core.current_task()

        assert tasks["parent"].child_nurseries == []

        async with _core.open_nursery() as nursery1:
            async with _core.open_nursery() as nursery2:
                assert tasks["parent"].child_nurseries == [nursery1, nursery2]

        assert tasks["parent"].child_nurseries == []

        nursery: _core.Nursery | None
        async with _core.open_nursery() as nursery:
            nurseries["parent"] = nursery
            await nursery.start(child1)

        # Upward links survive after tasks/nurseries exit
        assert nurseries["parent"].parent_task is tasks["parent"]
        assert tasks["child1"].parent_nursery is nurseries["parent"]
        assert nurseries["child1"].parent_task is tasks["child1"]
        assert tasks["child2"].parent_nursery is nurseries["child1"]

        nursery = _core.current_task().parent_nursery
        # Make sure that chaining eventually gives a nursery of None (and not,
        # for example, an error)
        while nursery is not None:
            t = nursery.parent_task
            nursery = t.parent_nursery

    async def child2() -> None:
        tasks["child2"] = _core.current_task()
        assert tasks["parent"].child_nurseries == [nurseries["parent"]]
        assert nurseries["parent"].child_tasks == frozenset({tasks["child1"]})
        assert tasks["child1"].child_nurseries == [nurseries["child1"]]
        assert nurseries["child1"].child_tasks == frozenset({tasks["child2"]})
        assert tasks["child2"].child_nurseries == []

    async def child1(
        *,
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        me = tasks["child1"] = _core.current_task()
        assert not_none(me.parent_nursery).parent_task is tasks["parent"]
        assert me.parent_nursery is not nurseries["parent"]
        assert me.eventual_parent_nursery is nurseries["parent"]
        task_status.started()
        assert me.parent_nursery is nurseries["parent"]
        assert me.eventual_parent_nursery is None

        # Wait for the start() call to return and close its internal nursery, to
        # ensure consistent results in child2:
        await _core.wait_all_tasks_blocked()

        async with _core.open_nursery() as nursery:
            nurseries["child1"] = nursery
            nursery.start_soon(child2)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(parent)

    # There are no pending starts, so no one should have a non-None
    # eventual_parent_nursery
    for task in tasks.values():
        assert task.eventual_parent_nursery is None


async def test_nursery_closure() -> None:
    async def child1(nursery: _core.Nursery) -> None:
        # We can add new tasks to the nursery even after entering __aexit__,
        # so long as there are still tasks running
        nursery.start_soon(child2)

    async def child2() -> None:
        pass

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child1, nursery)

    # But once we've left __aexit__, the nursery is closed
    with pytest.raises(RuntimeError):
        nursery.start_soon(child2)


async def test_spawn_name() -> None:
    async def func1(expected: str) -> None:
        task = _core.current_task()
        assert expected in task.name

    async def func2() -> None:  # pragma: no cover
        pass

    async def check(spawn_fn: Callable[..., object]) -> None:
        spawn_fn(func1, "func1")
        spawn_fn(func1, "func2", name=func2)
        spawn_fn(func1, "func3", name="func3")
        spawn_fn(functools.partial(func1, "func1"))
        spawn_fn(func1, "object", name=object())

    async with _core.open_nursery() as nursery:
        await check(nursery.start_soon)
    await check(_core.spawn_system_task)


async def test_current_effective_deadline(mock_clock: _core.MockClock) -> None:
    assert _core.current_effective_deadline() == inf

    with _core.CancelScope(deadline=5) as scope1:
        with _core.CancelScope(deadline=10) as scope2:
            assert _core.current_effective_deadline() == 5
            scope2.deadline = 3
            assert _core.current_effective_deadline() == 3
            scope2.deadline = 10
            assert _core.current_effective_deadline() == 5
            scope2.shield = True
            assert _core.current_effective_deadline() == 10
            scope2.shield = False
            assert _core.current_effective_deadline() == 5
            scope1.cancel()
            assert _core.current_effective_deadline() == -inf
            scope2.shield = True
            assert _core.current_effective_deadline() == 10
        assert _core.current_effective_deadline() == -inf
    assert _core.current_effective_deadline() == inf


def test_nice_error_on_bad_calls_to_run_or_spawn() -> None:
    def bad_call_run(
        func: Callable[..., Awaitable[object]],
        *args: tuple[object, ...],
    ) -> None:
        _core.run(func, *args)

    def bad_call_spawn(
        func: Callable[..., Awaitable[object]],
        *args: tuple[object, ...],
    ) -> None:
        async def main() -> None:
            async with _core.open_nursery() as nursery:
                nursery.start_soon(func, *args)

        _core.run(main)

    async def f() -> None:  # pragma: no cover
        pass

    async def async_gen(arg: T) -> AsyncGenerator[T, None]:  # pragma: no cover
        yield arg

    # If/when RaisesGroup/Matcher is added to pytest in some form this test can be
    # rewritten to use a loop again, and avoid specifying the exceptions twice in
    # different ways
    with pytest.raises(
        TypeError,
        match="^Trio was expecting an async function, but instead it got a coroutine object <.*>",
    ):
        bad_call_run(f())  # type: ignore[arg-type]
    with pytest.raises(
        TypeError, match="expected an async function but got an async generator"
    ):
        bad_call_run(async_gen, 0)  # type: ignore

    # bad_call_spawn calls the function inside a nursery, so the exception will be
    # wrapped in an exceptiongroup
    with RaisesGroup(Matcher(TypeError, "expecting an async function")):
        bad_call_spawn(f())  # type: ignore[arg-type]

    with RaisesGroup(
        Matcher(TypeError, "expected an async function but got an async generator")
    ):
        bad_call_spawn(async_gen, 0)  # type: ignore


def test_calling_asyncio_function_gives_nice_error() -> None:
    async def child_xyzzy() -> None:
        await create_asyncio_future_in_new_loop()

    async def misguided() -> None:
        await child_xyzzy()

    with pytest.raises(TypeError, match="asyncio") as excinfo:
        _core.run(misguided)

    # The traceback should point to the location of the foreign await
    assert any(  # pragma: no branch
        entry.name == "child_xyzzy" for entry in excinfo.traceback
    )


async def test_asyncio_function_inside_nursery_does_not_explode() -> None:
    # Regression test for https://github.com/python-trio/trio/issues/552
    with RaisesGroup(Matcher(TypeError, "asyncio")):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleep_forever)
            await create_asyncio_future_in_new_loop()


async def test_trivial_yields() -> None:
    with assert_checkpoints():
        await _core.checkpoint()

    with assert_checkpoints():
        await _core.checkpoint_if_cancelled()
        await _core.cancel_shielded_checkpoint()

    # Weird case: opening and closing a nursery schedules, but doesn't check
    # for cancellation (unless something inside the nursery does)
    task = _core.current_task()
    before_schedule_points = task._schedule_points
    with _core.CancelScope() as cs:
        cs.cancel()
        async with _core.open_nursery():
            pass
    assert not cs.cancelled_caught
    assert task._schedule_points > before_schedule_points

    before_schedule_points = task._schedule_points

    async def noop_with_no_checkpoint() -> None:
        pass

    with _core.CancelScope() as cs:
        cs.cancel()
        async with _core.open_nursery() as nursery:
            nursery.start_soon(noop_with_no_checkpoint)
    assert not cs.cancelled_caught

    assert task._schedule_points > before_schedule_points

    with _core.CancelScope() as cancel_scope:
        cancel_scope.cancel()
        with RaisesGroup(KeyError):
            async with _core.open_nursery():
                raise KeyError


async def test_nursery_start(autojump_clock: _core.MockClock) -> None:
    async def no_args() -> None:  # pragma: no cover
        pass

    # Errors in calling convention get raised immediately from start
    async with _core.open_nursery() as nursery:
        with pytest.raises(TypeError):
            await nursery.start(no_args)

    async def sleep_then_start(
        seconds: int, *, task_status: _core.TaskStatus[int] = _core.TASK_STATUS_IGNORED
    ) -> None:
        repr(task_status)  # smoke test
        await sleep(seconds)
        task_status.started(seconds)
        await sleep(seconds)

    # Basic happy-path check: start waits for the task to call started(), then
    # returns, passes back the value, and the given nursery then waits for it
    # to exit.
    for seconds in [1, 2]:
        async with _core.open_nursery() as nursery:
            assert len(nursery.child_tasks) == 0
            t0 = _core.current_time()
            assert await nursery.start(sleep_then_start, seconds) == seconds
            assert _core.current_time() - t0 == seconds
            assert len(nursery.child_tasks) == 1
        assert _core.current_time() - t0 == 2 * seconds

    # Make sure TASK_STATUS_IGNORED works so task function can be called
    # directly
    t0 = _core.current_time()
    await sleep_then_start(3)
    assert _core.current_time() - t0 == 2 * 3

    # calling started twice
    async def double_started(
        *,
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        task_status.started()
        with pytest.raises(RuntimeError):
            task_status.started()

    async with _core.open_nursery() as nursery:
        await nursery.start(double_started)

    # child crashes before calling started -> error comes out of .start()
    async def raise_keyerror(
        *,
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        raise KeyError("oops")

    async with _core.open_nursery() as nursery:
        with pytest.raises(KeyError):
            await nursery.start(raise_keyerror)

    # child exiting cleanly before calling started -> triggers a RuntimeError
    async def nothing(
        *,
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        return

    async with _core.open_nursery() as nursery:
        with pytest.raises(RuntimeError) as excinfo1:
            await nursery.start(nothing)
        assert "exited without calling" in str(excinfo1.value)

    # if the call to start() is cancelled, then the call to started() does
    # nothing -- the child keeps executing under start(). The value it passed
    # is ignored; start() raises Cancelled.
    async def just_started(
        *,
        task_status: _core.TaskStatus[str] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        task_status.started("hi")
        await _core.checkpoint()

    async with _core.open_nursery() as nursery:
        with _core.CancelScope() as cs:
            cs.cancel()
            with pytest.raises(_core.Cancelled):
                await nursery.start(just_started)

    # but if the task does not execute any checkpoints, and exits, then start()
    # doesn't raise Cancelled, since the task completed successfully.
    async def started_with_no_checkpoint(
        *, task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED
    ) -> None:
        task_status.started(None)

    async with _core.open_nursery() as nursery:
        with _core.CancelScope() as cs:
            cs.cancel()
            await nursery.start(started_with_no_checkpoint)
        assert not cs.cancelled_caught

    # and since starting in a cancelled context makes started() a no-op, if
    # the child crashes after calling started(), the error can *still* come
    # out of start()
    async def raise_keyerror_after_started(
        *, task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED
    ) -> None:
        task_status.started()
        raise KeyError("whoopsiedaisy")

    async with _core.open_nursery() as nursery:
        with _core.CancelScope() as cs:
            cs.cancel()
            with pytest.raises(KeyError):
                await nursery.start(raise_keyerror_after_started)

    # trying to start in a closed nursery raises an error immediately
    async with _core.open_nursery() as closed_nursery:
        pass
    t0 = _core.current_time()
    with pytest.raises(RuntimeError):
        await closed_nursery.start(sleep_then_start, 7)
    # sub-second delays can be caused by unrelated multitasking by an OS
    assert int(_core.current_time()) == int(t0)


async def test_task_nursery_stack() -> None:
    task = _core.current_task()
    assert task._child_nurseries == []
    async with _core.open_nursery() as nursery1:
        assert task._child_nurseries == [nursery1]
        with RaisesGroup(KeyError):
            async with _core.open_nursery() as nursery2:
                assert task._child_nurseries == [nursery1, nursery2]
                raise KeyError
        assert task._child_nurseries == [nursery1]
    assert task._child_nurseries == []


async def test_nursery_start_with_cancelled_nursery() -> None:
    # This function isn't testing task_status, it's using task_status as a
    # convenient way to get a nursery that we can test spawning stuff into.
    async def setup_nursery(
        task_status: _core.TaskStatus[_core.Nursery] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        async with _core.open_nursery() as nursery:
            task_status.started(nursery)
            await sleep_forever()

    # Calls started() while children are asleep, so we can make sure
    # that the cancellation machinery notices and aborts when a sleeping task
    # is moved into a cancelled scope.
    async def sleeping_children(
        fn: Callable[[], object],
        *,
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleep_forever)
            nursery.start_soon(sleep_forever)
            await wait_all_tasks_blocked()
            fn()
            task_status.started()

    # Cancelling the setup_nursery just *before* calling started()
    async with _core.open_nursery() as nursery:
        target_nursery: _core.Nursery = await nursery.start(setup_nursery)
        await target_nursery.start(
            sleeping_children, target_nursery.cancel_scope.cancel
        )

    # Cancelling the setup_nursery just *after* calling started()
    async with _core.open_nursery() as nursery:
        target_nursery = await nursery.start(setup_nursery)
        await target_nursery.start(sleeping_children, lambda: None)
        target_nursery.cancel_scope.cancel()


async def test_nursery_start_keeps_nursery_open(
    autojump_clock: _core.MockClock,
) -> None:
    async def sleep_a_bit(
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        await sleep(2)
        task_status.started()
        await sleep(3)

    async with _core.open_nursery() as nursery1:
        t0 = _core.current_time()
        async with _core.open_nursery() as nursery2:
            # Start the 'start' call running in the background
            nursery1.start_soon(nursery2.start, sleep_a_bit)
            # Sleep a bit
            await sleep(1)
            # Start another one.
            nursery1.start_soon(nursery2.start, sleep_a_bit)
            # Then exit this nursery. At this point, there are no tasks
            # present in this nursery -- the only thing keeping it open is
            # that the tasks will be placed into it soon, when they call
            # started().
        assert _core.current_time() - t0 == 6

    # Check that it still works even if the task that the nursery is waiting
    # for ends up crashing, and never actually enters the nursery.
    async def sleep_then_crash(
        task_status: _core.TaskStatus[None] = _core.TASK_STATUS_IGNORED,
    ) -> None:
        await sleep(7)
        raise KeyError

    async def start_sleep_then_crash(nursery: _core.Nursery) -> None:
        with pytest.raises(KeyError):
            await nursery.start(sleep_then_crash)

    async with _core.open_nursery() as nursery1:
        t0 = _core.current_time()
        async with _core.open_nursery() as nursery2:
            nursery1.start_soon(start_sleep_then_crash, nursery2)
            await wait_all_tasks_blocked()
        assert _core.current_time() - t0 == 7


async def test_nursery_explicit_exception() -> None:
    with RaisesGroup(KeyError):
        async with _core.open_nursery():
            raise KeyError()


async def test_nursery_stop_iteration() -> None:
    async def fail() -> NoReturn:
        raise ValueError

    with RaisesGroup(StopIteration, ValueError):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(fail)
            raise StopIteration


async def test_nursery_stop_async_iteration() -> None:
    class it:
        def __init__(self, count: int) -> None:
            self.count = count
            self.val = 0

        async def __anext__(self) -> int:
            await sleep(0)
            val = self.val
            if val >= self.count:
                raise StopAsyncIteration
            self.val += 1
            return val

    class async_zip:
        def __init__(self, *largs: it) -> None:
            self.nexts = [obj.__anext__ for obj in largs]

        async def _accumulate(
            self, f: Callable[[], Awaitable[int]], items: list[int], i: int
        ) -> None:
            items[i] = await f()

        def __aiter__(self) -> async_zip:
            return self

        async def __anext__(self) -> list[int]:
            nexts = self.nexts
            items: list[int] = [-1] * len(nexts)

            try:
                async with _core.open_nursery() as nursery:
                    for i, f in enumerate(nexts):
                        nursery.start_soon(self._accumulate, f, items, i)
            except ExceptionGroup as e:
                # With strict_exception_groups enabled, users now need to unwrap
                # StopAsyncIteration and re-raise it.
                # This would be relatively clean on python3.11+ with except*.
                # We could also use RaisesGroup, but that's primarily meant as
                # test infra, not as a runtime tool.
                if len(e.exceptions) == 1 and isinstance(
                    e.exceptions[0], StopAsyncIteration
                ):
                    raise e.exceptions[0] from None
                else:  # pragma: no cover
                    raise AssertionError("unknown error in _accumulate") from e

            return items

    result: list[list[int]] = []
    async for vals in async_zip(it(4), it(2)):
        result.append(vals)
    assert result == [[0, 0], [1, 1]]


async def test_traceback_frame_removal() -> None:
    async def my_child_task() -> NoReturn:
        raise KeyError()

    def check_traceback(exc: KeyError) -> bool:
        # The top frame in the exception traceback should be inside the child
        # task, not trio/contextvars internals. And there's only one frame
        # inside the child task, so this will also detect if our frame-removal
        # is too eager.
        tb = exc.__traceback__
        assert tb is not None
        return tb.tb_frame.f_code is my_child_task.__code__

    expected_exception = Matcher(KeyError, check=check_traceback)

    with RaisesGroup(expected_exception, expected_exception):
        # Trick: For now cancel/nursery scopes still leave a bunch of tb gunk
        # behind. But if there's an ExceptionGroup, they leave it on the group,
        # which lets us get a clean look at the KeyError itself. Someday I
        # guess this will always be an ExceptionGroup (#611), but for now we can
        # force it by raising two exceptions.
        async with _core.open_nursery() as nursery:
            nursery.start_soon(my_child_task)
            nursery.start_soon(my_child_task)


def test_contextvar_support() -> None:
    var: contextvars.ContextVar[str] = contextvars.ContextVar("test")
    var.set("before")

    assert var.get() == "before"

    async def inner() -> None:
        task = _core.current_task()
        assert task.context.get(var) == "before"
        assert var.get() == "before"
        var.set("after")
        assert var.get() == "after"
        assert var in task.context
        assert task.context.get(var) == "after"

    _core.run(inner)
    assert var.get() == "before"


async def test_contextvar_multitask() -> None:
    var = contextvars.ContextVar("test", default="hmmm")

    async def t1() -> None:
        assert var.get() == "hmmm"
        var.set("hmmmm")
        assert var.get() == "hmmmm"

    async def t2() -> None:
        assert var.get() == "hmmmm"

    async with _core.open_nursery() as n:
        n.start_soon(t1)
        await wait_all_tasks_blocked()
        assert var.get() == "hmmm"
        var.set("hmmmm")
        n.start_soon(t2)
        await wait_all_tasks_blocked()


def test_system_task_contexts() -> None:
    cvar: contextvars.ContextVar[str] = contextvars.ContextVar("qwilfish")
    cvar.set("water")

    async def system_task() -> None:
        assert cvar.get() == "water"

    async def regular_task() -> None:
        assert cvar.get() == "poison"

    async def inner() -> None:
        async with _core.open_nursery() as nursery:
            cvar.set("poison")
            nursery.start_soon(regular_task)
            _core.spawn_system_task(system_task)
            await wait_all_tasks_blocked()

    _core.run(inner)


async def test_Nursery_init() -> None:
    """Test that nurseries cannot be constructed directly."""
    # This function is async so that we have access to a task object we can
    # pass in. It should never be accessed though.
    task = _core.current_task()
    scope = _core.CancelScope()
    with pytest.raises(TypeError):
        _core._run.Nursery(task, scope, True)


async def test_Nursery_private_init() -> None:
    # context manager creation should not raise
    async with _core.open_nursery() as nursery:
        assert not nursery._closed


def test_Nursery_subclass() -> None:
    with pytest.raises(TypeError):
        type("Subclass", (_core._run.Nursery,), {})


def test_Cancelled_init() -> None:
    with pytest.raises(TypeError):
        raise _core.Cancelled

    with pytest.raises(TypeError):
        _core.Cancelled()

    # private constructor should not raise
    _core.Cancelled._create()


def test_Cancelled_str() -> None:
    cancelled = _core.Cancelled._create()
    assert str(cancelled) == "Cancelled"


def test_Cancelled_subclass() -> None:
    with pytest.raises(TypeError):
        type("Subclass", (_core.Cancelled,), {})


def test_CancelScope_subclass() -> None:
    with pytest.raises(TypeError):
        type("Subclass", (_core.CancelScope,), {})


def test_sniffio_integration() -> None:
    with pytest.raises(sniffio.AsyncLibraryNotFoundError):
        sniffio.current_async_library()

    async def check_inside_trio() -> None:
        assert sniffio.current_async_library() == "trio"

    def check_function_returning_coroutine() -> Awaitable[object]:
        assert sniffio.current_async_library() == "trio"
        return check_inside_trio()

    _core.run(check_inside_trio)

    with pytest.raises(sniffio.AsyncLibraryNotFoundError):
        sniffio.current_async_library()

    @contextmanager
    def alternate_sniffio_library() -> Generator[None, None, None]:
        prev_token = sniffio.current_async_library_cvar.set("nullio")
        prev_library, sniffio.thread_local.name = sniffio.thread_local.name, "nullio"
        try:
            yield
            assert sniffio.current_async_library() == "nullio"
        finally:
            sniffio.thread_local.name = prev_library
            sniffio.current_async_library_cvar.reset(prev_token)

    async def check_new_task_resets_sniffio_library() -> None:
        with alternate_sniffio_library():
            _core.spawn_system_task(check_inside_trio)
        async with _core.open_nursery() as nursery:
            with alternate_sniffio_library():
                nursery.start_soon(check_inside_trio)
                nursery.start_soon(check_function_returning_coroutine)

    _core.run(check_new_task_resets_sniffio_library)


async def test_Task_custom_sleep_data() -> None:
    task = _core.current_task()
    assert task.custom_sleep_data is None
    task.custom_sleep_data = 1
    assert task.custom_sleep_data == 1
    await _core.checkpoint()
    assert task.custom_sleep_data is None


@types.coroutine
def async_yield(value: T) -> Generator[T, None, None]:
    yield value


async def test_permanently_detach_coroutine_object() -> None:
    task: _core.Task | None = None
    pdco_outcome: outcome.Outcome[str] | None = None

    async def detachable_coroutine(
        task_outcome: outcome.Outcome[None],
        yield_value: object,
    ) -> None:
        await sleep(0)
        nonlocal task, pdco_outcome
        task = _core.current_task()
        pdco_outcome = await outcome.acapture(
            _core.permanently_detach_coroutine_object, task_outcome
        )
        await async_yield(yield_value)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(detachable_coroutine, outcome.Value(None), "I'm free!")

    # If we get here then Trio thinks the task has exited... but the coroutine
    # is still iterable. At that point anything can be sent into the coroutine, so the .coro type
    # is wrong.
    assert pdco_outcome is None
    assert not_none(task).coro.send(cast(Any, "be free!")) == "I'm free!"
    assert pdco_outcome == outcome.Value("be free!")
    with pytest.raises(StopIteration):
        not_none(task).coro.send(cast(Any, None))

    # Check the exception paths too
    task = None
    pdco_outcome = None
    with RaisesGroup(KeyError):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(detachable_coroutine, outcome.Error(KeyError()), "uh oh")
    throw_in = ValueError()
    assert isinstance(task, _core.Task)  # For type checkers.
    assert not_none(task).coro.throw(throw_in) == "uh oh"
    assert pdco_outcome == outcome.Error(throw_in)
    with pytest.raises(StopIteration):
        task.coro.send(cast(Any, None))

    async def bad_detach() -> None:
        async with _core.open_nursery():
            with pytest.raises(RuntimeError) as excinfo:
                await _core.permanently_detach_coroutine_object(outcome.Value(None))
            assert "open nurser" in str(excinfo.value)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(bad_detach)


async def test_detach_and_reattach_coroutine_object() -> None:
    unrelated_task: _core.Task | None = None
    task: _core.Task | None = None

    async def unrelated_coroutine() -> None:
        nonlocal unrelated_task
        unrelated_task = _core.current_task()

    async def reattachable_coroutine() -> None:
        nonlocal task
        await sleep(0)

        task = _core.current_task()

        def abort_fn(_: _core.RaiseCancelT) -> _core.Abort:  # pragma: no cover
            return _core.Abort.FAILED

        got = await _core.temporarily_detach_coroutine_object(abort_fn)
        assert got == "not trio!"

        await async_yield(1)
        await async_yield(2)

        with pytest.raises(RuntimeError) as excinfo:
            await _core.reattach_detached_coroutine_object(
                not_none(unrelated_task), None
            )
        assert "does not match" in str(excinfo.value)

        await _core.reattach_detached_coroutine_object(task, "byebye")

        await sleep(0)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(unrelated_coroutine)
        nursery.start_soon(reattachable_coroutine)
        await wait_all_tasks_blocked()

        # Okay, it's detached. Here's our coroutine runner:
        assert not_none(task).coro.send(cast(Any, "not trio!")) == 1
        assert not_none(task).coro.send(cast(Any, None)) == 2
        assert not_none(task).coro.send(cast(Any, None)) == "byebye"

        # Now it's been reattached, and we can leave the nursery


async def test_detached_coroutine_cancellation() -> None:
    abort_fn_called = False
    task: _core.Task | None = None

    async def reattachable_coroutine() -> None:
        await sleep(0)

        nonlocal task
        task = _core.current_task()

        def abort_fn(_: _core.RaiseCancelT) -> _core.Abort:
            nonlocal abort_fn_called
            abort_fn_called = True
            return _core.Abort.FAILED

        await _core.temporarily_detach_coroutine_object(abort_fn)
        await _core.reattach_detached_coroutine_object(task, None)
        with pytest.raises(_core.Cancelled):
            await sleep(0)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(reattachable_coroutine)
        await wait_all_tasks_blocked()
        assert task is not None
        nursery.cancel_scope.cancel()
        task.coro.send(cast(Any, None))

    assert abort_fn_called


@restore_unraisablehook()
def test_async_function_implemented_in_C() -> None:
    # These used to crash because we'd try to mutate the coroutine object's
    # cr_frame, but C functions don't have Python frames.

    async def agen_fn(record: list[str]) -> AsyncIterator[None]:
        assert not _core.currently_ki_protected()
        record.append("the generator ran")
        yield

    run_record: list[str] = []
    agen = agen_fn(run_record)
    _core.run(agen.__anext__)
    assert run_record == ["the generator ran"]

    async def main() -> None:
        start_soon_record: list[str] = []
        agen = agen_fn(start_soon_record)
        async with _core.open_nursery() as nursery:
            nursery.start_soon(agen.__anext__)
        assert start_soon_record == ["the generator ran"]

    _core.run(main)


async def test_very_deep_cancel_scope_nesting() -> None:
    # This used to crash with a RecursionError in CancelStatus.recalculate
    with ExitStack() as exit_stack:
        outermost_scope = _core.CancelScope()
        exit_stack.enter_context(outermost_scope)
        for _ in range(5000):
            exit_stack.enter_context(_core.CancelScope())
        outermost_scope.cancel()


async def test_cancel_scope_deadline_duplicates() -> None:
    # This exercises an assert in Deadlines._prune, by intentionally creating
    # duplicate entries in the deadline heap.
    now = _core.current_time()
    with _core.CancelScope() as cscope:
        for _ in range(DEADLINE_HEAP_MIN_PRUNE_THRESHOLD * 2):
            cscope.deadline = now + 9998
            cscope.deadline = now + 9999
        await sleep(0.01)


# I don't know if this one can fail anymore, the `del` next to the comment that used to
# refer to this only seems to break test_cancel_scope_exit_doesnt_create_cyclic_garbage
# We're keeping it for now to cover Outcome and potential future refactoring
@pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="Only makes sense with refcounting GC"
)
async def test_simple_cancel_scope_usage_doesnt_create_cyclic_garbage() -> None:
    # https://github.com/python-trio/trio/issues/1770
    gc.collect()

    async def do_a_cancel() -> None:
        with _core.CancelScope() as cscope:
            cscope.cancel()
            await sleep_forever()

    async def crasher() -> NoReturn:
        raise ValueError("this is a crash")

    old_flags = gc.get_debug()
    try:
        gc.collect()
        gc.set_debug(gc.DEBUG_SAVEALL)

        # cover outcome.Error.unwrap
        # (See https://github.com/python-trio/outcome/pull/29)
        await do_a_cancel()
        # cover outcome.Error.unwrap if unrolled_run hangs on to exception refs
        # (See https://github.com/python-trio/trio/pull/1864)
        await do_a_cancel()

        with RaisesGroup(Matcher(ValueError, "^this is a crash$")):
            async with _core.open_nursery() as nursery:
                # cover NurseryManager.__aexit__
                nursery.start_soon(crasher)

        gc.collect()
        assert not gc.garbage
    finally:
        gc.set_debug(old_flags)
        gc.garbage.clear()


@pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="Only makes sense with refcounting GC"
)
async def test_cancel_scope_exit_doesnt_create_cyclic_garbage() -> None:
    # https://github.com/python-trio/trio/pull/2063
    gc.collect()

    async def crasher() -> NoReturn:
        raise ValueError("this is a crash")

    old_flags = gc.get_debug()
    try:
        with RaisesGroup(
            Matcher(ValueError, "^this is a crash$")
        ), _core.CancelScope() as outer:
            async with _core.open_nursery() as nursery:
                gc.collect()
                gc.set_debug(gc.DEBUG_SAVEALL)
                # One child that gets cancelled by the outer scope
                nursery.start_soon(sleep_forever)
                outer.cancel()
                # And one that raises a different error
                nursery.start_soon(crasher)
                # so that outer filters a Cancelled from the ExceptionGroup and
                # covers CancelScope.__exit__ (and NurseryManager.__aexit__)
                # (See https://github.com/python-trio/trio/pull/2063)

        gc.collect()
        assert not gc.garbage
    finally:
        gc.set_debug(old_flags)
        gc.garbage.clear()


@pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="Only makes sense with refcounting GC"
)
async def test_nursery_cancel_doesnt_create_cyclic_garbage() -> None:
    collected = False

    # https://github.com/python-trio/trio/issues/1770#issuecomment-730229423
    def toggle_collected() -> None:
        nonlocal collected
        collected = True

    gc.collect()
    old_flags = gc.get_debug()
    try:
        gc.set_debug(0)
        gc.collect()
        gc.set_debug(gc.DEBUG_SAVEALL)

        # cover Nursery._nested_child_finished
        async with _core.open_nursery() as nursery:
            nursery.cancel_scope.cancel()

        weakref.finalize(nursery, toggle_collected)
        del nursery
        # a checkpoint clears the nursery from the internals, apparently
        # TODO: stop event loop from hanging on to the nursery at this point
        await _core.checkpoint()

        assert collected
        gc.collect()
        assert not gc.garbage
    finally:
        gc.set_debug(old_flags)
        gc.garbage.clear()


@pytest.mark.skipif(
    sys.implementation.name != "cpython", reason="Only makes sense with refcounting GC"
)
async def test_locals_destroyed_promptly_on_cancel() -> None:
    destroyed = False

    def finalizer() -> None:
        nonlocal destroyed
        destroyed = True

    class A:
        pass

    async def task() -> None:
        a = A()
        weakref.finalize(a, finalizer)
        await _core.checkpoint()

    async with _core.open_nursery() as nursery:
        nursery.start_soon(task)
        nursery.cancel_scope.cancel()
    assert destroyed


def _create_kwargs(strictness: bool | None) -> dict[str, bool]:
    """Turn a bool|None into a kwarg dict that can be passed to `run` or `open_nursery`"""

    if strictness is None:
        return {}
    return {"strict_exception_groups": strictness}


@pytest.mark.filterwarnings(
    "ignore:.*strict_exception_groups=False:trio.TrioDeprecationWarning"
)
@pytest.mark.parametrize("run_strict", [True, False, None])
@pytest.mark.parametrize("open_nursery_strict", [True, False, None])
@pytest.mark.parametrize("multiple_exceptions", [True, False])
def test_setting_strict_exception_groups(
    run_strict: bool | None, open_nursery_strict: bool | None, multiple_exceptions: bool
) -> None:
    """
    Test default values and that nurseries can both inherit and override the global context
    setting of strict_exception_groups.
    """

    async def raise_error() -> NoReturn:
        raise RuntimeError("test error")

    async def main() -> None:
        """Open a nursery, and raise one or two errors inside"""
        async with _core.open_nursery(**_create_kwargs(open_nursery_strict)) as nursery:
            nursery.start_soon(raise_error)
            if multiple_exceptions:
                nursery.start_soon(raise_error)

    def run_main() -> None:
        # mypy doesn't like kwarg magic
        _core.run(main, **_create_kwargs(run_strict))  # type: ignore[arg-type]

    matcher = Matcher(RuntimeError, "^test error$")

    if multiple_exceptions:
        with RaisesGroup(matcher, matcher):
            run_main()
    elif open_nursery_strict or (
        open_nursery_strict is None and run_strict is not False
    ):
        with RaisesGroup(matcher):
            run_main()
    else:
        with pytest.raises(RuntimeError, match="^test error$"):
            run_main()


@pytest.mark.filterwarnings(
    "ignore:.*strict_exception_groups=False:trio.TrioDeprecationWarning"
)
@pytest.mark.parametrize("strict", [True, False, None])
async def test_nursery_collapse(strict: bool | None) -> None:
    """
    Test that a single exception from a nested nursery gets collapsed correctly
    depending on strict_exception_groups value when CancelledErrors are stripped from it.
    """

    async def raise_error() -> NoReturn:
        raise RuntimeError("test error")

    # mypy requires explicit type for conditional expression
    maybe_wrapped_runtime_error: type[RuntimeError] | RaisesGroup[RuntimeError] = (
        RuntimeError if strict is False else RaisesGroup(RuntimeError)
    )

    with RaisesGroup(RuntimeError, maybe_wrapped_runtime_error):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(sleep_forever)
            nursery.start_soon(raise_error)
            async with _core.open_nursery(**_create_kwargs(strict)) as nursery2:
                nursery2.start_soon(sleep_forever)
                nursery2.start_soon(raise_error)
                nursery.cancel_scope.cancel()


async def test_cancel_scope_no_cancellederror() -> None:
    """
    Test that when a cancel scope encounters an exception group that does NOT contain
    a Cancelled exception, it will NOT set the ``cancelled_caught`` flag.
    """

    with RaisesGroup(RuntimeError, RuntimeError, match="test"):
        with _core.CancelScope() as scope:
            scope.cancel()
            raise ExceptionGroup("test", [RuntimeError(), RuntimeError()])

    assert not scope.cancelled_caught


@pytest.mark.filterwarnings(
    "ignore:.*strict_exception_groups=False:trio.TrioDeprecationWarning"
)
@pytest.mark.parametrize("run_strict", [False, True])
@pytest.mark.parametrize("start_raiser_strict", [False, True, None])
@pytest.mark.parametrize("raise_after_started", [False, True])
@pytest.mark.parametrize("raise_custom_exc_grp", [False, True])
def test_trio_run_strict_before_started(
    run_strict: bool,
    start_raiser_strict: bool | None,
    raise_after_started: bool,
    raise_custom_exc_grp: bool,
) -> None:
    """
    Regression tests for #2611, where exceptions raised before
    `TaskStatus.started()` caused `Nursery.start()` to wrap them in an
    ExceptionGroup when using `run(..., strict_exception_groups=True)`.

    Regression tests for #2844, where #2611 was initially fixed in a way that
    had unintended side effects.
    """

    raiser_exc: ValueError | ExceptionGroup[ValueError]
    if raise_custom_exc_grp:
        raiser_exc = ExceptionGroup("my group", [ValueError()])
    else:
        raiser_exc = ValueError()

    async def raiser(*, task_status: _core.TaskStatus[None]) -> None:
        if raise_after_started:
            task_status.started()
        raise raiser_exc

    async def start_raiser() -> None:
        try:
            async with _core.open_nursery(
                strict_exception_groups=start_raiser_strict
            ) as nursery:
                await nursery.start(raiser)
        except BaseExceptionGroup as exc_group:
            if start_raiser_strict:
                # Iff the code using the nursery *forced* it to be strict
                # (overriding the runner setting) then it may replace the bland
                # exception group raised by trio with a more specific one (subtype,
                # different message, etc.).
                raise BaseExceptionGroup(
                    "start_raiser nursery custom message", exc_group.exceptions
                ) from None
            raise

    with pytest.raises(BaseException) as exc_info:  # noqa: PT011  # no `match`
        _core.run(start_raiser, strict_exception_groups=run_strict)

    if start_raiser_strict or (run_strict and start_raiser_strict is None):
        # start_raiser's nursery was strict.
        assert isinstance(exc_info.value, BaseExceptionGroup)
        if start_raiser_strict:
            # start_raiser didn't unknowingly inherit its nursery strictness
            # from `run`---it explicitly chose for its nursery to be strict.
            assert exc_info.value.message == "start_raiser nursery custom message"
        assert len(exc_info.value.exceptions) == 1
        should_be_raiser_exc = exc_info.value.exceptions[0]
    else:
        # start_raiser's nursery was not strict.
        should_be_raiser_exc = exc_info.value
    if isinstance(raiser_exc, ValueError):
        assert should_be_raiser_exc is raiser_exc
    else:
        # Check attributes, not identity, because should_be_raiser_exc may be a
        # copy of raiser_exc rather than raiser_exc by identity.
        assert type(should_be_raiser_exc) == type(raiser_exc)
        assert should_be_raiser_exc.message == raiser_exc.message
        assert should_be_raiser_exc.exceptions == raiser_exc.exceptions


async def test_internal_error_old_nursery_multiple_tasks() -> None:
    async def error_func() -> None:
        raise ValueError

    async def spawn_tasks_in_old_nursery(task_status: _core.TaskStatus[None]) -> None:
        old_nursery = _core.current_task().parent_nursery
        assert old_nursery is not None
        old_nursery.start_soon(error_func)
        old_nursery.start_soon(error_func)

    async with _core.open_nursery() as nursery:
        with pytest.raises(_core.TrioInternalError) as excinfo:
            await nursery.start(spawn_tasks_in_old_nursery)
    assert RaisesGroup(ValueError, ValueError).matches(excinfo.value.__cause__)
