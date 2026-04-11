import asyncio
import io
import os
import pathlib
import sys
from contextlib import suppress
from enum import Enum, auto
from mimetypes import MimeTypes
from stat import S_ISREG
from types import MappingProxyType
from typing import (  # noqa
    IO,
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Final,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from . import hdrs
from .abc import AbstractStreamWriter
from .helpers import ETAG_ANY, ETag, must_be_empty_body
from .typedefs import LooseHeaders, PathLike
from .web_exceptions import (
    HTTPForbidden,
    HTTPNotFound,
    HTTPNotModified,
    HTTPPartialContent,
    HTTPPreconditionFailed,
    HTTPRequestRangeNotSatisfiable,
)
from .web_response import StreamResponse

__all__ = ("FileResponse",)

if TYPE_CHECKING:
    from .web_request import BaseRequest


_T_OnChunkSent = Optional[Callable[[bytes], Awaitable[None]]]


NOSENDFILE: Final[bool] = bool(os.environ.get("AIOHTTP_NOSENDFILE"))

CONTENT_TYPES: Final[MimeTypes] = MimeTypes()

# File extension to IANA encodings map that will be checked in the order defined.
ENCODING_EXTENSIONS = MappingProxyType(
    {ext: CONTENT_TYPES.encodings_map[ext] for ext in (".br", ".gz")}
)

FALLBACK_CONTENT_TYPE = "application/octet-stream"

# Provide additional MIME type/extension pairs to be recognized.
# https://en.wikipedia.org/wiki/List_of_archive_formats#Compression_only
ADDITIONAL_CONTENT_TYPES = MappingProxyType(
    {
        "application/gzip": ".gz",
        "application/x-brotli": ".br",
        "application/x-bzip2": ".bz2",
        "application/x-compress": ".Z",
        "application/x-xz": ".xz",
    }
)


class _FileResponseResult(Enum):
    """The result of the file response."""

    SEND_FILE = auto()  # Ie a regular file to send
    NOT_ACCEPTABLE = auto()  # Ie a socket, or non-regular file
    PRE_CONDITION_FAILED = auto()  # Ie If-Match or If-None-Match failed
    NOT_MODIFIED = auto()  # 304 Not Modified


# Add custom pairs and clear the encodings map so guess_type ignores them.
CONTENT_TYPES.encodings_map.clear()
for content_type, extension in ADDITIONAL_CONTENT_TYPES.items():
    CONTENT_TYPES.add_type(content_type, extension)


_CLOSE_FUTURES: Set[asyncio.Future[None]] = set()


class FileResponse(StreamResponse):
    """A response object can be used to send files."""

    def __init__(
        self,
        path: PathLike,
        chunk_size: int = 256 * 1024,
        status: int = 200,
        reason: Optional[str] = None,
        headers: Optional[LooseHeaders] = None,
    ) -> None:
        super().__init__(status=status, reason=reason, headers=headers)

        self._path = pathlib.Path(path)
        self._chunk_size = chunk_size

    def _seek_and_read(self, fobj: IO[Any], offset: int, chunk_size: int) -> bytes:
        fobj.seek(offset)
        return fobj.read(chunk_size)  # type: ignore[no-any-return]

    async def _sendfile_fallback(
        self, writer: AbstractStreamWriter, fobj: IO[Any], offset: int, count: int
    ) -> AbstractStreamWriter:
        # To keep memory usage low,fobj is transferred in chunks
        # controlled by the constructor's chunk_size argument.

        chunk_size = self._chunk_size
        loop = asyncio.get_event_loop()
        chunk = await loop.run_in_executor(
            None, self._seek_and_read, fobj, offset, chunk_size
        )
        while chunk:
            await writer.write(chunk)
            count = count - chunk_size
            if count <= 0:
                break
            chunk = await loop.run_in_executor(None, fobj.read, min(chunk_size, count))

        await writer.drain()
        return writer

    async def _sendfile(
        self, request: "BaseRequest", fobj: IO[Any], offset: int, count: int
    ) -> AbstractStreamWriter:
        writer = await super().prepare(request)
        assert writer is not None

        if NOSENDFILE or self.compression:
            return await self._sendfile_fallback(writer, fobj, offset, count)

        loop = request._loop
        transport = request.transport
        assert transport is not None

        try:
            await loop.sendfile(transport, fobj, offset, count)
        except NotImplementedError:
            return await self._sendfile_fallback(writer, fobj, offset, count)

        await super().write_eof()
        return writer

    @staticmethod
    def _etag_match(etag_value: str, etags: Tuple[ETag, ...], *, weak: bool) -> bool:
        if len(etags) == 1 and etags[0].value == ETAG_ANY:
            return True
        return any(
            etag.value == etag_value for etag in etags if weak or not etag.is_weak
        )

    async def _not_modified(
        self, request: "BaseRequest", etag_value: str, last_modified: float
    ) -> Optional[AbstractStreamWriter]:
        self.set_status(HTTPNotModified.status_code)
        self._length_check = False
        self.etag = etag_value
        self.last_modified = last_modified
        # Delete any Content-Length headers provided by user. HTTP 304
        # should always have empty response body
        return await super().prepare(request)

    async def _precondition_failed(
        self, request: "BaseRequest"
    ) -> Optional[AbstractStreamWriter]:
        self.set_status(HTTPPreconditionFailed.status_code)
        self.content_length = 0
        return await super().prepare(request)

    def _make_response(
        self, request: "BaseRequest", accept_encoding: str
    ) -> Tuple[
        _FileResponseResult, Optional[io.BufferedReader], os.stat_result, Optional[str]
    ]:
        """Return the response result, io object, stat result, and encoding.

        If an uncompressed file is returned, the encoding is set to
        :py:data:`None`.

        This method should be called from a thread executor
        since it calls os.stat which may block.
        """
        file_path, st, file_encoding = self._get_file_path_stat_encoding(
            accept_encoding
        )
        if not file_path:
            return _FileResponseResult.NOT_ACCEPTABLE, None, st, None

        etag_value = f"{st.st_mtime_ns:x}-{st.st_size:x}"

        # https://www.rfc-editor.org/rfc/rfc9110#section-13.1.1-2
        if (ifmatch := request.if_match) is not None and not self._etag_match(
            etag_value, ifmatch, weak=False
        ):
            return _FileResponseResult.PRE_CONDITION_FAILED, None, st, file_encoding

        if (
            (unmodsince := request.if_unmodified_since) is not None
            and ifmatch is None
            and st.st_mtime > unmodsince.timestamp()
        ):
            return _FileResponseResult.PRE_CONDITION_FAILED, None, st, file_encoding

        # https://www.rfc-editor.org/rfc/rfc9110#section-13.1.2-2
        if (ifnonematch := request.if_none_match) is not None and self._etag_match(
            etag_value, ifnonematch, weak=True
        ):
            return _FileResponseResult.NOT_MODIFIED, None, st, file_encoding

        if (
            (modsince := request.if_modified_since) is not None
            and ifnonematch is None
            and st.st_mtime <= modsince.timestamp()
        ):
            return _FileResponseResult.NOT_MODIFIED, None, st, file_encoding

        fobj = file_path.open("rb")
        with suppress(OSError):
            # fstat() may not be available on all platforms
            # Once we open the file, we want the fstat() to ensure
            # the file has not changed between the first stat()
            # and the open().
            st = os.stat(fobj.fileno())
        return _FileResponseResult.SEND_FILE, fobj, st, file_encoding

    def _get_file_path_stat_encoding(
        self, accept_encoding: str
    ) -> Tuple[Optional[pathlib.Path], os.stat_result, Optional[str]]:
        file_path = self._path
        for file_extension, file_encoding in ENCODING_EXTENSIONS.items():
            if file_encoding not in accept_encoding:
                continue

            compressed_path = file_path.with_suffix(file_path.suffix + file_extension)
            with suppress(OSError):
                # Do not follow symlinks and ignore any non-regular files.
                st = compressed_path.lstat()
                if S_ISREG(st.st_mode):
                    return compressed_path, st, file_encoding

        # Fallback to the uncompressed file
        st = file_path.stat()
        return file_path if S_ISREG(st.st_mode) else None, st, None

    async def prepare(self, request: "BaseRequest") -> Optional[AbstractStreamWriter]:
        loop = asyncio.get_running_loop()
        # Encoding comparisons should be case-insensitive
        # https://www.rfc-editor.org/rfc/rfc9110#section-8.4.1
        accept_encoding = request.headers.get(hdrs.ACCEPT_ENCODING, "").lower()
        try:
            response_result, fobj, st, file_encoding = await loop.run_in_executor(
                None, self._make_response, request, accept_encoding
            )
        except PermissionError:
            self.set_status(HTTPForbidden.status_code)
            return await super().prepare(request)
        except OSError:
            # Most likely to be FileNotFoundError or OSError for circular
            # symlinks in python >= 3.13, so respond with 404.
            self.set_status(HTTPNotFound.status_code)
            return await super().prepare(request)

        # Forbid special files like sockets, pipes, devices, etc.
        if response_result is _FileResponseResult.NOT_ACCEPTABLE:
            self.set_status(HTTPForbidden.status_code)
            return await super().prepare(request)

        if response_result is _FileResponseResult.PRE_CONDITION_FAILED:
            return await self._precondition_failed(request)

        if response_result is _FileResponseResult.NOT_MODIFIED:
            etag_value = f"{st.st_mtime_ns:x}-{st.st_size:x}"
            last_modified = st.st_mtime
            return await self._not_modified(request, etag_value, last_modified)

        assert fobj is not None
        try:
            return await self._prepare_open_file(request, fobj, st, file_encoding)
        finally:
            # We do not await here because we do not want to wait
            # for the executor to finish before returning the response
            # so the connection can begin servicing another request
            # as soon as possible.
            close_future = loop.run_in_executor(None, fobj.close)
            # Hold a strong reference to the future to prevent it from being
            # garbage collected before it completes.
            _CLOSE_FUTURES.add(close_future)
            close_future.add_done_callback(_CLOSE_FUTURES.remove)

    async def _prepare_open_file(
        self,
        request: "BaseRequest",
        fobj: io.BufferedReader,
        st: os.stat_result,
        file_encoding: Optional[str],
    ) -> Optional[AbstractStreamWriter]:
        status = self._status
        file_size: int = st.st_size
        file_mtime: float = st.st_mtime
        count: int = file_size
        start: Optional[int] = None

        if (ifrange := request.if_range) is None or file_mtime <= ifrange.timestamp():
            # If-Range header check:
            # condition = cached date >= last modification date
            # return 206 if True else 200.
            # if False:
            #   Range header would not be processed, return 200
            # if True but Range header missing
            #   return 200
            try:
                rng = request.http_range
                start = rng.start
                end: Optional[int] = rng.stop
            except ValueError:
                # https://tools.ietf.org/html/rfc7233:
                # A server generating a 416 (Range Not Satisfiable) response to
                # a byte-range request SHOULD send a Content-Range header field
                # with an unsatisfied-range value.
                # The complete-length in a 416 response indicates the current
                # length of the selected representation.
                #
                # Will do the same below. Many servers ignore this and do not
                # send a Content-Range header with HTTP 416
                self._headers[hdrs.CONTENT_RANGE] = f"bytes */{file_size}"
                self.set_status(HTTPRequestRangeNotSatisfiable.status_code)
                return await super().prepare(request)

            # If a range request has been made, convert start, end slice
            # notation into file pointer offset and count
            if start is not None:
                if start < 0 and end is None:  # return tail of file
                    start += file_size
                    if start < 0:
                        # if Range:bytes=-1000 in request header but file size
                        # is only 200, there would be trouble without this
                        start = 0
                    count = file_size - start
                else:
                    # rfc7233:If the last-byte-pos value is
                    # absent, or if the value is greater than or equal to
                    # the current length of the representation data,
                    # the byte range is interpreted as the remainder
                    # of the representation (i.e., the server replaces the
                    # value of last-byte-pos with a value that is one less than
                    # the current length of the selected representation).
                    count = (
                        min(end if end is not None else file_size, file_size) - start
                    )

                if start >= file_size:
                    # HTTP 416 should be returned in this case.
                    #
                    # According to https://tools.ietf.org/html/rfc7233:
                    # If a valid byte-range-set includes at least one
                    # byte-range-spec with a first-byte-pos that is less than
                    # the current length of the representation, or at least one
                    # suffix-byte-range-spec with a non-zero suffix-length,
                    # then the byte-range-set is satisfiable. Otherwise, the
                    # byte-range-set is unsatisfiable.
                    self._headers[hdrs.CONTENT_RANGE] = f"bytes */{file_size}"
                    self.set_status(HTTPRequestRangeNotSatisfiable.status_code)
                    return await super().prepare(request)

                status = HTTPPartialContent.status_code
                # Even though you are sending the whole file, you should still
                # return a HTTP 206 for a Range request.
                self.set_status(status)

        # If the Content-Type header is not already set, guess it based on the
        # extension of the request path. The encoding returned by guess_type
        #  can be ignored since the map was cleared above.
        if hdrs.CONTENT_TYPE not in self._headers:
            if sys.version_info >= (3, 13):
                guesser = CONTENT_TYPES.guess_file_type
            else:
                guesser = CONTENT_TYPES.guess_type
            self.content_type = guesser(self._path)[0] or FALLBACK_CONTENT_TYPE

        if file_encoding:
            self._headers[hdrs.CONTENT_ENCODING] = file_encoding
            self._headers[hdrs.VARY] = hdrs.ACCEPT_ENCODING
            # Disable compression if we are already sending
            # a compressed file since we don't want to double
            # compress.
            self._compression = False

        self.etag = f"{st.st_mtime_ns:x}-{st.st_size:x}"
        self.last_modified = file_mtime
        self.content_length = count

        self._headers[hdrs.ACCEPT_RANGES] = "bytes"

        if status == HTTPPartialContent.status_code:
            real_start = start
            assert real_start is not None
            self._headers[hdrs.CONTENT_RANGE] = "bytes {}-{}/{}".format(
                real_start, real_start + count - 1, file_size
            )

        # If we are sending 0 bytes calling sendfile() will throw a ValueError
        if count == 0 or must_be_empty_body(request.method, status):
            return await super().prepare(request)

        # be aware that start could be None or int=0 here.
        offset = start or 0

        return await self._sendfile(request, fobj, offset, count)
