from typing import AsyncGenerator

import trio


async def coro1(event: trio.Event) -> None:
    event.set()
    await trio.sleep_forever()


async def coro2(event: trio.Event) -> None:
    await coro1(event)


async def coro3(event: trio.Event) -> None:
    await coro2(event)


async def coro2_async_gen(event: trio.Event) -> AsyncGenerator[None, None]:
    # mypy does not like `yield await trio.lowlevel.checkpoint()` - but that
    # should be equivalent to splitting the statement
    await trio.lowlevel.checkpoint()
    yield
    await coro1(event)
    yield  # pragma: no cover
    await trio.lowlevel.checkpoint()  # pragma: no cover
    yield  # pragma: no cover


async def coro3_async_gen(event: trio.Event) -> None:
    async for _ in coro2_async_gen(event):
        pass


async def test_task_iter_await_frames() -> None:
    async with trio.open_nursery() as nursery:
        event = trio.Event()
        nursery.start_soon(coro3, event)
        await event.wait()

        (task,) = nursery.child_tasks

        assert [frame.f_code.co_name for frame, _ in task.iter_await_frames()][:3] == [
            "coro3",
            "coro2",
            "coro1",
        ]

        nursery.cancel_scope.cancel()


async def test_task_iter_await_frames_async_gen() -> None:
    async with trio.open_nursery() as nursery:
        event = trio.Event()
        nursery.start_soon(coro3_async_gen, event)
        await event.wait()

        (task,) = nursery.child_tasks

        assert [frame.f_code.co_name for frame, _ in task.iter_await_frames()][:3] == [
            "coro3_async_gen",
            "coro2_async_gen",
            "coro1",
        ]

        nursery.cancel_scope.cancel()
