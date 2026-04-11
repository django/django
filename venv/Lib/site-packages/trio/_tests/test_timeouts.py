from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol, TypeVar

import outcome
import pytest

import trio

from .. import _core
from .._core._tests.tutil import slow
from .._timeouts import (
    TooSlowError,
    fail_after,
    fail_at,
    move_on_after,
    move_on_at,
    sleep,
    sleep_forever,
    sleep_until,
)
from ..testing import assert_checkpoints

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


async def check_takes_about(f: Callable[[], Awaitable[T]], expected_dur: float) -> T:
    start = time.perf_counter()
    result = await outcome.acapture(f)
    dur = time.perf_counter() - start
    print(dur / expected_dur)
    # 1.5 is an arbitrary fudge factor because there's always some delay
    # between when we become eligible to wake up and when we actually do. We
    # used to sleep for 0.05, and regularly observed overruns of 1.6x on
    # Appveyor, and then started seeing overruns of 2.3x on Travis's macOS, so
    # now we bumped up the sleep to 1 second, marked the tests as slow, and
    # hopefully now the proportional error will be less huge.
    #
    # We also also for durations that are a hair shorter than expected. For
    # example, here's a run on Windows where a 1.0 second sleep was measured
    # to take 0.9999999999999858 seconds:
    #   https://ci.appveyor.com/project/njsmith/trio/build/1.0.768/job/3lbdyxl63q3h9s21
    # I believe that what happened here is that Windows's low clock resolution
    # meant that our calls to time.monotonic() returned exactly the same
    # values as the calls inside the actual run loop, but the two subtractions
    # returned slightly different values because the run loop's clock adds a
    # random floating point offset to both times, which should cancel out, but
    # lol floating point we got slightly different rounding errors. (That
    # value above is exactly 128 ULPs below 1.0, which would make sense if it
    # started as a 1 ULP error at a different dynamic range.)
    assert (1 - 1e-8) <= (dur / expected_dur) < 1.5

    return result.unwrap()


# How long to (attempt to) sleep for when testing. Smaller numbers make the
# test suite go faster.
TARGET = 1.0


@slow
async def test_sleep() -> None:
    async def sleep_1() -> None:
        await sleep_until(_core.current_time() + TARGET)

    await check_takes_about(sleep_1, TARGET)

    async def sleep_2() -> None:
        await sleep(TARGET)

    await check_takes_about(sleep_2, TARGET)

    with assert_checkpoints():
        await sleep(0)
    # This also serves as a test of the trivial move_on_at
    with move_on_at(_core.current_time()):
        with pytest.raises(_core.Cancelled):
            await sleep(0)


@slow
async def test_move_on_after() -> None:
    async def sleep_3() -> None:
        with move_on_after(TARGET):
            await sleep(100)

    await check_takes_about(sleep_3, TARGET)


async def test_cannot_wake_sleep_forever() -> None:
    # Test an error occurs if you manually wake sleep_forever().
    task = trio.lowlevel.current_task()

    async def wake_task() -> None:
        await trio.lowlevel.checkpoint()
        trio.lowlevel.reschedule(task, outcome.Value(None))

    async with trio.open_nursery() as nursery:
        nursery.start_soon(wake_task)
        with pytest.raises(RuntimeError):
            await trio.sleep_forever()


class TimeoutScope(Protocol):
    def __call__(self, seconds: float, *, shield: bool) -> trio.CancelScope: ...


@pytest.mark.parametrize("scope", [move_on_after, fail_after])
async def test_context_shields_from_outer(scope: TimeoutScope) -> None:
    with _core.CancelScope() as outer, scope(TARGET, shield=True) as inner:
        outer.cancel()
        try:
            await trio.lowlevel.checkpoint()
        except trio.Cancelled:  # pragma: no cover
            pytest.fail("shield didn't work")
        inner.shield = False
        with pytest.raises(trio.Cancelled):
            await trio.lowlevel.checkpoint()


@slow
async def test_move_on_after_moves_on_even_if_shielded() -> None:
    async def task() -> None:
        with _core.CancelScope() as outer, move_on_after(TARGET, shield=True):
            outer.cancel()
            # The outer scope is cancelled, but this task is protected by the
            # shield, so it manages to get to sleep until deadline is met
            await sleep_forever()

    await check_takes_about(task, TARGET)


