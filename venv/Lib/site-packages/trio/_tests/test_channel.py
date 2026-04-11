from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

import trio
from trio import EndOfChannel, as_safe_channel, open_memory_channel

from ..testing import assert_checkpoints, wait_all_tasks_blocked

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


async def test_channel() -> None:
    with pytest.raises(TypeError):
        open_memory_channel(1.0)
    with pytest.raises(ValueError, match=r"^max_buffer_size must be >= 0$"):
        open_memory_channel(-1)

    s, r = open_memory_channel[int | str | None](2)
    repr(s)  # smoke test
    repr(r)  # smoke test

    s.send_nowait(1)
    with assert_checkpoints():
        await s.send(2)
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(None)

    with assert_checkpoints():
        assert await r.receive() == 1
    assert r.receive_nowait() == 2
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()

    s.send_nowait("last")
    await s.aclose()
    with pytest.raises(trio.ClosedResourceError):
        await s.send("too late")
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait("too late")
    with pytest.raises(trio.ClosedResourceError):
        s.clone()
    await s.aclose()

    assert r.receive_nowait() == "last"
    with pytest.raises(EndOfChannel):
        await r.receive()
    await r.aclose()
    with pytest.raises(trio.ClosedResourceError):
        await r.receive()
    with pytest.raises(trio.ClosedResourceError):
        r.receive_nowait()
    await r.aclose()


async def test_553(autojump_clock: trio.abc.Clock) -> None:
    s, r = open_memory_channel[str](1)
    with trio.move_on_after(10) as timeout_scope:
        await r.receive()
    assert timeout_scope.cancelled_caught
    await s.send("Test for PR #553")


async def test_channel_multiple_producers() -> None:
    async def producer(send_channel: trio.MemorySendChannel[int], i: int) -> None:
        # We close our handle when we're done with it
        async with send_channel:
            for j in range(3 * i, 3 * (i + 1)):
                await send_channel.send(j)

    send_channel, receive_channel = open_memory_channel[int](0)
    async with trio.open_nursery() as nursery:
        # We hand out clones to all the new producers, and then close the
        # original.
        async with send_channel:
            for i in range(10):
                nursery.start_soon(producer, send_channel.clone(), i)

        got = [value async for value in receive_channel]

        got.sort()
        assert got == list(range(30))


async def test_channel_multiple_consumers() -> None:
    successful_receivers = set()
    received = []

    async def consumer(receive_channel: trio.MemoryReceiveChannel[int], i: int) -> None:
        async for value in receive_channel:
            successful_receivers.add(i)
            received.append(value)

    async with trio.open_nursery() as nursery:
        send_channel, receive_channel = trio.open_memory_channel[int](1)
        async with send_channel:
            for i in range(5):
                nursery.start_soon(consumer, receive_channel, i)
            await wait_all_tasks_blocked()
            for i in range(10):
                await send_channel.send(i)

    assert successful_receivers == set(range(5))
    assert len(received) == 10
    assert set(received) == set(range(10))


async def test_close_basics() -> None:
    async def send_block(
        s: trio.MemorySendChannel[None],
        expect: type[BaseException],
    ) -> None:
        with pytest.raises(expect):
            await s.send(None)

    # closing send -> other send gets ClosedResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.ClosedResourceError)
        await wait_all_tasks_blocked()
        await s.aclose()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.ClosedResourceError):
        await s.send(None)

    # and receive gets EndOfChannel
    with pytest.raises(EndOfChannel):
        r.receive_nowait()
    with pytest.raises(EndOfChannel):
        await r.receive()

    # closing receive -> send gets BrokenResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.BrokenResourceError)
        await wait_all_tasks_blocked()
        await r.aclose()

    # and it's persistent
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.BrokenResourceError):
        await s.send(None)

    # closing receive -> other receive gets ClosedResourceError
    async def receive_block(r: trio.MemoryReceiveChannel[int]) -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r.receive()

    _s2, r2 = open_memory_channel[int](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_block, r2)
        await wait_all_tasks_blocked()
        await r2.aclose()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        r2.receive_nowait()
    with pytest.raises(trio.ClosedResourceError):
        await r2.receive()


