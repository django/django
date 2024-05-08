from __future__ import annotations

import random
import socket as stdlib_socket
from contextlib import suppress
from typing import TYPE_CHECKING, Awaitable, Callable, Tuple, TypeVar

import pytest

import trio

from ... import _core
from ...testing import assert_checkpoints, wait_all_tasks_blocked

# Cross-platform tests for IO handling

if TYPE_CHECKING:
    from collections.abc import Generator

    from typing_extensions import ParamSpec

    ArgsT = ParamSpec("ArgsT")


def fill_socket(sock: stdlib_socket.socket) -> None:
    try:
        while True:
            sock.send(b"x" * 65536)
    except BlockingIOError:
        pass


def drain_socket(sock: stdlib_socket.socket) -> None:
    try:
        while True:
            sock.recv(65536)
    except BlockingIOError:
        pass


WaitSocket = Callable[[stdlib_socket.socket], Awaitable[object]]
SocketPair = Tuple[stdlib_socket.socket, stdlib_socket.socket]
RetT = TypeVar("RetT")


@pytest.fixture
def socketpair() -> Generator[SocketPair, None, None]:
    pair = stdlib_socket.socketpair()
    for sock in pair:
        sock.setblocking(False)
    yield pair
    for sock in pair:
        sock.close()


def also_using_fileno(
    fn: Callable[[stdlib_socket.socket | int], RetT],
) -> list[Callable[[stdlib_socket.socket], RetT]]:
    def fileno_wrapper(fileobj: stdlib_socket.socket) -> RetT:
        return fn(fileobj.fileno())

    name = f"<{fn.__name__} on fileno>"
    fileno_wrapper.__name__ = fileno_wrapper.__qualname__ = name
    return [fn, fileno_wrapper]


# Decorators that feed in different settings for wait_readable / wait_writable
# / notify_closing.
# Note that if you use all three decorators on the same test, it will run all
# N**3 *combinations*
read_socket_test = pytest.mark.parametrize(
    "wait_readable",
    also_using_fileno(trio.lowlevel.wait_readable),
    ids=lambda fn: fn.__name__,
)
write_socket_test = pytest.mark.parametrize(
    "wait_writable",
    also_using_fileno(trio.lowlevel.wait_writable),
    ids=lambda fn: fn.__name__,
)
notify_closing_test = pytest.mark.parametrize(
    "notify_closing",
    also_using_fileno(trio.lowlevel.notify_closing),
    ids=lambda fn: fn.__name__,
)


# XX These tests are all a bit dicey because they can't distinguish between
# wait_on_{read,writ}able blocking the way it should, versus blocking
# momentarily and then immediately resuming.
@read_socket_test
@write_socket_test
async def test_wait_basic(
    socketpair: SocketPair, wait_readable: WaitSocket, wait_writable: WaitSocket
) -> None:
    a, b = socketpair

    # They start out writable()
    with assert_checkpoints():
        await wait_writable(a)

    # But readable() blocks until data arrives
    record = []

    async def block_on_read() -> None:
        try:
            with assert_checkpoints():
                await wait_readable(a)
        except _core.Cancelled:
            record.append("cancelled")
        else:
            record.append("readable")
            assert a.recv(10) == b"x"

    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_read)
        await wait_all_tasks_blocked()
        assert record == []
        b.send(b"x")

    fill_socket(a)

    # Now writable will block, but readable won't
    with assert_checkpoints():
        await wait_readable(b)
    record = []

    async def block_on_write() -> None:
        try:
            with assert_checkpoints():
                await wait_writable(a)
        except _core.Cancelled:
            record.append("cancelled")
        else:
            record.append("writable")

    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_write)
        await wait_all_tasks_blocked()
        assert record == []
        drain_socket(b)

    # check cancellation
    record = []
    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_read)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
    assert record == ["cancelled"]

    fill_socket(a)
    record = []
    async with _core.open_nursery() as nursery:
        nursery.start_soon(block_on_write)
        await wait_all_tasks_blocked()
        nursery.cancel_scope.cancel()
    assert record == ["cancelled"]


@read_socket_test
async def test_double_read(socketpair: SocketPair, wait_readable: WaitSocket) -> None:
    a, b = socketpair

    # You can't have two tasks trying to read from a socket at the same time
    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_readable, a)
        await wait_all_tasks_blocked()
        with pytest.raises(_core.BusyResourceError):
            await wait_readable(a)
        nursery.cancel_scope.cancel()


@write_socket_test
async def test_double_write(socketpair: SocketPair, wait_writable: WaitSocket) -> None:
    a, b = socketpair

    # You can't have two tasks trying to write to a socket at the same time
    fill_socket(a)
    async with _core.open_nursery() as nursery:
        nursery.start_soon(wait_writable, a)
        await wait_all_tasks_blocked()
        with pytest.raises(_core.BusyResourceError):
            await wait_writable(a)
        nursery.cancel_scope.cancel()


