import os
import socket
import sys
import tempfile
from typing import TYPE_CHECKING

import pytest

from trio import Path, open_unix_socket
from trio._highlevel_open_unix_stream import close_on_error

assert not TYPE_CHECKING or sys.platform != "win32"

skip_if_not_unix = pytest.mark.skipif(
    not hasattr(socket, "AF_UNIX"),
    reason="Needs unix socket support",
)


@skip_if_not_unix
def test_close_on_error() -> None:
    class CloseMe:
        closed = False

        def close(self) -> None:
            self.closed = True

    with close_on_error(CloseMe()) as c:
        pass
    assert not c.closed

    with pytest.raises(RuntimeError):
        with close_on_error(CloseMe()) as c:
            raise RuntimeError
    assert c.closed


@skip_if_not_unix
@pytest.mark.parametrize("filename", [4, 4.5])
async def test_open_with_bad_filename_type(filename: float) -> None:
    with pytest.raises(TypeError):
        await open_unix_socket(filename)  # type: ignore[arg-type]


@skip_if_not_unix
async def test_open_bad_socket() -> None:
    # mktemp is marked as insecure, but that's okay, we don't want the file to
    # exist
    name = tempfile.mktemp()
    with pytest.raises(FileNotFoundError):
        await open_unix_socket(name)


@skip_if_not_unix
async def test_open_unix_socket() -> None:
    for name_type in [Path, str]:
        name = tempfile.mktemp()
        serv_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        with serv_sock:
            serv_sock.bind(name)
            try:
                serv_sock.listen(1)

                # The actual function we're testing
                unix_socket = await open_unix_socket(name_type(name))

                async with unix_socket:
                    client, _ = serv_sock.accept()
                    with client:
                        await unix_socket.send_all(b"test")
                        assert client.recv(2048) == b"test"

                        client.sendall(b"response")
                        received = await unix_socket.receive_some(2048)
                        assert received == b"response"
            finally:
                os.unlink(name)


@pytest.mark.skipif(hasattr(socket, "AF_UNIX"), reason="Test for non-unix platforms")
async def test_error_on_no_unix() -> None:
    with pytest.raises(
        RuntimeError,
        match=r"^Unix sockets are not supported on this platform$",
    ):
        await open_unix_socket("")
