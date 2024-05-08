from typing import Awaitable, Callable

import pytest

import trio


async def test_deprecation_warning_open_nursery() -> None:
    with pytest.warns(
        trio.TrioDeprecationWarning, match="strict_exception_groups=False"
    ) as record:
        async with trio.open_nursery(strict_exception_groups=False):
            ...
    assert len(record) == 1
    async with trio.open_nursery(strict_exception_groups=True):
        ...
    async with trio.open_nursery():
        ...


def test_deprecation_warning_run() -> None:
    async def foo() -> None: ...

    async def foo_nursery() -> None:
        # this should not raise a warning, even if it's implied loose
        async with trio.open_nursery():
            ...

    async def foo_loose_nursery() -> None:
        # this should raise a warning, even if specifying the parameter is redundant
        async with trio.open_nursery(strict_exception_groups=False):
            ...

    def helper(fun: Callable[..., Awaitable[None]], num: int) -> None:
        with pytest.warns(
            trio.TrioDeprecationWarning, match="strict_exception_groups=False"
        ) as record:
            trio.run(fun, strict_exception_groups=False)
        assert len(record) == num

    helper(foo, 1)
    helper(foo_nursery, 1)
    helper(foo_loose_nursery, 2)


def test_deprecation_warning_start_guest_run() -> None:
    # "The simplest possible "host" loop."
    from .._core._tests.test_guest_mode import trivial_guest_run

    async def trio_return(in_host: object) -> str:
        await trio.lowlevel.checkpoint()
        return "ok"

    with pytest.warns(
        trio.TrioDeprecationWarning, match="strict_exception_groups=False"
    ) as record:
        trivial_guest_run(
            trio_return,
            strict_exception_groups=False,
        )
    assert len(record) == 1