@read_socket_test
@write_socket_test
@notify_closing_test
async def test_interrupted_by_close(
    socketpair: SocketPair,
    wait_readable: WaitSocket,
    wait_writable: WaitSocket,
    notify_closing: Callable[[stdlib_socket.socket], object],
) -> None:
    a, b = socketpair

    async def reader() -> None:
        with pytest.raises(_core.ClosedResourceError):
            await wait_readable(a)

    async def writer() -> None:
        with pytest.raises(_core.ClosedResourceError):
            await wait_writable(a)

    fill_socket(a)

    async with _core.open_nursery() as nursery:
        nursery.start_soon(reader)
        nursery.start_soon(writer)
        await wait_all_tasks_blocked()
        notify_closing(a)


@read_socket_test
@write_socket_test
async def test_socket_simultaneous_read_write(
    socketpair: SocketPair, wait_readable: WaitSocket, wait_writable: WaitSocket
) -> None:
    record: list[str] = []

    async def r_task(sock: stdlib_socket.socket) -> None:
        await wait_readable(sock)
        record.append("r_task")

    async def w_task(sock: stdlib_socket.socket) -> None:
        await wait_writable(sock)
        record.append("w_task")

    a, b = socketpair
    fill_socket(a)
    async with _core.open_nursery() as nursery:
        nursery.start_soon(r_task, a)
        nursery.start_soon(w_task, a)
        await wait_all_tasks_blocked()
        assert record == []
        b.send(b"x")
        await wait_all_tasks_blocked()
        assert record == ["r_task"]
        drain_socket(b)
        await wait_all_tasks_blocked()
        assert record == ["r_task", "w_task"]


@read_socket_test
@write_socket_test
async def test_socket_actual_streaming(
    socketpair: SocketPair, wait_readable: WaitSocket, wait_writable: WaitSocket
) -> None:
    a, b = socketpair

    # Use a small send buffer on one of the sockets to increase the chance of
    # getting partial writes
    a.setsockopt(stdlib_socket.SOL_SOCKET, stdlib_socket.SO_SNDBUF, 10000)

    N = 1000000  # 1 megabyte
    MAX_CHUNK = 65536

    results: dict[str, int] = {}

    async def sender(sock: stdlib_socket.socket, seed: int, key: str) -> None:
        r = random.Random(seed)
        sent = 0
        while sent < N:
            print("sent", sent)
            chunk = bytearray(r.randrange(MAX_CHUNK))
            while chunk:
                with assert_checkpoints():
                    await wait_writable(sock)
                this_chunk_size = sock.send(chunk)
                sent += this_chunk_size
                del chunk[:this_chunk_size]
        sock.shutdown(stdlib_socket.SHUT_WR)
        results[key] = sent

    async def receiver(sock: stdlib_socket.socket, key: str) -> None:
        received = 0
        while True:
            print("received", received)
            with assert_checkpoints():
                await wait_readable(sock)
            this_chunk_size = len(sock.recv(MAX_CHUNK))
            if not this_chunk_size:
                break
            received += this_chunk_size
        results[key] = received

    async with _core.open_nursery() as nursery:
        nursery.start_soon(sender, a, 0, "send_a")
        nursery.start_soon(sender, b, 1, "send_b")
        nursery.start_soon(receiver, a, "recv_a")
        nursery.start_soon(receiver, b, "recv_b")

    assert results["send_a"] == results["recv_b"]
    assert results["send_b"] == results["recv_a"]


async def test_notify_closing_on_invalid_object() -> None:
    # It should either be a no-op (generally on Unix, where we don't know
    # which fds are valid), or an OSError (on Windows, where we currently only
    # support sockets, so we have to do some validation to figure out whether
    # it's a socket or a regular handle).
    got_oserror = False
    got_no_error = False
    try:
        trio.lowlevel.notify_closing(-1)
    except OSError:
        got_oserror = True
    else:
        got_no_error = True
    assert got_oserror or got_no_error


async def test_wait_on_invalid_object() -> None:
    # We definitely want to raise an error everywhere if you pass in an
    # invalid fd to wait_*
    for wait in [trio.lowlevel.wait_readable, trio.lowlevel.wait_writable]:
        with stdlib_socket.socket() as s:
            fileno = s.fileno()
        # We just closed the socket and don't do anything else in between, so
        # we can be confident that the fileno hasn't be reassigned.
        with pytest.raises(
            OSError,
            match=r"^\[\w+ \d+] (Bad file descriptor|An operation was attempted on something that is not a socket)$",
        ):
            await wait(fileno)


