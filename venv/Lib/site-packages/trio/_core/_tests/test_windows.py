from __future__ import annotations

import os
import sys
import tempfile
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import create_autospec

import pytest

on_windows = os.name == "nt"
# Mark all the tests in this file as being windows-only
pytestmark = pytest.mark.skipif(not on_windows, reason="windows only")

assert (
    sys.platform == "win32" or not TYPE_CHECKING
)  # Skip type checking when not on Windows

from ... import _core, sleep
from ...testing import wait_all_tasks_blocked
from .tutil import gc_collect_harder, restore_unraisablehook, slow

if TYPE_CHECKING:
    from collections.abc import Generator
    from io import BufferedWriter

if on_windows:
    from .._windows_cffi import (
        INVALID_HANDLE_VALUE,
        FileFlags,
        Handle,
        ffi,
        kernel32,
        raise_winerror,
    )


def test_winerror(monkeypatch: pytest.MonkeyPatch) -> None:
    # this is unfortunately needed as the generated ffi is read-only
    class FFIWrapper:
        def getwinerror(self) -> None:
            raise NotImplementedError("this is a fake implementation")

    mock = create_autospec(ffi.getwinerror)
    monkeypatch.setattr("trio._core._windows_cffi.ffi", FFIWrapper)
    monkeypatch.setattr("trio._core._windows_cffi.ffi.getwinerror", mock)

    # Returning none = no error, should not happen.
    mock.return_value = None
    with pytest.raises(RuntimeError, match=r"^No error set\?$"):
        raise_winerror()
    mock.assert_called_once_with()
    mock.reset_mock()

    with pytest.raises(RuntimeError, match=r"^No error set\?$"):
        raise_winerror(38)
    mock.assert_called_once_with(38)
    mock.reset_mock()

    mock.return_value = (12, "test error")
    with pytest.raises(
        OSError,
        match=r"^\[WinError 12\] test error: 'file_1' -> 'file_2'$",
    ) as exc:
        raise_winerror(filename="file_1", filename2="file_2")
    mock.assert_called_once_with()
    mock.reset_mock()
    assert exc.value.winerror == 12
    assert exc.value.strerror == "test error"
    assert exc.value.filename == "file_1"
    assert exc.value.filename2 == "file_2"

    # With an explicit number passed in, it overrides what getwinerror() returns.
    with pytest.raises(
        OSError,
        match=r"^\[WinError 18\] test error: 'a/file' -> 'b/file'$",
    ) as exc:
        raise_winerror(18, filename="a/file", filename2="b/file")
    mock.assert_called_once_with(18)
    mock.reset_mock()
    assert exc.value.winerror == 18
    assert exc.value.strerror == "test error"
    assert exc.value.filename == "a/file"
    assert exc.value.filename2 == "b/file"


# The undocumented API that this is testing should be changed to stop using
# UnboundedQueue (or just removed until we have time to redo it), but until
# then we filter out the warning.
@pytest.mark.filterwarnings("ignore:.*UnboundedQueue:trio.TrioDeprecationWarning")
async def test_completion_key_listen() -> None:
    from .. import _io_windows

    async def post(key: int) -> None:
        iocp = Handle(ffi.cast("HANDLE", _core.current_iocp()))
        for i in range(10):
            print("post", i)
            if i % 3 == 0:
                await _core.checkpoint()
            success = kernel32.PostQueuedCompletionStatus(iocp, i, key, ffi.NULL)
            assert success

    with _core.monitor_completion_key() as (key, queue):
        async with _core.open_nursery() as nursery:
            nursery.start_soon(post, key)
            i = 0
            print("loop")
            async for batch in queue:  # pragma: no branch
                print("got some", batch)
                for info in batch:
                    assert isinstance(info, _io_windows.CompletionKeyEventInfo)
                    assert info.lpOverlapped == 0
                    assert info.dwNumberOfBytesTransferred == i
                    i += 1
                if i == 10:
                    break
            print("end loop")


async def test_readinto_overlapped() -> None:
    data = b"1" * 1024 + b"2" * 1024 + b"3" * 1024 + b"4" * 1024
    buffer = bytearray(len(data))

    with tempfile.TemporaryDirectory() as tdir:
        tfile = os.path.join(tdir, "numbers.txt")
        with open(  # noqa: ASYNC230  # This is a test, synchronous is ok
            tfile,
            "wb",
        ) as fp:
            fp.write(data)
            fp.flush()

        rawname = tfile.encode("utf-16le") + b"\0\0"
        rawname_buf = ffi.from_buffer(rawname)
        handle = kernel32.CreateFileW(
            ffi.cast("LPCWSTR", rawname_buf),
            FileFlags.GENERIC_READ,
            FileFlags.FILE_SHARE_READ,
            ffi.NULL,  # no security attributes
            FileFlags.OPEN_EXISTING,
            FileFlags.FILE_FLAG_OVERLAPPED,
            ffi.NULL,  # no template file
        )
        if handle == INVALID_HANDLE_VALUE:  # pragma: no cover
            raise_winerror()

        try:
            with memoryview(buffer) as buffer_view:

                async def read_region(start: int, end: int) -> None:
                    await _core.readinto_overlapped(
                        handle,
                        buffer_view[start:end],
                        start,
                    )

                _core.register_with_iocp(handle)
                async with _core.open_nursery() as nursery:
                    for start in range(0, 4096, 512):
                        nursery.start_soon(read_region, start, start + 512)

                assert buffer == data

                with pytest.raises((BufferError, TypeError)):
                    await _core.readinto_overlapped(handle, b"immutable")
        finally:
            kernel32.CloseHandle(handle)


