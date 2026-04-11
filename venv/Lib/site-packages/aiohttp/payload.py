import asyncio
import enum
import io
import json
import mimetypes
import os
import sys
import warnings
from abc import ABC, abstractmethod
from collections.abc import Iterable
from itertools import chain
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Dict,
    Final,
    List,
    Optional,
    Set,
    TextIO,
    Tuple,
    Type,
    Union,
)

from multidict import CIMultiDict

from . import hdrs
from .abc import AbstractStreamWriter
from .helpers import (
    _SENTINEL,
    content_disposition_header,
    guess_filename,
    parse_mimetype,
    sentinel,
)
from .streams import StreamReader
from .typedefs import JSONEncoder, _CIMultiDict

__all__ = (
    "PAYLOAD_REGISTRY",
    "get_payload",
    "payload_type",
    "Payload",
    "BytesPayload",
    "StringPayload",
    "IOBasePayload",
    "BytesIOPayload",
    "BufferedReaderPayload",
    "TextIOPayload",
    "StringIOPayload",
    "JsonPayload",
    "AsyncIterablePayload",
)

TOO_LARGE_BYTES_BODY: Final[int] = 2**20  # 1 MB
READ_SIZE: Final[int] = 2**16  # 64 KB
_CLOSE_FUTURES: Set[asyncio.Future[None]] = set()


class LookupError(Exception):
    """Raised when no payload factory is found for the given data type."""


class Order(str, enum.Enum):
    normal = "normal"
    try_first = "try_first"
    try_last = "try_last"


def get_payload(data: Any, *args: Any, **kwargs: Any) -> "Payload":
    return PAYLOAD_REGISTRY.get(data, *args, **kwargs)


def register_payload(
    factory: Type["Payload"], type: Any, *, order: Order = Order.normal
) -> None:
    PAYLOAD_REGISTRY.register(factory, type, order=order)


class payload_type:
    def __init__(self, type: Any, *, order: Order = Order.normal) -> None:
        self.type = type
        self.order = order

    def __call__(self, factory: Type["Payload"]) -> Type["Payload"]:
        register_payload(factory, self.type, order=self.order)
        return factory


PayloadType = Type["Payload"]
_PayloadRegistryItem = Tuple[PayloadType, Any]


class PayloadRegistry:
    """Payload registry.

    note: we need zope.interface for more efficient adapter search
    """

    __slots__ = ("_first", "_normal", "_last", "_normal_lookup")

    def __init__(self) -> None:
        self._first: List[_PayloadRegistryItem] = []
        self._normal: List[_PayloadRegistryItem] = []
        self._last: List[_PayloadRegistryItem] = []
        self._normal_lookup: Dict[Any, PayloadType] = {}

    def get(
        self,
        data: Any,
        *args: Any,
        _CHAIN: "Type[chain[_PayloadRegistryItem]]" = chain,
        **kwargs: Any,
    ) -> "Payload":
        if self._first:
            for factory, type_ in self._first:
                if isinstance(data, type_):
                    return factory(data, *args, **kwargs)
        # Try the fast lookup first
        if lookup_factory := self._normal_lookup.get(type(data)):
            return lookup_factory(data, *args, **kwargs)
        # Bail early if its already a Payload
        if isinstance(data, Payload):
            return data
        # Fallback to the slower linear search
        for factory, type_ in _CHAIN(self._normal, self._last):
            if isinstance(data, type_):
                return factory(data, *args, **kwargs)
        raise LookupError()

    def register(
        self, factory: PayloadType, type: Any, *, order: Order = Order.normal
    ) -> None:
        if order is Order.try_first:
            self._first.append((factory, type))
        elif order is Order.normal:
            self._normal.append((factory, type))
            if isinstance(type, Iterable):
                for t in type:
                    self._normal_lookup[t] = factory
            else:
                self._normal_lookup[type] = factory
        elif order is Order.try_last:
            self._last.append((factory, type))
        else:
            raise ValueError(f"Unsupported order {order!r}")


