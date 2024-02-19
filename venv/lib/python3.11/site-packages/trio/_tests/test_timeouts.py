import time
from typing import Awaitable, Callable, TypeVar

import outcome
import pytest

from .. import _core
from .._core._tests.tutil import slow
from .._timeouts import *
from ..testing import assert_checkpoints

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
            match="^(duration|deadline|timeout) must (not )*be (non-negative|NaN)$",
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
            match="^(duration|deadline|timeout) must (not )*be (non-negative|NaN)$",
        ):
            with cm(val):
                pass  # pragma: no cover
