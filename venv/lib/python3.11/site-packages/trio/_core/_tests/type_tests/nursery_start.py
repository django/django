"""Test variadic generic typing for Nursery.start[_soon]()."""
from typing import Awaitable, Callable

from trio import TASK_STATUS_IGNORED, Nursery, TaskStatus


async def task_0() -> None:
    ...


async def task_1a(value: int) -> None:
    ...


async def task_1b(value: str) -> None:
    ...


async def task_2a(a: int, b: str) -> None:
    ...


async def task_2b(a: str, b: int) -> None:
    ...


async def task_2c(a: str, b: int, optional: bool = False) -> None:
    ...


async def task_requires_kw(a: int, *, b: bool) -> None:
    ...


async def task_startable_1(
    a: str,
    *,
    task_status: TaskStatus[bool] = TASK_STATUS_IGNORED,
) -> None:
    ...


async def task_startable_2(
    a: str,
    b: float,
    *,
    task_status: TaskStatus[bool] = TASK_STATUS_IGNORED,
) -> None:
    ...


async def task_requires_start(*, task_status: TaskStatus[str]) -> None:
    """Check a function requiring start() to be used."""


async def task_pos_or_kw(value: str, task_status: TaskStatus[int]) -> None:
    """Check a function which doesn't use the *-syntax works."""
    ...


def check_start_soon(nursery: Nursery) -> None:
    """start_soon() functionality."""
    nursery.start_soon(task_0)
    nursery.start_soon(task_1a)  # type: ignore
    nursery.start_soon(task_2b)  # type: ignore

    nursery.start_soon(task_0, 45)  # type: ignore
    nursery.start_soon(task_1a, 32)
    nursery.start_soon(task_1b, 32)  # type: ignore
    nursery.start_soon(task_1a, "abc")  # type: ignore
    nursery.start_soon(task_1b, "abc")

    nursery.start_soon(task_2b, "abc")  # type: ignore
    nursery.start_soon(task_2a, 38, "46")
    nursery.start_soon(task_2c, "abc", 12, True)

    nursery.start_soon(task_2c, "abc", 12)
    task_2c_cast: Callable[
        [str, int], Awaitable[object]
    ] = task_2c  # The assignment makes it work.
    nursery.start_soon(task_2c_cast, "abc", 12)

    nursery.start_soon(task_requires_kw, 12, True)  # type: ignore
    # Tasks following the start() API can be made to work.
    nursery.start_soon(task_startable_1, "cdf")
