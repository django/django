import sys
from abc import ABC
from asyncio import IncompleteReadError, StreamReader, TimeoutError
from typing import List, Optional, Union

if sys.version_info.major >= 3 and sys.version_info.minor >= 11:
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout

from ..exceptions import (
    AuthenticationError,
    AuthenticationWrongNumberOfArgsError,
    BusyLoadingError,
    ConnectionError,
    ExecAbortError,
    ModuleError,
    NoPermissionError,
    NoScriptError,
    OutOfMemoryError,
    ReadOnlyError,
    RedisError,
    ResponseError,
)
from ..typing import EncodableT
from .encoders import Encoder
from .socket import SERVER_CLOSED_CONNECTION_ERROR, SocketBuffer

MODULE_LOAD_ERROR = "Error loading the extension. " "Please check the server logs."
NO_SUCH_MODULE_ERROR = "Error unloading module: no such module with that name"
MODULE_UNLOAD_NOT_POSSIBLE_ERROR = "Error unloading module: operation not " "possible."
MODULE_EXPORTS_DATA_TYPES_ERROR = (
    "Error unloading module: the module "
    "exports one or more module-side data "
    "types, can't unload"
)
# user send an AUTH cmd to a server without authorization configured
NO_AUTH_SET_ERROR = {
    # Redis >= 6.0
    "AUTH <password> called without any password "
    "configured for the default user. Are you sure "
    "your configuration is correct?": AuthenticationError,
    # Redis < 6.0
    "Client sent AUTH, but no password is set": AuthenticationError,
}


class BaseParser(ABC):
    EXCEPTION_CLASSES = {
        "ERR": {
            "max number of clients reached": ConnectionError,
            "invalid password": AuthenticationError,
            # some Redis server versions report invalid command syntax
            # in lowercase
            "wrong number of arguments "
            "for 'auth' command": AuthenticationWrongNumberOfArgsError,
            # some Redis server versions report invalid command syntax
            # in uppercase
            "wrong number of arguments "
            "for 'AUTH' command": AuthenticationWrongNumberOfArgsError,
            MODULE_LOAD_ERROR: ModuleError,
            MODULE_EXPORTS_DATA_TYPES_ERROR: ModuleError,
            NO_SUCH_MODULE_ERROR: ModuleError,
            MODULE_UNLOAD_NOT_POSSIBLE_ERROR: ModuleError,
            **NO_AUTH_SET_ERROR,
        },
        "OOM": OutOfMemoryError,
        "WRONGPASS": AuthenticationError,
        "EXECABORT": ExecAbortError,
        "LOADING": BusyLoadingError,
        "NOSCRIPT": NoScriptError,
        "READONLY": ReadOnlyError,
        "NOAUTH": AuthenticationError,
        "NOPERM": NoPermissionError,
    }

    @classmethod
    def parse_error(cls, response):
        "Parse an error response"
        error_code = response.split(" ")[0]
        if error_code in cls.EXCEPTION_CLASSES:
            response = response[len(error_code) + 1 :]
            exception_class = cls.EXCEPTION_CLASSES[error_code]
            if isinstance(exception_class, dict):
                exception_class = exception_class.get(response, ResponseError)
            return exception_class(response)
        return ResponseError(response)

    def on_disconnect(self):
        raise NotImplementedError()

    def on_connect(self, connection):
        raise NotImplementedError()


class _RESPBase(BaseParser):
    """Base class for sync-based resp parsing"""

    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size
        self.encoder = None
        self._sock = None
        self._buffer = None

    def __del__(self):
        try:
            self.on_disconnect()
        except Exception:
            pass

    def on_connect(self, connection):
        "Called when the socket connects"
        self._sock = connection._sock
        self._buffer = SocketBuffer(
            self._sock, self.socket_read_size, connection.socket_timeout
        )
        self.encoder = connection.encoder

    def on_disconnect(self):
        "Called when the socket disconnects"
        self._sock = None
        if self._buffer is not None:
            self._buffer.close()
            self._buffer = None
        self.encoder = None

    def can_read(self, timeout):
        return self._buffer and self._buffer.can_read(timeout)


class AsyncBaseParser(BaseParser):
    """Base parsing class for the python-backed async parser"""

    __slots__ = "_stream", "_read_size"

    def __init__(self, socket_read_size: int):
        self._stream: Optional[StreamReader] = None
        self._read_size = socket_read_size

    async def can_read_destructive(self) -> bool:
        raise NotImplementedError()

    async def read_response(
        self, disable_decoding: bool = False
    ) -> Union[EncodableT, ResponseError, None, List[EncodableT]]:
        raise NotImplementedError()


class _AsyncRESPBase(AsyncBaseParser):
    """Base class for async resp parsing"""

    __slots__ = AsyncBaseParser.__slots__ + ("encoder", "_buffer", "_pos", "_chunks")

    def __init__(self, socket_read_size: int):
        super().__init__(socket_read_size)
        self.encoder: Optional[Encoder] = None
        self._buffer = b""
        self._chunks = []
        self._pos = 0

    def _clear(self):
        self._buffer = b""
        self._chunks.clear()

    def on_connect(self, connection):
        """Called when the stream connects"""
        self._stream = connection._reader
        if self._stream is None:
            raise RedisError("Buffer is closed.")
        self.encoder = connection.encoder
        self._clear()
        self._connected = True

    def on_disconnect(self):
        """Called when the stream disconnects"""
        self._connected = False

    async def can_read_destructive(self) -> bool:
        if not self._connected:
            raise RedisError("Buffer is closed.")
        if self._buffer:
            return True
        try:
            async with async_timeout(0):
                return await self._stream.read(1)
        except TimeoutError:
            return False

    async def _read(self, length: int) -> bytes:
        """
        Read `length` bytes of data.  These are assumed to be followed
        by a '\r\n' terminator which is subsequently discarded.
        """
        want = length + 2
        end = self._pos + want
        if len(self._buffer) >= end:
            result = self._buffer[self._pos : end - 2]
        else:
            tail = self._buffer[self._pos :]
            try:
                data = await self._stream.readexactly(want - len(tail))
            except IncompleteReadError as error:
                raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR) from error
            result = (tail + data)[:-2]
            self._chunks.append(data)
        self._pos += want
        return result

    async def _readline(self) -> bytes:
        """
        read an unknown number of bytes up to the next '\r\n'
        line separator, which is discarded.
        """
        found = self._buffer.find(b"\r\n", self._pos)
        if found >= 0:
            result = self._buffer[self._pos : found]
        else:
            tail = self._buffer[self._pos :]
            data = await self._stream.readline()
            if not data.endswith(b"\r\n"):
                raise ConnectionError(SERVER_CLOSED_CONNECTION_ERROR)
            result = (tail + data)[:-2]
            self._chunks.append(data)
        self._pos += len(result) + 2
        return result