@contextmanager
def pipe_with_overlapped_read() -> Generator[tuple[BufferedWriter, int], None, None]:
    import msvcrt
    from asyncio.windows_utils import pipe

    read_handle, write_handle = pipe(overlapped=(True, False))
    try:
        write_fd = msvcrt.open_osfhandle(write_handle, 0)
        yield os.fdopen(write_fd, "wb", closefd=False), read_handle
    finally:
        kernel32.CloseHandle(Handle(ffi.cast("HANDLE", read_handle)))
        kernel32.CloseHandle(Handle(ffi.cast("HANDLE", write_handle)))


@restore_unraisablehook()
def test_forgot_to_register_with_iocp() -> None:
    with pipe_with_overlapped_read() as (write_fp, read_handle):
        with write_fp:
            write_fp.write(b"test\n")

        left_run_yet = False

        async def main() -> None:
            target = bytearray(1)
            try:
                async with _core.open_nursery() as nursery:
                    nursery.start_soon(
                        _core.readinto_overlapped,
                        read_handle,
                        target,
                        name="xyz",
                    )
                    await wait_all_tasks_blocked()
                    nursery.cancel_scope.cancel()
            finally:
                # Run loop is exited without unwinding running tasks, so
                # we don't get here until the main() coroutine is GC'ed
                assert left_run_yet

        with pytest.raises(_core.TrioInternalError) as exc_info:
            _core.run(main)
        left_run_yet = True
        assert "Failed to cancel overlapped I/O in xyz " in str(exc_info.value)
        assert "forget to call register_with_iocp()?" in str(exc_info.value)

        # Make sure the Nursery.__del__ assertion about dangling children
        # gets put with the correct test
        del exc_info
        gc_collect_harder()


@slow
async def test_too_late_to_cancel() -> None:
    import time

    with pipe_with_overlapped_read() as (write_fp, read_handle):
        _core.register_with_iocp(read_handle)
        target = bytearray(6)
        async with _core.open_nursery() as nursery:
            # Start an async read in the background
            nursery.start_soon(_core.readinto_overlapped, read_handle, target)
            await wait_all_tasks_blocked()

            # Synchronous write to the other end of the pipe
            with write_fp:
                write_fp.write(b"test1\ntest2\n")

            # Note: not trio.sleep! We're making sure the OS level
            # ReadFile completes, before Trio has a chance to execute
            # another checkpoint and notice it completed.
            time.sleep(1)  # noqa: ASYNC251
            nursery.cancel_scope.cancel()
        assert target[:6] == b"test1\n"

        # Do another I/O to make sure we've actually processed the
        # fallback completion that was posted when CancelIoEx failed.
        assert await _core.readinto_overlapped(read_handle, target) == 6
        assert target[:6] == b"test2\n"


def test_lsp_that_hooks_select_gives_good_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from .. import _io_windows
    from .._windows_cffi import CData, WSAIoctls, _handle

    def patched_get_underlying(
        sock: int | CData,
        *,
        which: int = WSAIoctls.SIO_BASE_HANDLE,
    ) -> CData:
        if hasattr(sock, "fileno"):  # pragma: no branch
            sock = sock.fileno()
        if which == WSAIoctls.SIO_BSP_HANDLE_SELECT:
            return _handle(sock + 1)
        else:
            return _handle(sock)

    monkeypatch.setattr(_io_windows, "_get_underlying_socket", patched_get_underlying)
    with pytest.raises(
        RuntimeError,
        match="SIO_BASE_HANDLE and SIO_BSP_HANDLE_SELECT differ",
    ):
        _core.run(sleep, 0)


def test_lsp_that_completely_hides_base_socket_gives_good_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This tests behavior with an LSP that fails SIO_BASE_HANDLE and returns
    # self for SIO_BSP_HANDLE_SELECT (like Komodia), but also returns
    # self for SIO_BSP_HANDLE_POLL. No known LSP does this, but we want to
    # make sure we get an error rather than an infinite loop.

    from .. import _io_windows
    from .._windows_cffi import CData, WSAIoctls, _handle

    def patched_get_underlying(
        sock: int | CData,
        *,
        which: int = WSAIoctls.SIO_BASE_HANDLE,
    ) -> CData:
        if hasattr(sock, "fileno"):  # pragma: no branch
            sock = sock.fileno()
        if which == WSAIoctls.SIO_BASE_HANDLE:
            raise OSError("nope")
        else:
            return _handle(sock)

    monkeypatch.setattr(_io_windows, "_get_underlying_socket", patched_get_underlying)
    with pytest.raises(
        RuntimeError,
        match="SIO_BASE_HANDLE failed and SIO_BSP_HANDLE_POLL didn't return a diff",
    ):
        _core.run(sleep, 0)