async def test_close_sync() -> None:
    async def send_block(
        s: trio.MemorySendChannel[None],
        expect: type[BaseException],
    ) -> None:
        with pytest.raises(expect):
            await s.send(None)

    # closing send -> other send gets ClosedResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.ClosedResourceError)
        await wait_all_tasks_blocked()
        s.close()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.ClosedResourceError):
        await s.send(None)

    # and receive gets EndOfChannel
    with pytest.raises(EndOfChannel):
        r.receive_nowait()
    with pytest.raises(EndOfChannel):
        await r.receive()

    # closing receive -> send gets BrokenResourceError
    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_block, s, trio.BrokenResourceError)
        await wait_all_tasks_blocked()
        r.close()

    # and it's persistent
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)
    with pytest.raises(trio.BrokenResourceError):
        await s.send(None)

    # closing receive -> other receive gets ClosedResourceError
    async def receive_block(r: trio.MemoryReceiveChannel[None]) -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r.receive()

    s, r = open_memory_channel[None](0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_block, r)
        await wait_all_tasks_blocked()
        r.close()

    # and it's persistent
    with pytest.raises(trio.ClosedResourceError):
        r.receive_nowait()
    with pytest.raises(trio.ClosedResourceError):
        await r.receive()


async def test_receive_channel_clone_and_close() -> None:
    s, r = open_memory_channel[None](10)

    r2 = r.clone()
    r3 = r.clone()

    s.send_nowait(None)
    await r.aclose()
    with r2:
        pass

    with pytest.raises(trio.ClosedResourceError):
        r.clone()

    with pytest.raises(trio.ClosedResourceError):
        r2.clone()

    # Can still send, r3 is still open
    s.send_nowait(None)

    await r3.aclose()

    # But now the receiver is really closed
    with pytest.raises(trio.BrokenResourceError):
        s.send_nowait(None)


async def test_close_multiple_send_handles() -> None:
    # With multiple send handles, closing one handle only wakes senders on
    # that handle, but others can continue just fine
    s1, r = open_memory_channel[str](0)
    s2 = s1.clone()

    async def send_will_close() -> None:
        with pytest.raises(trio.ClosedResourceError):
            await s1.send("nope")

    async def send_will_succeed() -> None:
        await s2.send("ok")

    async with trio.open_nursery() as nursery:
        nursery.start_soon(send_will_close)
        nursery.start_soon(send_will_succeed)
        await wait_all_tasks_blocked()
        await s1.aclose()
        assert await r.receive() == "ok"


async def test_close_multiple_receive_handles() -> None:
    # With multiple receive handles, closing one handle only wakes receivers on
    # that handle, but others can continue just fine
    s, r1 = open_memory_channel[str](0)
    r2 = r1.clone()

    async def receive_will_close() -> None:
        with pytest.raises(trio.ClosedResourceError):
            await r1.receive()

    async def receive_will_succeed() -> None:
        assert await r2.receive() == "ok"

    async with trio.open_nursery() as nursery:
        nursery.start_soon(receive_will_close)
        nursery.start_soon(receive_will_succeed)
        await wait_all_tasks_blocked()
        await r1.aclose()
        await s.send("ok")


async def test_inf_capacity() -> None:
    send, receive = open_memory_channel[int](float("inf"))

    # It's accepted, and we can send all day without blocking
    with send:
        for i in range(10):
            send.send_nowait(i)

    got = [i async for i in receive]
    assert got == list(range(10))


async def test_statistics() -> None:
    s, r = open_memory_channel[None](2)

    assert s.statistics() == r.statistics()
    stats = s.statistics()
    assert stats.current_buffer_used == 0
    assert stats.max_buffer_size == 2
    assert stats.open_send_channels == 1
    assert stats.open_receive_channels == 1
    assert stats.tasks_waiting_send == 0
    assert stats.tasks_waiting_receive == 0

    s.send_nowait(None)
    assert s.statistics().current_buffer_used == 1

    s2 = s.clone()
    assert s.statistics().open_send_channels == 2
    await s.aclose()
    assert s2.statistics().open_send_channels == 1

    r2 = r.clone()
    assert s2.statistics().open_receive_channels == 2
    await r2.aclose()
    assert s2.statistics().open_receive_channels == 1

    async with trio.open_nursery() as nursery:
        s2.send_nowait(None)  # fill up the buffer
        assert s.statistics().current_buffer_used == 2
        nursery.start_soon(s2.send, None)
        nursery.start_soon(s2.send, None)
        await wait_all_tasks_blocked()
        assert s.statistics().tasks_waiting_send == 2
        nursery.cancel_scope.cancel()
    assert s.statistics().tasks_waiting_send == 0

    # empty out the buffer again
    try:
        while True:
            r.receive_nowait()
    except trio.WouldBlock:
        pass

    async with trio.open_nursery() as nursery:
        nursery.start_soon(r.receive)
        await wait_all_tasks_blocked()
        assert s.statistics().tasks_waiting_receive == 1
        nursery.cancel_scope.cancel()
    assert s.statistics().tasks_waiting_receive == 0


