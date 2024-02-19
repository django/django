from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from .. import _core
from ..testing import check_one_way_stream, wait_all_tasks_blocked

# Mark all the tests in this file as being windows-only
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="windows only")

assert (  # Skip type checking when not on Windows
    sys.platform == "win32" or not TYPE_CHECKING
)

if sys.platform == "win32":
    from asyncio.windows_utils import pipe

    from .._core._windows_cffi import _handle, kernel32
    from .._windows_pipes import PipeReceiveStream, PipeSendStream


async def make_pipe() -> tuple[PipeSendStream, PipeReceiveStream]:
    """Makes a new pair of pipes."""
    (r, w) = pipe()
    return PipeSendStream(w), PipeReceiveStream(r)


async def test_pipe_typecheck() -> None:
    with pytest.raises(TypeError):
        PipeSendStream(1.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        PipeReceiveStream(None)  # type: ignore[arg-type]


async def test_pipe_error_on_close() -> None:
    # Make sure we correctly handle a failure from kernel32.CloseHandle
    r, w = pipe()

    send_stream = PipeSendStream(w)
    receive_stream = PipeReceiveStream(r)

    assert kernel32.CloseHandle(_handle(r))
    assert kernel32.CloseHandle(_handle(w))

    with pytest.raises(OSError, match=r"^\[WinError 6\] The handle is invalid$"):
        await send_stream.aclose()
    with pytest.raises(OSError, match=r"^\[WinError 6\] The handle is invalid$"):
        await receive_stream.aclose()


async def test_pipes_combined() -> None:
    write, read = await make_pipe()
    count = 2**20
    replicas = 3

    async def sender() -> None:
        async with write:
            big = bytearray(count)
            for _ in range(replicas):
                await write.send_all(big)

    async def reader() -> None:
        async with read:
            await wait_all_tasks_blocked()
            total_received = 0
            while True:
                # 5000 is chosen because it doesn't evenly divide 2**20
                received = len(await read.receive_some(5000))
                if not received:
                    break
                total_received += received

            assert total_received == count * replicas

    async with _core.open_nursery() as n:
        n.start_soon(sender)
        n.start_soon(reader)


async def test_async_with() -> None:
    w, r = await make_pipe()
    async with w, r:
        pass

    with pytest.raises(_core.ClosedResourceError):
        await w.send_all(b"")
    with pytest.raises(_core.ClosedResourceError):
        await r.receive_some(10)


async def test_close_during_write() -> None:
    w, r = await make_pipe()
    async with _core.open_nursery() as nursery:

        async def write_forever() -> None:
            with pytest.raises(_core.ClosedResourceError) as excinfo:  # noqa: PT012
                while True:
                    await w.send_all(b"x" * 4096)
            assert "another task" in str(excinfo.value)

        nursery.start_soon(write_forever)
        await wait_all_tasks_blocked(0.1)
        await w.aclose()


async def test_pipe_fully() -> None:
    # passing make_clogged_pipe tests wait_send_all_might_not_block, and we
    # can't implement that on Windows
    await check_one_way_stream(make_pipe, None)
