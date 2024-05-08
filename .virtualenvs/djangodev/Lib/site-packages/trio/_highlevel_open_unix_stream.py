from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol, TypeVar

import trio
from trio.socket import SOCK_STREAM, socket

if TYPE_CHECKING:
    from collections.abc import Generator


class Closable(Protocol):
    def close(self) -> None: ...


CloseT = TypeVar("CloseT", bound=Closable)


try:
    from trio.socket import AF_UNIX

    has_unix = True
except ImportError:
    has_unix = False


@contextmanager
def close_on_error(obj: CloseT) -> Generator[CloseT, None, None]:
    try:
        yield obj
    except:
        obj.close()
        raise


async def open_unix_socket(
    filename: str | bytes | os.PathLike[str] | os.PathLike[bytes],
) -> trio.SocketStream:
    """Opens a connection to the specified
    `Unix domain socket <https://en.wikipedia.org/wiki/Unix_domain_socket>`__.

    You must have read/write permission on the specified file to connect.

    Args:
      filename (str or bytes): The filename to open the connection to.

    Returns:
      SocketStream: a :class:`~trio.abc.Stream` connected to the given file.

    Raises:
      OSError: If the socket file could not be connected to.
      RuntimeError: If AF_UNIX sockets are not supported.
    """
    if not has_unix:
        raise RuntimeError("Unix sockets are not supported on this platform")

    # much more simplified logic vs tcp sockets - one socket type and only one
    # possible location to connect to
    sock = socket(AF_UNIX, SOCK_STREAM)
    with close_on_error(sock):
        await sock.connect(os.fspath(filename))

    return trio.SocketStream(sock)