async def test_channel_fairness() -> None:
    # We can remove an item we just sent, and send an item back in after, if
    # no-one else is waiting.
    s, r = open_memory_channel[int | None](1)
    s.send_nowait(1)
    assert r.receive_nowait() == 1
    s.send_nowait(2)
    assert r.receive_nowait() == 2

    # But if someone else is waiting to receive, then they "own" the item we
    # send, so we can't receive it (even though we run first):

    result: int | None = None

    async def do_receive(r: trio.MemoryReceiveChannel[int | None]) -> None:
        nonlocal result
        result = await r.receive()

    async with trio.open_nursery() as nursery:
        nursery.start_soon(do_receive, r)
        await wait_all_tasks_blocked()
        s.send_nowait(2)
        with pytest.raises(trio.WouldBlock):
            r.receive_nowait()
    assert result == 2

    # And the analogous situation for send: if we free up a space, we can't
    # immediately send something in it if someone is already waiting to do
    # that
    s, r = open_memory_channel[int | None](1)
    s.send_nowait(1)
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(None)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(s.send, 2)
        await wait_all_tasks_blocked()
        assert r.receive_nowait() == 1
        with pytest.raises(trio.WouldBlock):
            s.send_nowait(3)
        assert (await r.receive()) == 2


async def test_unbuffered() -> None:
    s, r = open_memory_channel[int](0)
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()
    with pytest.raises(trio.WouldBlock):
        s.send_nowait(1)

    async def do_send(s: trio.MemorySendChannel[int], v: int) -> None:
        with assert_checkpoints():
            await s.send(v)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(do_send, s, 1)
        with assert_checkpoints():
            assert await r.receive() == 1
    with pytest.raises(trio.WouldBlock):
        r.receive_nowait()


async def test_as_safe_channel_exhaust() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1

    async with agen() as recv_chan:
        async for x in recv_chan:
            assert x == 1


async def test_as_safe_channel_broken_resource() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        yield 2  # pragma: no cover

    async with agen() as recv_chan:
        assert await recv_chan.__anext__() == 1

        # close the receiving channel
        await recv_chan.aclose()

        # trying to get the next element errors
        with pytest.raises(trio.ClosedResourceError):
            await recv_chan.__anext__()

        # but we don't get an error on exit of the cm


async def test_as_safe_channel_cancelled() -> None:
    with trio.CancelScope() as cs:

        @as_safe_channel
        async def agen() -> AsyncGenerator[None]:  # pragma: no cover
            raise AssertionError(
                "cancel before consumption means generator should not be iterated"
            )
            yield  # indicate that we're an iterator

        async with agen():
            cs.cancel()


async def test_as_safe_channel_no_race() -> None:
    # this previously led to a race condition due to
    # https://github.com/python-trio/trio/issues/1559
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise ValueError("oae")

    with pytest.raises(ValueError, match=r"^oae$"):
        async with agen() as recv_chan:
            async for x in recv_chan:
                assert x == 1


async def test_as_safe_channel_buffer_size_too_small(
    autojump_clock: trio.testing.MockClock,
) -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise AssertionError(
            "buffer size 0 means we shouldn't be asked for another value"
        )  # pragma: no cover

    with trio.move_on_after(5):
        async with agen() as recv_chan:
            async for x in recv_chan:  # pragma: no branch
                assert x == 1
                await trio.sleep_forever()


async def test_as_safe_channel_no_interleave() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        yield 1
        raise AssertionError  # pragma: no cover

    async with agen() as recv_chan:
        assert await recv_chan.__anext__() == 1
        await trio.lowlevel.checkpoint()


async def test_as_safe_channel_genexit_finally() -> None:
    @as_safe_channel
    async def agen(events: list[str]) -> AsyncGenerator[int]:
        try:
            yield 1
        except BaseException as e:
            events.append(repr(e))
            raise
        finally:
            events.append("finally")
            raise ValueError("agen")

    events: list[str] = []
    with pytest.RaisesGroup(
        pytest.RaisesExc(ValueError, match="^agen$"),
        pytest.RaisesExc(TypeError, match="^iterator$"),
    ) as g:
        async with agen(events) as recv_chan:
            async for i in recv_chan:  # pragma: no branch
                assert i == 1
                raise TypeError("iterator")

    if sys.version_info >= (3, 11):
        assert g.value.__notes__ == [
            "Encountered exception during cleanup of generator object, as "
            "well as exception in the contextmanager body - unable to unwrap."
        ]

    assert events == ["GeneratorExit()", "finally"]


async def test_as_safe_channel_nested_loop() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        for i in range(2):
            yield i

    ii = 0
    async with agen() as recv_chan1:
        async for i in recv_chan1:
            async with agen() as recv_chan:
                jj = 0
                async for j in recv_chan:
                    assert (i, j) == (ii, jj)
                    jj += 1
            ii += 1


async def test_as_safe_channel_doesnt_leak_cancellation() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        yield
        with trio.CancelScope() as cscope:
            cscope.cancel()
            yield

    with pytest.raises(AssertionError):
        async with agen() as recv_chan:
            async for _ in recv_chan:
                pass
        raise AssertionError("should be reachable")


