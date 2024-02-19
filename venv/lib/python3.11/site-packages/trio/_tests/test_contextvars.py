from __future__ import annotations

import contextvars

from .. import _core

trio_testing_contextvar: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trio_testing_contextvar"
)


async def test_contextvars_default() -> None:
    trio_testing_contextvar.set("main")
    record: list[str] = []

    async def child() -> None:
        value = trio_testing_contextvar.get()
        record.append(value)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child)
    assert record == ["main"]


async def test_contextvars_set() -> None:
    trio_testing_contextvar.set("main")
    record: list[str] = []

    async def child() -> None:
        trio_testing_contextvar.set("child")
        value = trio_testing_contextvar.get()
        record.append(value)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(child)
    value = trio_testing_contextvar.get()
    assert record == ["child"]
    assert value == "main"


async def test_contextvars_copy() -> None:
    trio_testing_contextvar.set("main")
    context = contextvars.copy_context()
    trio_testing_contextvar.set("second_main")
    record: list[str] = []

    async def child() -> None:
        value = trio_testing_contextvar.get()
        record.append(value)

    async with _core.open_nursery() as nursery:
        context.run(nursery.start_soon, child)
        nursery.start_soon(child)
    value = trio_testing_contextvar.get()
    assert set(record) == {"main", "second_main"}
    assert value == "second_main"
