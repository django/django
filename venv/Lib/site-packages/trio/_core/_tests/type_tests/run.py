from __future__ import annotations

from typing import TYPE_CHECKING, overload

import trio
from typing_extensions import assert_type

if TYPE_CHECKING:
    from collections.abc import Sequence


async def sleep_sort(values: Sequence[float]) -> list[float]:
    return [1]


async def has_optional(arg: int | None = None) -> int:
    return 5


@overload
async def foo_overloaded(arg: int) -> str: ...


@overload
async def foo_overloaded(arg: str) -> int: ...


async def foo_overloaded(arg: int | str) -> int | str:
    if isinstance(arg, str):
        return 5
    return "hello"


v = trio.run(
    sleep_sort,
    (1, 3, 5, 2, 4),
    clock=trio.testing.MockClock(autojump_threshold=0),
)
assert_type(v, "list[float]")
trio.run(sleep_sort, ["hi", "there"])  # type: ignore[arg-type]
trio.run(sleep_sort)  # type: ignore[arg-type]

r = trio.run(has_optional)
assert_type(r, int)
r = trio.run(has_optional, 5)
trio.run(has_optional, 7, 8)  # type: ignore[arg-type]
trio.run(has_optional, "hello")  # type: ignore[arg-type]


assert_type(trio.run(foo_overloaded, 5), str)
assert_type(trio.run(foo_overloaded, ""), int)