async def test_as_safe_channel_dont_unwrap_user_exceptiongroup() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        raise NotImplementedError("not entered")
        yield  # pragma: no cover

    with pytest.RaisesGroup(pytest.RaisesExc(ValueError, match="bar"), match="foo"):
        async with agen() as _:
            raise ExceptionGroup("foo", [ValueError("bar")])


async def test_as_safe_channel_multiple_receiver() -> None:
    event = trio.Event()

    @as_safe_channel
    async def agen() -> AsyncGenerator[int]:
        await event.wait()
        yield 0
        yield 1

    async def handle_value(
        recv_chan: trio.abc.ReceiveChannel[int],
        value: int,
        task_status: trio.TaskStatus,
    ) -> None:
        task_status.started()
        assert await recv_chan.receive() == value

    async with agen() as recv_chan:
        async with trio.open_nursery() as nursery:
            await nursery.start(handle_value, recv_chan, 0)
            await nursery.start(handle_value, recv_chan, 1)
            event.set()


async def test_as_safe_channel_multi_cancel() -> None:
    @as_safe_channel
    async def agen(events: list[str]) -> AsyncGenerator[None]:
        try:
            yield
        finally:
            # this will give a warning of ASYNC120, although it's not technically a
            # problem of swallowing existing exceptions
            try:
                await trio.lowlevel.checkpoint()
            except trio.Cancelled:
                events.append("agen cancel")
                raise

    events: list[str] = []
    with trio.CancelScope() as cs:
        with pytest.raises(trio.Cancelled):
            async with agen(events) as recv_chan:
                async for _ in recv_chan:  # pragma: no branch
                    cs.cancel()
                    try:
                        await trio.lowlevel.checkpoint()
                    except trio.Cancelled:
                        events.append("body cancel")
                        raise
    assert events == ["body cancel", "agen cancel"]


async def test_as_safe_channel_genexit_exception_group() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        try:
            async with trio.open_nursery():
                yield
        except BaseException as e:
            assert pytest.RaisesGroup(GeneratorExit).matches(e)  # noqa: PT017
            raise

    async with agen() as g:
        async for _ in g:
            break


async def test_as_safe_channel_does_not_suppress_nested_genexit() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        yield

    with pytest.RaisesGroup(GeneratorExit):
        async with agen() as g, trio.open_nursery():
            await g.receive()  # this is for coverage reasons
            raise GeneratorExit


async def test_as_safe_channel_genexit_filter() -> None:
    async def wait_then_raise() -> None:
        try:
            await trio.sleep_forever()
        except trio.Cancelled:
            raise ValueError from None

    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(wait_then_raise)
            yield

    with pytest.RaisesGroup(ValueError):
        async with agen() as g:
            async for _ in g:
                break


async def test_as_safe_channel_swallowing_extra_exceptions() -> None:
    async def wait_then_raise(ex: type[BaseException]) -> None:
        try:
            await trio.sleep_forever()
        except trio.Cancelled:
            raise ex from None

    @as_safe_channel
    async def agen(ex: type[BaseException]) -> AsyncGenerator[None]:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(wait_then_raise, ex)
            nursery.start_soon(wait_then_raise, GeneratorExit)
            yield

    with pytest.RaisesGroup(AssertionError):
        async with agen(GeneratorExit) as g:
            async for _ in g:
                break

    with pytest.RaisesGroup(ValueError, AssertionError):
        async with agen(ValueError) as g:
            async for _ in g:
                break


async def test_as_safe_channel_close_between_iteration() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        while True:
            yield

    async with agen() as chan, trio.open_nursery() as nursery:

        async def close_channel() -> None:
            await trio.lowlevel.checkpoint()
            await chan.aclose()

        nursery.start_soon(close_channel)
        with pytest.raises(trio.ClosedResourceError):
            async for _ in chan:
                pass


async def test_as_safe_channel_close_before_iteration() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        raise AssertionError("should be unreachable")  # pragma: no cover
        yield  # pragma: no cover

    async with agen() as chan:
        await chan.aclose()
        with pytest.raises(trio.ClosedResourceError):
            await chan.receive()


async def test_as_safe_channel_close_during_iteration() -> None:
    @as_safe_channel
    async def agen() -> AsyncGenerator[None]:
        yield
        await chan.aclose()
        while True:
            yield

    async with agen() as chan:
        with pytest.raises(trio.ClosedResourceError):
            async for _ in chan:
                pass

        # This is necessary to ensure that `chan` has been sent
        # to. Otherwise, this test sometimes passes on a broken
        # version of trio.
        await trio.testing.wait_all_tasks_blocked()