async def test_io_manager_statistics() -> None:
    def check(*, expected_readers: int, expected_writers: int) -> None:
        statistics = _core.current_statistics()
        print(statistics)
        iostats = statistics.io_statistics
        if iostats.backend == "epoll" or iostats.backend == "windows":
            assert iostats.tasks_waiting_read == expected_readers
            assert iostats.tasks_waiting_write == expected_writers
        else:
            assert iostats.backend == "kqueue"
            assert iostats.tasks_waiting == expected_readers + expected_writers

    a1, b1 = stdlib_socket.socketpair()
    a2, b2 = stdlib_socket.socketpair()
    a3, b3 = stdlib_socket.socketpair()
    for sock in [a1, b1, a2, b2, a3, b3]:
        sock.setblocking(False)
    with a1, b1, a2, b2, a3, b3:
        # let the call_soon_task settle down
        await wait_all_tasks_blocked()

        # 1 for call_soon_task
        check(expected_readers=1, expected_writers=0)

        # We want:
        # - one socket with a writer blocked
        # - two sockets with a reader blocked
        # - a socket with both blocked
        fill_socket(a1)
        fill_socket(a3)
        async with _core.open_nursery() as nursery:
            nursery.start_soon(_core.wait_writable, a1)
            nursery.start_soon(_core.wait_readable, a2)
            nursery.start_soon(_core.wait_readable, b2)
            nursery.start_soon(_core.wait_writable, a3)
            nursery.start_soon(_core.wait_readable, a3)

            await wait_all_tasks_blocked()

            # +1 for call_soon_task
            check(expected_readers=3 + 1, expected_writers=2)

            nursery.cancel_scope.cancel()

        # 1 for call_soon_task
        check(expected_readers=1, expected_writers=0)


async def test_can_survive_unnotified_close() -> None:
    # An "unnotified" close is when the user closes an fd/socket/handle
    # directly, without calling notify_closing first. This should never happen
    # -- users should call notify_closing before closing things. But, just in
    # case they don't, we would still like to avoid exploding.
    #
    # Acceptable behaviors:
    # - wait_* never return, but can be cancelled cleanly
    # - wait_* exit cleanly
    # - wait_* raise an OSError
    #
    # Not acceptable:
    # - getting stuck in an uncancellable state
    # - TrioInternalError blowing up the whole run
    #
    # This test exercises some tricky "unnotified close" scenarios, to make
    # sure we get the "acceptable" behaviors.

    async def allow_OSError(
        async_func: Callable[ArgsT, Awaitable[object]],
        *args: ArgsT.args,
        **kwargs: ArgsT.kwargs,
    ) -> None:
        with suppress(OSError):
            await async_func(*args, **kwargs)

    with stdlib_socket.socket() as s:
        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, s)
            await wait_all_tasks_blocked()
            s.close()
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    # We hit different paths on Windows depending on whether we close the last
    # handle to the object (which produces a LOCAL_CLOSE notification and
    # wakes up wait_readable), or only close one of the handles (which leaves
    # wait_readable pending until cancelled).
    with stdlib_socket.socket() as s, s.dup() as s2:  # noqa: F841
        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, s)
            await wait_all_tasks_blocked()
            s.close()
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()

    # A more elaborate case, with two tasks waiting. On windows and epoll,
    # the two tasks get muxed together onto a single underlying wait
    # operation. So when they're cancelled, there's a brief moment where one
    # of the tasks is cancelled but the other isn't, so we try to re-issue the
    # underlying wait operation. But here, the handle we were going to use to
    # do that has been pulled out from under our feet... so test that we can
    # survive this.
    a, b = stdlib_socket.socketpair()
    with a, b, a.dup() as a2:
        a.setblocking(False)
        b.setblocking(False)
        fill_socket(a)
        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, a)
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_writable, a)
            await wait_all_tasks_blocked()
            a.close()
            nursery.cancel_scope.cancel()

    # A similar case, but now the single-task-wakeup happens due to I/O
    # arriving, not a cancellation, so the operation gets re-issued from
    # handle_io context rather than abort context.
    a, b = stdlib_socket.socketpair()
    with a, b, a.dup() as a2:
        print(f"a={a.fileno()}, b={b.fileno()}, a2={a2.fileno()}")
        a.setblocking(False)
        b.setblocking(False)
        fill_socket(a)
        e = trio.Event()

        # We want to wait for the kernel to process the wakeup on 'a', if any.
        # But depending on the platform, we might not get a wakeup on 'a'. So
        # we put one task to sleep waiting on 'a', and we put a second task to
        # sleep waiting on 'a2', with the idea that the 'a2' notification will
        # definitely arrive, and when it does then we can assume that whatever
        # notification was going to arrive for 'a' has also arrived.
        async def wait_readable_a2_then_set() -> None:
            await trio.lowlevel.wait_readable(a2)
            e.set()

        async with trio.open_nursery() as nursery:
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_readable, a)
            nursery.start_soon(allow_OSError, trio.lowlevel.wait_writable, a)
            nursery.start_soon(wait_readable_a2_then_set)
            await wait_all_tasks_blocked()
            a.close()
            b.send(b"x")
            # Make sure that the wakeup has been received and everything has
            # settled before cancelling the wait_writable.
            await e.wait()
            await wait_all_tasks_blocked()
            nursery.cancel_scope.cancel()