class Payload(ABC):

    _default_content_type: str = "application/octet-stream"
    _size: Optional[int] = None
    _consumed: bool = False  # Default: payload has not been consumed yet
    _autoclose: bool = False  # Default: assume resource needs explicit closing

    def __init__(
        self,
        value: Any,
        headers: Optional[
            Union[_CIMultiDict, Dict[str, str], Iterable[Tuple[str, str]]]
        ] = None,
        content_type: Union[str, None, _SENTINEL] = sentinel,
        filename: Optional[str] = None,
        encoding: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self._encoding = encoding
        self._filename = filename
        self._headers: _CIMultiDict = CIMultiDict()
        self._value = value
        if content_type is not sentinel and content_type is not None:
            self._headers[hdrs.CONTENT_TYPE] = content_type
        elif self._filename is not None:
            if sys.version_info >= (3, 13):
                guesser = mimetypes.guess_file_type
            else:
                guesser = mimetypes.guess_type
            content_type = guesser(self._filename)[0]
            if content_type is None:
                content_type = self._default_content_type
            self._headers[hdrs.CONTENT_TYPE] = content_type
        else:
            self._headers[hdrs.CONTENT_TYPE] = self._default_content_type
        if headers:
            self._headers.update(headers)

    @property
    def size(self) -> Optional[int]:
        """Size of the payload in bytes.

        Returns the number of bytes that will be transmitted when the payload
        is written. For string payloads, this is the size after encoding to bytes,
        not the length of the string.
        """
        return self._size

    @property
    def filename(self) -> Optional[str]:
        """Filename of the payload."""
        return self._filename

    @property
    def headers(self) -> _CIMultiDict:
        """Custom item headers"""
        return self._headers

    @property
    def _binary_headers(self) -> bytes:
        return (
            "".join([k + ": " + v + "\r\n" for k, v in self.headers.items()]).encode(
                "utf-8"
            )
            + b"\r\n"
        )

    @property
    def encoding(self) -> Optional[str]:
        """Payload encoding"""
        return self._encoding

    @property
    def content_type(self) -> str:
        """Content type"""
        return self._headers[hdrs.CONTENT_TYPE]

    @property
    def consumed(self) -> bool:
        """Whether the payload has been consumed and cannot be reused."""
        return self._consumed

    @property
    def autoclose(self) -> bool:
        """
        Whether the payload can close itself automatically.

        Returns True if the payload has no file handles or resources that need
        explicit closing. If False, callers must await close() to release resources.
        """
        return self._autoclose

    def set_content_disposition(
        self,
        disptype: str,
        quote_fields: bool = True,
        _charset: str = "utf-8",
        **params: Any,
    ) -> None:
        """Sets ``Content-Disposition`` header."""
        self._headers[hdrs.CONTENT_DISPOSITION] = content_disposition_header(
            disptype, quote_fields=quote_fields, _charset=_charset, **params
        )

    @abstractmethod
    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Return string representation of the value.

        This is named decode() to allow compatibility with bytes objects.
        """

    @abstractmethod
    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This is a legacy method that writes the entire payload without length constraints.

        Important:
            For new implementations, use write_with_length() instead of this method.
            This method is maintained for backwards compatibility and will eventually
            delegate to write_with_length(writer, None) in all implementations.

        All payload subclasses must override this method for backwards compatibility,
        but new code should use write_with_length for more flexibility and control.

        """

    # write_with_length is new in aiohttp 3.12
    # it should be overridden by subclasses
    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This method allows writing payload content with a specific length constraint,
        which is particularly useful for HTTP responses with Content-Length header.

        Note:
            This is the base implementation that provides backwards compatibility
            for subclasses that don't override this method. Specific payload types
            should override this method to implement proper length-constrained writing.

        """
        # Backwards compatibility for subclasses that don't override this method
        # and for the default implementation
        await self.write(writer)

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This is a convenience method that calls decode() and encodes the result
        to bytes using the specified encoding.
        """
        # Use instance encoding if available, otherwise use parameter
        actual_encoding = self._encoding or encoding
        return self.decode(actual_encoding, errors).encode(actual_encoding)

    def _close(self) -> None:
        """
        Async safe synchronous close operations for backwards compatibility.

        This method exists only for backwards compatibility with code that
        needs to clean up payloads synchronously. In the future, we will
        drop this method and only support the async close() method.

        WARNING: This method must be safe to call from within the event loop
        without blocking. Subclasses should not perform any blocking I/O here.

        WARNING: This method must be called from within an event loop for
        certain payload types (e.g., IOBasePayload). Calling it outside an
        event loop may raise RuntimeError.
        """
        # This is a no-op by default, but subclasses can override it
        # for non-blocking cleanup operations.

    async def close(self) -> None:
        """
        Close the payload if it holds any resources.

        IMPORTANT: This method must not await anything that might not finish
        immediately, as it may be called during cleanup/cancellation. Schedule
        any long-running operations without awaiting them.

        In the future, this will be the only close method supported.
        """
        self._close()


class BytesPayload(Payload):
    _value: bytes
    # _consumed = False (inherited) - Bytes are immutable and can be reused
    _autoclose = True  # No file handle, just bytes in memory

    def __init__(
        self, value: Union[bytes, bytearray, memoryview], *args: Any, **kwargs: Any
    ) -> None:
        if "content_type" not in kwargs:
            kwargs["content_type"] = "application/octet-stream"

        super().__init__(value, *args, **kwargs)

        if isinstance(value, memoryview):
            self._size = value.nbytes
        elif isinstance(value, (bytes, bytearray)):
            self._size = len(value)
        else:
            raise TypeError(f"value argument must be byte-ish, not {type(value)!r}")

        if self._size > TOO_LARGE_BYTES_BODY:
            kwargs = {"source": self}
            warnings.warn(
                "Sending a large body directly with raw bytes might"
                " lock the event loop. You should probably pass an "
                "io.BytesIO object instead",
                ResourceWarning,
                **kwargs,
            )

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        return self._value.decode(encoding, errors)

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method returns the raw bytes content of the payload.
        It is equivalent to accessing the _value attribute directly.
        """
        return self._value

    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write the entire bytes payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This method writes the entire bytes content without any length constraint.

        Note:
            For new implementations that need length control, use write_with_length().
            This method is maintained for backwards compatibility and is equivalent
            to write_with_length(writer, None).

        """
        await writer.write(self._value)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write bytes payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This method writes either the entire byte sequence or a slice of it
        up to the specified content_length. For BytesPayload, this operation
        is performed efficiently using array slicing.

        """
        if content_length is not None:
            await writer.write(self._value[:content_length])
        else:
            await writer.write(self._value)


class StringPayload(BytesPayload):
    def __init__(
        self,
        value: str,
        *args: Any,
        encoding: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:

        if encoding is None:
            if content_type is None:
                real_encoding = "utf-8"
                content_type = "text/plain; charset=utf-8"
            else:
                mimetype = parse_mimetype(content_type)
                real_encoding = mimetype.parameters.get("charset", "utf-8")
        else:
            if content_type is None:
                content_type = "text/plain; charset=%s" % encoding
            real_encoding = encoding

        super().__init__(
            value.encode(real_encoding),
            encoding=real_encoding,
            content_type=content_type,
            *args,
            **kwargs,
        )


class StringIOPayload(StringPayload):
    def __init__(self, value: IO[str], *args: Any, **kwargs: Any) -> None:
        super().__init__(value.read(), *args, **kwargs)


class IOBasePayload(Payload):
    _value: io.IOBase
    # _consumed = False (inherited) - File can be re-read from the same position
    _start_position: Optional[int] = None
    # _autoclose = False (inherited) - Has file handle that needs explicit closing

    def __init__(
        self, value: IO[Any], disposition: str = "attachment", *args: Any, **kwargs: Any
    ) -> None:
        if "filename" not in kwargs:
            kwargs["filename"] = guess_filename(value)

        super().__init__(value, *args, **kwargs)

        if self._filename is not None and disposition is not None:
            if hdrs.CONTENT_DISPOSITION not in self.headers:
                self.set_content_disposition(disposition, filename=self._filename)

    def _set_or_restore_start_position(self) -> None:
        """Set or restore the start position of the file-like object."""
        if self._start_position is None:
            try:
                self._start_position = self._value.tell()
            except (OSError, AttributeError):
                self._consumed = True  # Cannot seek, mark as consumed
            return
        try:
            self._value.seek(self._start_position)
        except (OSError, AttributeError):
            # Failed to seek back - mark as consumed since we've already read
            self._consumed = True

    def _read_and_available_len(
        self, remaining_content_len: Optional[int]
    ) -> Tuple[Optional[int], bytes]:
        """
        Read the file-like object and return both its total size and the first chunk.

        Args:
            remaining_content_len: Optional limit on how many bytes to read in this operation.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A tuple containing:
            - The total size of the remaining unread content (None if size cannot be determined)
            - The first chunk of bytes read from the file object

        This method is optimized to perform both size calculation and initial read
        in a single operation, which is executed in a single executor job to minimize
        context switches and file operations when streaming content.

        """
        self._set_or_restore_start_position()
        size = self.size  # Call size only once since it does I/O
        return size, self._value.read(
            min(READ_SIZE, size or READ_SIZE, remaining_content_len or READ_SIZE)
        )

    def _read(self, remaining_content_len: Optional[int]) -> bytes:
        """
        Read a chunk of data from the file-like object.

        Args:
            remaining_content_len: Optional maximum number of bytes to read.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A chunk of bytes read from the file object, respecting the
            remaining_content_len limit if specified.

        This method is used for subsequent reads during streaming after
        the initial _read_and_available_len call has been made.

        """
        return self._value.read(remaining_content_len or READ_SIZE)  # type: ignore[no-any-return]

    @property
    def size(self) -> Optional[int]:
        """
        Size of the payload in bytes.

        Returns the total size of the payload content from the initial position.
        This ensures consistent Content-Length for requests, including 307/308 redirects
        where the same payload instance is reused.

        Returns None if the size cannot be determined (e.g., for unseekable streams).
        """
        try:
            # Store the start position on first access.
            # This is critical when the same payload instance is reused (e.g., 307/308
            # redirects). Without storing the initial position, after the payload is
            # read once, the file position would be at EOF, which would cause the
            # size calculation to return 0 (file_size - EOF position).
            # By storing the start position, we ensure the size calculation always
            # returns the correct total size for any subsequent use.
            if self._start_position is None:
                self._start_position = self._value.tell()

            # Return the total size from the start position
            # This ensures Content-Length is correct even after reading
            return os.fstat(self._value.fileno()).st_size - self._start_position
        except (AttributeError, OSError):
            return None

    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write the entire file-like payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This method writes the entire file content without any length constraint.
        It delegates to write_with_length() with no length limit for implementation
        consistency.

        Note:
            For new implementations that need length control, use write_with_length() directly.
            This method is maintained for backwards compatibility with existing code.

        """
        await self.write_with_length(writer, None)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write file-like payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This method implements optimized streaming of file content with length constraints:

        1. File reading is performed in a thread pool to avoid blocking the event loop
        2. Content is read and written in chunks to maintain memory efficiency
        3. Writing stops when either:
           - All available file content has been written (when size is known)
           - The specified content_length has been reached
        4. File resources are properly closed even if the operation is cancelled

        The implementation carefully handles both known-size and unknown-size payloads,
        as well as constrained and unconstrained content lengths.

        """
        loop = asyncio.get_running_loop()
        total_written_len = 0
        remaining_content_len = content_length

        # Get initial data and available length
        available_len, chunk = await loop.run_in_executor(
            None, self._read_and_available_len, remaining_content_len
        )
        # Process data chunks until done
        while chunk:
            chunk_len = len(chunk)

            # Write data with or without length constraint
            if remaining_content_len is None:
                await writer.write(chunk)
            else:
                await writer.write(chunk[:remaining_content_len])
                remaining_content_len -= chunk_len

            total_written_len += chunk_len

            # Check if we're done writing
            if self._should_stop_writing(
                available_len, total_written_len, remaining_content_len
            ):
                return

            # Read next chunk
            chunk = await loop.run_in_executor(
                None,
                self._read,
                (
                    min(READ_SIZE, remaining_content_len)
                    if remaining_content_len is not None
                    else READ_SIZE
                ),
            )

    def _should_stop_writing(
        self,
        available_len: Optional[int],
        total_written_len: int,
        remaining_content_len: Optional[int],
    ) -> bool:
        """
        Determine if we should stop writing data.

        Args:
            available_len: Known size of the payload if available (None if unknown)
            total_written_len: Number of bytes already written
            remaining_content_len: Remaining bytes to be written for content-length limited responses

        Returns:
            True if we should stop writing data, based on either:
            - Having written all available data (when size is known)
            - Having written all requested content (when content-length is specified)

        """
        return (available_len is not None and total_written_len >= available_len) or (
            remaining_content_len is not None and remaining_content_len <= 0
        )

    def _close(self) -> None:
        """
        Async safe synchronous close operations for backwards compatibility.

        This method exists only for backwards
        compatibility. Use the async close() method instead.

        WARNING: This method MUST be called from within an event loop.
        Calling it outside an event loop will raise RuntimeError.
        """
        # Skip if already consumed
        if self._consumed:
            return
        self._consumed = True  # Mark as consumed to prevent further writes
        # Schedule file closing without awaiting to prevent cancellation issues
        loop = asyncio.get_running_loop()
        close_future = loop.run_in_executor(None, self._value.close)
        # Hold a strong reference to the future to prevent it from being
        # garbage collected before it completes.
        _CLOSE_FUTURES.add(close_future)
        close_future.add_done_callback(_CLOSE_FUTURES.remove)

    async def close(self) -> None:
        """
        Close the payload if it holds any resources.

        IMPORTANT: This method must not await anything that might not finish
        immediately, as it may be called during cleanup/cancellation. Schedule
        any long-running operations without awaiting them.
        """
        self._close()

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Return string representation of the value.

        WARNING: This method does blocking I/O and should not be called in the event loop.
        """
        return self._read_all().decode(encoding, errors)

    def _read_all(self) -> bytes:
        """Read the entire file-like object and return its content as bytes."""
        self._set_or_restore_start_position()
        # Use readlines() to ensure we get all content
        return b"".join(self._value.readlines())

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire file content and returns it as bytes.
        It is equivalent to reading the file-like object directly.
        The file reading is performed in an executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._read_all)


