import trio


async def coro1(event: trio.Event):
    event.set()
    await trio.sleep_forever()


async def coro2(event: trio.Event):
    await coro1(event)


async def coro3(event: trio.Event):
    await coro2(event)


async def coro2_async_gen(event: trio.Event):
    yield await trio.lowlevel.checkpoint()
    yield await coro1(event)
    yield await trio.lowlevel.checkpoint()


async def coro3_async_gen(event: trio.Event):
    async for x in coro2_async_gen(event):
        pass


async def test_task_iter_await_frames():
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


async def test_task_iter_await_frames_async_gen():
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
