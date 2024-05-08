from __future__ import annotations

import errno
from functools import partial
from typing import TYPE_CHECKING, Awaitable, Callable, NoReturn

import attrs

import trio
from trio import Nursery, StapledStream, TaskStatus
from trio.testing import (
    Matcher,
    MemoryReceiveStream,
    MemorySendStream,
    MockClock,
    RaisesGroup,
    memory_stream_pair,
    wait_all_tasks_blocked,
)

if TYPE_CHECKING:
    import pytest

    from trio._channel import MemoryReceiveChannel, MemorySendChannel
    from trio.abc import Stream

# types are somewhat tentative - I just bruteforced them until I got something that didn't
# give errors
StapledMemoryStream = StapledStream[MemorySendStream, MemoryReceiveStream]


@attrs.define(hash=False, eq=False, slots=False)
class MemoryListener(trio.abc.Listener[StapledMemoryStream]):
    closed: bool = False
    accepted_streams: list[trio.abc.Stream] = attrs.Factory(list)
    queued_streams: tuple[
        MemorySendChannel[StapledMemoryStream],
        MemoryReceiveChannel[StapledMemoryStream],
    ] = attrs.Factory(lambda: trio.open_memory_channel[StapledMemoryStream](1))
    accept_hook: Callable[[], Awaitable[object]] | None = None

    async def connect(self) -> StapledMemoryStream:
        assert not self.closed
        client, server = memory_stream_pair()
        await self.queued_streams[0].send(server)
        return client

    async def accept(self) -> StapledMemoryStream:
        await trio.lowlevel.checkpoint()
        assert not self.closed
        if self.accept_hook is not None:
            await self.accept_hook()
        stream = await self.queued_streams[1].receive()
        self.accepted_streams.append(stream)
        return stream

    async def aclose(self) -> None:
        self.closed = True
        await trio.lowlevel.checkpoint()


async def test_serve_listeners_basic() -> None:
    listeners = [MemoryListener(), MemoryListener()]

    record = []

    def close_hook() -> None:
        # Make sure this is a forceful close
        assert trio.current_effective_deadline() == float("-inf")
        record.append("closed")

    async def handler(stream: StapledMemoryStream) -> None:
        await stream.send_all(b"123")
        assert await stream.receive_some(10) == b"456"
        stream.send_stream.close_hook = close_hook
        stream.receive_stream.close_hook = close_hook

    async def client(listener: MemoryListener) -> None:
        s = await listener.connect()
        assert await s.receive_some(10) == b"123"
        await s.send_all(b"456")

    async def do_tests(parent_nursery: Nursery) -> None:
        async with trio.open_nursery() as nursery:
            for listener in listeners:
                for _ in range(3):
                    nursery.start_soon(client, listener)

        await wait_all_tasks_blocked()

        # verifies that all 6 streams x 2 directions each were closed ok
        assert len(record) == 12

        parent_nursery.cancel_scope.cancel()

    async with trio.open_nursery() as nursery:
        l2: list[MemoryListener] = await nursery.start(
            trio.serve_listeners, handler, listeners
        )
        assert l2 == listeners
        # This is just split into another function because gh-136 isn't
        # implemented yet
        nursery.start_soon(do_tests, nursery)

    for listener in listeners:
        assert listener.closed


async def test_serve_listeners_accept_unrecognized_error() -> None:
    for error in [KeyError(), OSError(errno.ECONNABORTED, "ECONNABORTED")]:
        listener = MemoryListener()

        async def raise_error() -> NoReturn:
            raise error  # noqa: B023  # Set from loop

        def check_error(e: BaseException) -> bool:
            return e is error  # noqa: B023

        listener.accept_hook = raise_error

        with RaisesGroup(Matcher(check=check_error)):
            await trio.serve_listeners(None, [listener])  # type: ignore[arg-type]


async def test_serve_listeners_accept_capacity_error(
    autojump_clock: MockClock, caplog: pytest.LogCaptureFixture
) -> None:
    listener = MemoryListener()

    async def raise_EMFILE() -> NoReturn:
        raise OSError(errno.EMFILE, "out of file descriptors")

    listener.accept_hook = raise_EMFILE

    # It retries every 100 ms, so in 950 ms it will retry at 0, 100, ..., 900
    # = 10 times total
    with trio.move_on_after(0.950):
        await trio.serve_listeners(None, [listener])  # type: ignore[arg-type]

    assert len(caplog.records) == 10
    for record in caplog.records:
        assert "retrying" in record.msg
        assert record.exc_info is not None
        assert isinstance(record.exc_info[1], OSError)
        assert record.exc_info[1].errno == errno.EMFILE


async def test_serve_listeners_connection_nursery(autojump_clock: MockClock) -> None:
    listener = MemoryListener()

    async def handler(stream: Stream) -> None:
        await trio.sleep(1)

    class Done(Exception):
        pass

    async def connection_watcher(
        *, task_status: TaskStatus[Nursery] = trio.TASK_STATUS_IGNORED
    ) -> NoReturn:
        async with trio.open_nursery() as nursery:
            task_status.started(nursery)
            await wait_all_tasks_blocked()
            assert len(nursery.child_tasks) == 10
            raise Done

    # the exception is wrapped twice because we open two nested nurseries
    with RaisesGroup(RaisesGroup(Done)):
        async with trio.open_nursery() as nursery:
            handler_nursery: trio.Nursery = await nursery.start(connection_watcher)
            await nursery.start(
                partial(
                    trio.serve_listeners,
                    handler,
                    [listener],
                    handler_nursery=handler_nursery,
                )
            )
            for _ in range(10):
                nursery.start_soon(listener.connect)