@slow
async def test_fail_after_fails_even_if_shielded() -> None:
    async def task() -> None:
        with (
            pytest.raises(TooSlowError),
            _core.CancelScope() as outer,
            fail_after(
                TARGET,
                shield=True,
            ),
        ):
            outer.cancel()
            # The outer scope is cancelled, but this task is protected by the
            # shield, so it manages to get to sleep until deadline is met
            await sleep_forever()

    await check_takes_about(task, TARGET)


@slow
async def test_fail() -> None:
    async def sleep_4() -> None:
        with fail_at(_core.current_time() + TARGET):
            await sleep(100)

    with pytest.raises(TooSlowError):
        await check_takes_about(sleep_4, TARGET)

    with fail_at(_core.current_time() + 100):
        await sleep(0)

    async def sleep_5() -> None:
        with fail_after(TARGET):
            await sleep(100)

    with pytest.raises(TooSlowError):
        await check_takes_about(sleep_5, TARGET)

    with fail_after(100):
        await sleep(0)


async def test_timeouts_raise_value_error() -> None:
    # deadlines are allowed to be negative, but not delays.
    # neither delays nor deadlines are allowed to be NaN

    nan = float("nan")

    for fun, val in (
        (sleep, -1),
        (sleep, nan),
        (sleep_until, nan),
    ):
        with pytest.raises(
            ValueError,
            match=r"^(deadline|`seconds`) must (not )*be (non-negative|NaN)$",
        ):
            await fun(val)

    for cm, val in (
        (fail_after, -1),
        (fail_after, nan),
        (fail_at, nan),
        (move_on_after, -1),
        (move_on_after, nan),
        (move_on_at, nan),
    ):
        with pytest.raises(
            ValueError,
            match=r"^(deadline|`seconds`) must (not )*be (non-negative|NaN)$",
        ):
            with cm(val):
                pass  # pragma: no cover


async def test_timeout_deadline_on_entry(mock_clock: _core.MockClock) -> None:
    rcs = move_on_after(5)
    assert rcs.relative_deadline == 5

    mock_clock.jump(3)
    start = _core.current_time()
    with rcs as cs:
        assert cs.is_relative is None

        # This would previously be start+2
        assert cs.deadline == start + 5
        assert cs.relative_deadline == 5

        cs.deadline = start + 3
        assert cs.deadline == start + 3
        assert cs.relative_deadline == 3

        cs.relative_deadline = 4
        assert cs.deadline == start + 4
        assert cs.relative_deadline == 4

    rcs = move_on_after(5)
    assert rcs.shield is False
    rcs.shield = True
    assert rcs.shield is True

    mock_clock.jump(3)
    start = _core.current_time()
    with rcs as cs:
        assert cs.deadline == start + 5

        assert rcs is cs


async def test_invalid_access_unentered(mock_clock: _core.MockClock) -> None:
    cs = move_on_after(5)
    mock_clock.jump(3)
    start = _core.current_time()

    match_str = "^unentered relative cancel scope does not have an absolute deadline"
    with pytest.warns(DeprecationWarning, match=match_str):
        assert cs.deadline == start + 5
    mock_clock.jump(1)
    # this is hella sketchy, but they *have* been warned
    with pytest.warns(DeprecationWarning, match=match_str):
        assert cs.deadline == start + 6

    with pytest.warns(DeprecationWarning, match=match_str):
        cs.deadline = 7
    # now transformed into absolute
    assert cs.deadline == 7
    assert not cs.is_relative

    cs = move_on_at(5)

    match_str = (
        "^unentered non-relative cancel scope does not have a relative deadline$"
    )
    with pytest.raises(RuntimeError, match=match_str):
        assert cs.relative_deadline
    with pytest.raises(RuntimeError, match=match_str):
        cs.relative_deadline = 7


@pytest.mark.xfail(reason="not implemented")
async def test_fail_access_before_entering() -> None:  # pragma: no cover
    my_fail_at = fail_at(5)
    assert my_fail_at.deadline  # type: ignore[attr-defined]
    my_fail_after = fail_after(5)
    assert my_fail_after.relative_deadline  # type: ignore[attr-defined]
