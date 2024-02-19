import errno
import io
import socket
from io import SEEK_END
from typing import Optional, Union

from ..exceptions import ConnectionError, TimeoutError
from ..utils import SSL_AVAILABLE

NONBLOCKING_EXCEPTION_ERROR_NUMBERS = {BlockingIOError: errno.EWOULDBLOCK}

if SSL_AVAILABLE:
    import ssl

    if hasattr(ssl, "SSLWantReadError"):
        NONBLOCKING_EXCEPTION_ERROR_NUMBERS[ssl.SSLWantReadError] = 2
        NONBLOCKING_EXCEPTION_ERROR_NUMBERS[ssl.SSLWantWriteError] = 2
    else:
        NONBLOCKING_EXCEPTION_ERROR_NUMBERS[ssl.SSLError] = 2

NONBLOCKING_EXCEPTIONS = tuple(NONBLOCKING_EXCEPTION_ERROR_NUMBERS.keys())

SERVER_CLOSED_CONNECTION_ERROR = "Connection closed by server."
SENTINEL = object()

SYM_CRLF = b"\r\n"


class SocketBuffer:
    def __init__(
        self, socket: socket.socket, socket_read_size: int, socket_timeout: float
    ):
        self._sock = socket
        self.socket_read_size = socket_read_size
        self.socket_timeout = socket_timeout
        self._buffer = io.BytesIO()

    def unread_bytes(self) -> int:
        """
        Remaining unread length of buffer
        """
        pos = self._buffer.tell()
        end = self._buffer.seek(0, SEEK_END)
        self._buffer.seek(pos)
        return end - pos

    def _read_from_socket(
        self,
        length: Optional[int] = None,
        timeout: Union[float, object] = SENTINEL,
        raise_on_timeout: Optional[bool] = True,
    ) -> bool:
        sock = self._sock
        socket_read_size = self.socket_read_size
        marker = 0
        custom_timeout = timeout is not SENTINEL

        buf = self._buffer
        current_pos = buf.tell()
        buf.seek(0, SEEK_END)
        if custom_timeout:
            sock.settimeout(timeout)
        try:
            while True:
                data = self._sock.recv(socket_read_size)
                # an empty string indicates the server shutdown the socket
                if isinstance(data, bytes) and len(data) == 0:
                    raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
                buf.write(data)
                data_length = len(data)
                marker += data_length

                if length is not None and length > marker:
                    continue
                return True
        except socket.timeout:
            if raise_on_timeout:
                raise TimeoutError("Timeout reading from socket")
            return False
        except NONBLOCKING_EXCEPTIONS as ex:
            # if we're in nonblocking mode and the recv raises a
            # blocking error, simply return False indicating that
            # there's no data to be read. otherwise raise the
            # original exception.
            allowed = NONBLOCKING_EXCEPTION_ERROR_NUMBERS.get(ex.__class__, -1)
            if not raise_on_timeout and ex.errno == allowed:
                return False
            raise ConnectionError(f"Error while reading from socket: {ex.args}")
        finally:
            buf.seek(current_pos)
            if custom_timeout:
                sock.settimeout(self.socket_timeout)

    def can_read(self, timeout: float) -> bool:
        return bool(self.unread_bytes()) or self._read_from_socket(
            timeout=timeout, raise_on_timeout=False
        )

    def read(self, length: int) -> bytes:
        length = length + 2  # make sure to read the \r\n terminator
        # BufferIO will return less than requested if buffer is short
        data = self._buffer.read(length)
        missing = length - len(data)
        if missing:
            # fill up the buffer and read the remainder
            self._read_from_socket(missing)
            data += self._buffer.read(missing)
        return data[:-2]

    def readline(self) -> bytes:
        buf = self._buffer
        data = buf.readline()
        while not data.endswith(SYM_CRLF):
            # there's more data in the socket that we need
            self._read_from_socket()
            data += buf.readline()

        return data[:-2]

    def get_pos(self) -> int:
        """
        Get current read position
        """
        return self._buffer.tell()

    def rewind(self, pos: int) -> None:
        """
        Rewind the buffer to a specific position, to re-start reading
        """
        self._buffer.seek(pos)

    def purge(self) -> None:
        """
        After a successful read, purge the read part of buffer
        """
        unread = self.unread_bytes()

        # Only if we have read all of the buffer do we truncate, to
        # reduce the amount of memory thrashing.  This heuristic
        # can be changed or removed later.
        if unread > 0:
            return

        if unread > 0:
            # move unread data to the front
            view = self._buffer.getbuffer()
            view[:unread] = view[-unread:]
        self._buffer.truncate(unread)
        self._buffer.seek(0)

    def close(self) -> None:
        try:
            self._buffer.close()
        except Exception:
            # issue #633 suggests the purge/close somehow raised a
            # BadFileDescriptor error. Perhaps the client ran out of
            # memory or something else? It's probably OK to ignore
            # any error being raised from purge/close since we're
            # removing the reference to the instance below.
            pass
        self._buffer = None
        self._sock = None