class TextIOPayload(IOBasePayload):
    _value: io.TextIOBase
    # _autoclose = False (inherited) - Has text file handle that needs explicit closing

    def __init__(
        self,
        value: TextIO,
        *args: Any,
        encoding: Optional[str] = None,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:

        if encoding is None:
            if content_type is None:
                encoding = "utf-8"
                content_type = "text/plain; charset=utf-8"
            else:
                mimetype = parse_mimetype(content_type)
                encoding = mimetype.parameters.get("charset", "utf-8")
        else:
            if content_type is None:
                content_type = "text/plain; charset=%s" % encoding

        super().__init__(
            value,
            content_type=content_type,
            encoding=encoding,
            *args,
            **kwargs,
        )

    def _read_and_available_len(
        self, remaining_content_len: Optional[int]
    ) -> Tuple[Optional[int], bytes]:
        """
        Read the text file-like object and return both its total size and the first chunk.

        Args:
            remaining_content_len: Optional limit on how many bytes to read in this operation.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A tuple containing:
            - The total size of the remaining unread content (None if size cannot be determined)
            - The first chunk of bytes read from the file object, encoded using the payload's encoding

        This method is optimized to perform both size calculation and initial read
        in a single operation, which is executed in a single executor job to minimize
        context switches and file operations when streaming content.

        Note:
            TextIOPayload handles encoding of the text content before writing it
            to the stream. If no encoding is specified, UTF-8 is used as the default.

        """
        self._set_or_restore_start_position()
        size = self.size
        chunk = self._value.read(
            min(READ_SIZE, size or READ_SIZE, remaining_content_len or READ_SIZE)
        )
        return size, chunk.encode(self._encoding) if self._encoding else chunk.encode()

    def _read(self, remaining_content_len: Optional[int]) -> bytes:
        """
        Read a chunk of data from the text file-like object.

        Args:
            remaining_content_len: Optional maximum number of bytes to read.
                If None, READ_SIZE will be used as the default chunk size.

        Returns:
            A chunk of bytes read from the file object and encoded using the payload's
            encoding. The data is automatically converted from text to bytes.

        This method is used for subsequent reads during streaming after
        the initial _read_and_available_len call has been made. It properly
        handles text encoding, converting the text content to bytes using
        the specified encoding (or UTF-8 if none was provided).

        """
        chunk = self._value.read(remaining_content_len or READ_SIZE)
        return chunk.encode(self._encoding) if self._encoding else chunk.encode()

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """
        Return string representation of the value.

        WARNING: This method does blocking I/O and should not be called in the event loop.
        """
        self._set_or_restore_start_position()
        return self._value.read()

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire text file content and returns it as bytes.
        It encodes the text content using the specified encoding.
        The file reading is performed in an executor to avoid blocking the event loop.
        """
        loop = asyncio.get_running_loop()

        # Use instance encoding if available, otherwise use parameter
        actual_encoding = self._encoding or encoding

        def _read_and_encode() -> bytes:
            self._set_or_restore_start_position()
            # TextIO read() always returns the full content
            return self._value.read().encode(actual_encoding, errors)

        return await loop.run_in_executor(None, _read_and_encode)


class BytesIOPayload(IOBasePayload):
    _value: io.BytesIO
    _size: int  # Always initialized in __init__
    _autoclose = True  # BytesIO is in-memory, safe to auto-close

    def __init__(self, value: io.BytesIO, *args: Any, **kwargs: Any) -> None:
        super().__init__(value, *args, **kwargs)
        # Calculate size once during initialization
        self._size = len(self._value.getbuffer()) - self._value.tell()

    @property
    def size(self) -> int:
        """Size of the payload in bytes.

        Returns the number of bytes in the BytesIO buffer that will be transmitted.
        This is calculated once during initialization for efficiency.
        """
        return self._size

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        self._set_or_restore_start_position()
        return self._value.read().decode(encoding, errors)

    async def write(self, writer: AbstractStreamWriter) -> None:
        return await self.write_with_length(writer, None)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write BytesIO payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This implementation is specifically optimized for BytesIO objects:

        1. Reads content in chunks to maintain memory efficiency
        2. Yields control back to the event loop periodically to prevent blocking
           when dealing with large BytesIO objects
        3. Respects content_length constraints when specified
        4. Properly cleans up by closing the BytesIO object when done or on error

        The periodic yielding to the event loop is important for maintaining
        responsiveness when processing large in-memory buffers.

        """
        self._set_or_restore_start_position()
        loop_count = 0
        remaining_bytes = content_length
        while chunk := self._value.read(READ_SIZE):
            if loop_count > 0:
                # Avoid blocking the event loop
                # if they pass a large BytesIO object
                # and we are not in the first iteration
                # of the loop
                await asyncio.sleep(0)
            if remaining_bytes is None:
                await writer.write(chunk)
            else:
                await writer.write(chunk[:remaining_bytes])
                remaining_bytes -= len(chunk)
                if remaining_bytes <= 0:
                    return
            loop_count += 1

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire BytesIO content and returns it as bytes.
        It is equivalent to accessing the _value attribute directly.
        """
        self._set_or_restore_start_position()
        return self._value.read()

    async def close(self) -> None:
        """
        Close the BytesIO payload.

        This does nothing since BytesIO is in-memory and does not require explicit closing.
        """


class BufferedReaderPayload(IOBasePayload):
    _value: io.BufferedIOBase
    # _autoclose = False (inherited) - Has buffered file handle that needs explicit closing

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        self._set_or_restore_start_position()
        return self._value.read().decode(encoding, errors)


class JsonPayload(BytesPayload):
    def __init__(
        self,
        value: Any,
        encoding: str = "utf-8",
        content_type: str = "application/json",
        dumps: JSONEncoder = json.dumps,
        *args: Any,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            dumps(value).encode(encoding),
            content_type=content_type,
            encoding=encoding,
            *args,
            **kwargs,
        )


if TYPE_CHECKING:
    from typing import AsyncIterable, AsyncIterator

    _AsyncIterator = AsyncIterator[bytes]
    _AsyncIterable = AsyncIterable[bytes]
else:
    from collections.abc import AsyncIterable, AsyncIterator

    _AsyncIterator = AsyncIterator
    _AsyncIterable = AsyncIterable


class AsyncIterablePayload(Payload):

    _iter: Optional[_AsyncIterator] = None
    _value: _AsyncIterable
    _cached_chunks: Optional[List[bytes]] = None
    # _consumed stays False to allow reuse with cached content
    _autoclose = True  # Iterator doesn't need explicit closing

    def __init__(self, value: _AsyncIterable, *args: Any, **kwargs: Any) -> None:
        if not isinstance(value, AsyncIterable):
            raise TypeError(
                "value argument must support "
                "collections.abc.AsyncIterable interface, "
                "got {!r}".format(type(value))
            )

        if "content_type" not in kwargs:
            kwargs["content_type"] = "application/octet-stream"

        super().__init__(value, *args, **kwargs)

        self._iter = value.__aiter__()

    async def write(self, writer: AbstractStreamWriter) -> None:
        """
        Write the entire async iterable payload to the writer stream.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing

        This method iterates through the async iterable and writes each chunk
        to the writer without any length constraint.

        Note:
            For new implementations that need length control, use write_with_length() directly.
            This method is maintained for backwards compatibility with existing code.

        """
        await self.write_with_length(writer, None)

    async def write_with_length(
        self, writer: AbstractStreamWriter, content_length: Optional[int]
    ) -> None:
        """
        Write async iterable payload with a specific content length constraint.

        Args:
            writer: An AbstractStreamWriter instance that handles the actual writing
            content_length: Maximum number of bytes to write (None for unlimited)

        This implementation handles streaming of async iterable content with length constraints:

        1. If cached chunks are available, writes from them
        2. Otherwise iterates through the async iterable one chunk at a time
        3. Respects content_length constraints when specified
        4. Does NOT generate cache - that's done by as_bytes()

        """
        # If we have cached chunks, use them
        if self._cached_chunks is not None:
            remaining_bytes = content_length
            for chunk in self._cached_chunks:
                if remaining_bytes is None:
                    await writer.write(chunk)
                elif remaining_bytes > 0:
                    await writer.write(chunk[:remaining_bytes])
                    remaining_bytes -= len(chunk)
                else:
                    break
            return

        # If iterator is exhausted and we don't have cached chunks, nothing to write
        if self._iter is None:
            return

        # Stream from the iterator
        remaining_bytes = content_length

        try:
            while True:
                if sys.version_info >= (3, 10):
                    chunk = await anext(self._iter)
                else:
                    chunk = await self._iter.__anext__()
                if remaining_bytes is None:
                    await writer.write(chunk)
                # If we have a content length limit
                elif remaining_bytes > 0:
                    await writer.write(chunk[:remaining_bytes])
                    remaining_bytes -= len(chunk)
                # We still want to exhaust the iterator even
                # if we have reached the content length limit
                # since the file handle may not get closed by
                # the iterator if we don't do this
        except StopAsyncIteration:
            # Iterator is exhausted
            self._iter = None
            self._consumed = True  # Mark as consumed when streamed without caching

    def decode(self, encoding: str = "utf-8", errors: str = "strict") -> str:
        """Decode the payload content as a string if cached chunks are available."""
        if self._cached_chunks is not None:
            return b"".join(self._cached_chunks).decode(encoding, errors)
        raise TypeError("Unable to decode - content not cached. Call as_bytes() first.")

    async def as_bytes(self, encoding: str = "utf-8", errors: str = "strict") -> bytes:
        """
        Return bytes representation of the value.

        This method reads the entire async iterable content and returns it as bytes.
        It generates and caches the chunks for future reuse.
        """
        # If we have cached chunks, return them joined
        if self._cached_chunks is not None:
            return b"".join(self._cached_chunks)

        # If iterator is exhausted and no cache, return empty
        if self._iter is None:
            return b""

        # Read all chunks and cache them
        chunks: List[bytes] = []
        async for chunk in self._iter:
            chunks.append(chunk)

        # Iterator is exhausted, cache the chunks
        self._iter = None
        self._cached_chunks = chunks
        # Keep _consumed as False to allow reuse with cached chunks

        return b"".join(chunks)


class StreamReaderPayload(AsyncIterablePayload):
    def __init__(self, value: StreamReader, *args: Any, **kwargs: Any) -> None:
        super().__init__(value.iter_any(), *args, **kwargs)


PAYLOAD_REGISTRY = PayloadRegistry()
PAYLOAD_REGISTRY.register(BytesPayload, (bytes, bytearray, memoryview))
PAYLOAD_REGISTRY.register(StringPayload, str)
PAYLOAD_REGISTRY.register(StringIOPayload, io.StringIO)
PAYLOAD_REGISTRY.register(TextIOPayload, io.TextIOBase)
PAYLOAD_REGISTRY.register(BytesIOPayload, io.BytesIO)
PAYLOAD_REGISTRY.register(BufferedReaderPayload, (io.BufferedReader, io.BufferedRandom))
PAYLOAD_REGISTRY.register(IOBasePayload, io.IOBase)
PAYLOAD_REGISTRY.register(StreamReaderPayload, StreamReader)
# try_last for giving a chance to more specialized async interables like
# multipart.BodyPartReaderPayload override the default
PAYLOAD_REGISTRY.register(AsyncIterablePayload, AsyncIterable, order=Order.try_last)
