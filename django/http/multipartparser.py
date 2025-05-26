"""
Multi-part parsing for file uploads.

Exposes one class, ``MultiPartParser``, which feeds chunks of uploaded data to
file upload handlers for processing.
"""

import base64
import binascii
import collections
import html

from django.conf import settings
from django.core.exceptions import (
    RequestDataTooBig,
    SuspiciousMultipartForm,
    TooManyFieldsSent,
    TooManyFilesSent,
)
from django.core.files.uploadhandler import SkipFile, StopFutureHandlers, StopUpload
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str
from django.utils.http import parse_header_parameters
from django.utils.regex_helper import _lazy_re_compile

__all__ = ("MultiPartParser", "MultiPartParserError", "InputStreamExhausted")


class MultiPartParserError(Exception):
    pass


class InputStreamExhausted(Exception):
    """
    No more reads are allowed from this device.
    """

    pass


RAW = "raw"
FILE = "file"
FIELD = "field"
FIELD_TYPES = frozenset([FIELD, RAW])
MAX_TOTAL_HEADER_SIZE = 1024


class MultiPartParser:
    """
    An RFC 7578 multipart/form-data parser.

    ``MultiValueDict.parse()`` reads the input stream in ``chunk_size`` chunks
    and returns a tuple of ``(MultiValueDict(POST), MultiValueDict(FILES))``.
    """

    boundary_re = _lazy_re_compile(r"[ -~]{0,200}[!-~]")

    def __init__(self, META, input_data, upload_handlers, encoding=None):
        """
        Initialize the MultiPartParser object.

        :META:
            The standard ``META`` dictionary in Django request objects.
        :input_data:
            The raw post data, as a file-like object.
        :upload_handlers:
            A list of UploadHandler instances that perform operations on the
            uploaded data.
        :encoding:
            The encoding with which to treat the incoming data.
        """
        # Content-Type should contain multipart and the boundary information.
        content_type = META.get("CONTENT_TYPE", "")
        if not content_type.startswith("multipart/"):
            raise MultiPartParserError("Invalid Content-Type: %s" % content_type)

        try:
            content_type.encode("ascii")
        except UnicodeEncodeError:
            raise MultiPartParserError(
                "Invalid non-ASCII Content-Type in multipart: %s"
                % force_str(content_type)
            )

        # Parse the header to get the boundary to split the parts.
        _, opts = parse_header_parameters(content_type)
        boundary = opts.get("boundary")
        if not boundary or not self.boundary_re.fullmatch(boundary):
            raise MultiPartParserError(
                "Invalid boundary in multipart: %s" % force_str(boundary)
            )

        # Content-Length should contain the length of the body we are about
        # to receive.
        try:
            content_length = int(META.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0

        if content_length < 0:
            # This means we shouldn't continue...raise an error.
            raise MultiPartParserError("Invalid content length: %r" % content_length)

        self._boundary = boundary.encode("ascii")
        self._input_data = input_data

        # For compatibility with low-level network APIs (with 32-bit integers),
        # the chunk size should be < 2^31, but still divisible by 4.
        possible_sizes = [x.chunk_size for x in upload_handlers if x.chunk_size]
        self._chunk_size = min([2**31 - 4, *possible_sizes])

        self._meta = META
        self._encoding = encoding or settings.DEFAULT_CHARSET
        self._content_length = content_length
        self._upload_handlers = upload_handlers

    def parse(self):
        # Call the actual parse routine and close all open files in case of
        # errors. This is needed because if exceptions are thrown the
        # MultiPartParser will not be garbage collected immediately and
        # resources would be kept alive. This is only needed for errors because
        # the Request object closes all uploaded files at the end of the
        # request.
        try:
            return self._parse()
        except Exception:
            if hasattr(self, "_files"):
                for _, files in self._files.lists():
                    for fileobj in files:
                        fileobj.close()
            raise

    def _parse(self):
        """
        Parse the POST data and break it into a FILES MultiValueDict and a POST
        MultiValueDict.

        Return a tuple containing the POST and FILES dictionary, respectively.
        """
        from django.http import QueryDict

        encoding = self._encoding
        handlers = self._upload_handlers

        # HTTP spec says that Content-Length >= 0 is valid
        # handling content-length == 0 before continuing
        if self._content_length == 0:
            return QueryDict(encoding=self._encoding), MultiValueDict()

        # See if any of the handlers take care of the parsing.
        # This allows overriding everything if need be.
        for handler in handlers:
            result = handler.handle_raw_input(
                self._input_data,
                self._meta,
                self._content_length,
                self._boundary,
                encoding,
            )
            # Check to see if it was handled
            if result is not None:
                return result[0], result[1]

        # Create the data structures to be used later.
        self._post = QueryDict(mutable=True)
        self._files = MultiValueDict()

        # Instantiate the parser and stream:
        stream = LazyStream(ChunkIter(self._input_data, self._chunk_size))

        # Whether or not to signal a file-completion at the beginning of the loop.
        old_field_name = None
        counters = [0] * len(handlers)

        # Number of bytes that have been read.
        num_bytes_read = 0
        # To count the number of keys in the request.
        num_post_keys = 0
        # To count the number of files in the request.
        num_files = 0
        # To limit the amount of data read from the request.
        read_size = None
        # Whether a file upload is finished.
        uploaded_file = True

        try:
            for item_type, meta_data, field_stream in Parser(stream, self._boundary):
                if old_field_name:
                    # We run this at the beginning of the next loop
                    # since we cannot be sure a file is complete until
                    # we hit the next boundary/part of the multipart content.
                    self.handle_file_complete(old_field_name, counters)
                    old_field_name = None
                    uploaded_file = True

                if (
                    item_type in FIELD_TYPES
                    and settings.DATA_UPLOAD_MAX_NUMBER_FIELDS is not None
                ):
                    # Avoid storing more than DATA_UPLOAD_MAX_NUMBER_FIELDS.
                    num_post_keys += 1
                    # 2 accounts for empty raw fields before and after the
                    # last boundary.
                    if settings.DATA_UPLOAD_MAX_NUMBER_FIELDS + 2 < num_post_keys:
                        raise TooManyFieldsSent(
                            "The number of GET/POST parameters exceeded "
                            "settings.DATA_UPLOAD_MAX_NUMBER_FIELDS."
                        )

                try:
                    disposition = meta_data["content-disposition"][1]
                    field_name = disposition["name"].strip()
                except (KeyError, IndexError, AttributeError):
                    continue

                transfer_encoding = meta_data.get("content-transfer-encoding")
                if transfer_encoding is not None:
                    transfer_encoding = transfer_encoding[0].strip()
                field_name = force_str(field_name, encoding, errors="replace")

                if item_type == FIELD:
                    # Avoid reading more than DATA_UPLOAD_MAX_MEMORY_SIZE.
                    if settings.DATA_UPLOAD_MAX_MEMORY_SIZE is not None:
                        read_size = (
                            settings.DATA_UPLOAD_MAX_MEMORY_SIZE - num_bytes_read
                        )

                    # This is a post field, we can just set it in the post
                    if transfer_encoding == "base64":
                        raw_data = field_stream.read(size=read_size)
                        num_bytes_read += len(raw_data)
                        try:
                            data = base64.b64decode(raw_data)
                        except binascii.Error:
                            data = raw_data
                    else:
                        data = field_stream.read(size=read_size)
                        num_bytes_read += len(data)

                    # Add two here to make the check consistent with the
                    # x-www-form-urlencoded check that includes '&='.
                    num_bytes_read += len(field_name) + 2
                    if (
                        settings.DATA_UPLOAD_MAX_MEMORY_SIZE is not None
                        and num_bytes_read > settings.DATA_UPLOAD_MAX_MEMORY_SIZE
                    ):
                        raise RequestDataTooBig(
                            "Request body exceeded "
                            "settings.DATA_UPLOAD_MAX_MEMORY_SIZE."
                        )

                    self._post.appendlist(
                        field_name, force_str(data, encoding, errors="replace")
                    )
                elif item_type == FILE:
                    # Avoid storing more than DATA_UPLOAD_MAX_NUMBER_FILES.
                    num_files += 1
                    if (
                        settings.DATA_UPLOAD_MAX_NUMBER_FILES is not None
                        and num_files > settings.DATA_UPLOAD_MAX_NUMBER_FILES
                    ):
                        raise TooManyFilesSent(
                            "The number of files exceeded "
                            "settings.DATA_UPLOAD_MAX_NUMBER_FILES."
                        )
                    # This is a file, use the handler...
                    file_name = disposition.get("filename")
                    if file_name:
                        file_name = force_str(file_name, encoding, errors="replace")
                        file_name = self.sanitize_file_name(file_name)
                    if not file_name:
                        continue

                    content_type, content_type_extra = meta_data.get(
                        "content-type", ("", {})
                    )
                    content_type = content_type.strip()
                    charset = content_type_extra.get("charset")

                    try:
                        content_length = int(meta_data.get("content-length")[0])
                    except (IndexError, TypeError, ValueError):
                        content_length = None

                    counters = [0] * len(handlers)
                    uploaded_file = False
                    try:
                        for handler in handlers:
                            try:
                                handler.new_file(
                                    field_name,
                                    file_name,
                                    content_type,
                                    content_length,
                                    charset,
                                    content_type_extra,
                                )
                            except StopFutureHandlers:
                                break

                        for chunk in field_stream:
                            if transfer_encoding == "base64":
                                # We only special-case base64 transfer encoding
                                # We should always decode base64 chunks by
                                # multiple of 4, ignoring whitespace.

                                stripped_chunk = b"".join(chunk.split())

                                remaining = len(stripped_chunk) % 4
                                while remaining != 0:
                                    over_chunk = field_stream.read(4 - remaining)
                                    if not over_chunk:
                                        break
                                    stripped_chunk += b"".join(over_chunk.split())
                                    remaining = len(stripped_chunk) % 4

                                try:
                                    chunk = base64.b64decode(stripped_chunk)
                                except Exception as exc:
                                    # Since this is only a chunk, any error is
                                    # an unfixable error.
                                    raise MultiPartParserError(
                                        "Could not decode base64 data."
                                    ) from exc

                            for i, handler in enumerate(handlers):
                                chunk_length = len(chunk)
                                chunk = handler.receive_data_chunk(chunk, counters[i])
                                counters[i] += chunk_length
                                if chunk is None:
                                    # Don't continue if the chunk received by
                                    # the handler is None.
                                    break

                    except SkipFile:
                        self._close_files()
                        # Just use up the rest of this file...
                        exhaust(field_stream)
                    else:
                        # Handle file upload completions on next iteration.
                        old_field_name = field_name
                else:
                    # If this is neither a FIELD nor a FILE, exhaust the field
                    # stream. Note: There could be an error here at some point,
                    # but there will be at least two RAW types (before and
                    # after the other boundaries). This branch is usually not
                    # reached at all, because a missing content-disposition
                    # header will skip the whole boundary.
                    exhaust(field_stream)
        except StopUpload as e:
            self._close_files()
            if not e.connection_reset:
                exhaust(self._input_data)
        else:
            if not uploaded_file:
                for handler in handlers:
                    handler.upload_interrupted()
            # Make sure that the request data is all fed
            exhaust(self._input_data)

        # Signal that the upload has completed.
        # any() shortcircuits if a handler's upload_complete() returns a value.
        any(handler.upload_complete() for handler in handlers)
        self._post._mutable = False
        return self._post, self._files

    def handle_file_complete(self, old_field_name, counters):
        """
        Handle all the signaling that takes place when a file is complete.
        """
        for i, handler in enumerate(self._upload_handlers):
            file_obj = handler.file_complete(counters[i])
            if file_obj:
                # If it returns a file object, then set the files dict.
                self._files.appendlist(
                    force_str(old_field_name, self._encoding, errors="replace"),
                    file_obj,
                )
                break

    def sanitize_file_name(self, file_name):
        """
        Sanitize the filename of an upload.

        Remove all possible path separators, even though that might remove more
        than actually required by the target system. Filenames that could
        potentially cause problems (current/parent dir) are also discarded.

        It should be noted that this function could still return a "filepath"
        like "C:some_file.txt" which is handled later on by the storage layer.
        So while this function does sanitize filenames to some extent, the
        resulting filename should still be considered as untrusted user input.
        """
        file_name = html.unescape(file_name)
        file_name = file_name.rsplit("/")[-1]
        file_name = file_name.rsplit("\\")[-1]
        # Remove non-printable characters.
        file_name = "".join([char for char in file_name if char.isprintable()])

        if file_name in {"", ".", ".."}:
            return None
        return file_name

    IE_sanitize = sanitize_file_name

    def _close_files(self):
        # Free up all file handles.
        # FIXME: this currently assumes that upload handlers store the file as 'file'
        # We should document that...
        # (Maybe add handler.free_file to complement new_file)
        for handler in self._upload_handlers:
            if hasattr(handler, "file"):
                handler.file.close()


class LazyStream:
    """
    The LazyStream wrapper allows one to get and "unget" bytes from a stream.

    Given a producer object (an iterator that yields bytestrings), the
    LazyStream object will support iteration, reading, and keeping a "look-back"
    variable in case you need to "unget" some bytes.
    """

    def __init__(self, producer, length=None):
        """
        Every LazyStream must have a producer when instantiated.

        A producer is an iterable that returns a string each time it
        is called.
        """
        self._producer = producer
        self._empty = False
        self._leftover = b""
        self.length = length
        self.position = 0
        self._remaining = length
        self._unget_history = []

    def tell(self):
        return self.position

    def read(self, size=None):
        def parts():
            remaining = self._remaining if size is None else size
            # do the whole thing in one shot if no limit was provided.
            if remaining is None:
                yield b"".join(self)
                return

            # otherwise do some bookkeeping to return exactly enough
            # of the stream and stashing any extra content we get from
            # the producer
            while remaining != 0:
                assert remaining > 0, "remaining bytes to read should never go negative"

                try:
                    chunk = next(self)
                except StopIteration:
                    return
                else:
                    emitting = chunk[:remaining]
                    self.unget(chunk[remaining:])
                    remaining -= len(emitting)
                    yield emitting

        return b"".join(parts())

    def __next__(self):
        """
        Used when the exact number of bytes to read is unimportant.

        Return whatever chunk is conveniently returned from the iterator.
        Useful to avoid unnecessary bookkeeping if performance is an issue.
        """
        if self._leftover:
            output = self._leftover
            self._leftover = b""
        else:
            output = next(self._producer)
            self._unget_history = []
        self.position += len(output)
        return output

    def close(self):
        """
        Used to invalidate/disable this lazy stream.

        Replace the producer with an empty list. Any leftover bytes that have
        already been read will still be reported upon read() and/or next().
        """
        self._producer = []

    def __iter__(self):
        return self

    def unget(self, bytes):
        """
        Place bytes back onto the front of the lazy stream.

        Future calls to read() will return those bytes first. The
        stream position and thus tell() will be rewound.
        """
        if not bytes:
            return
        self._update_unget_history(len(bytes))
        self.position -= len(bytes)
        self._leftover = bytes + self._leftover

    def _update_unget_history(self, num_bytes):
        """
        Update the unget history as a sanity check to see if we've pushed
        back the same number of bytes in one chunk. If we keep ungetting the
        same number of bytes many times (here, 50), we're mostly likely in an
        infinite loop of some sort. This is usually caused by a
        maliciously-malformed MIME request.
        """
        self._unget_history = [num_bytes] + self._unget_history[:49]
        number_equal = len(
            [
                current_number
                for current_number in self._unget_history
                if current_number == num_bytes
            ]
        )

        if number_equal > 40:
            raise SuspiciousMultipartForm(
                "The multipart parser got stuck, which shouldn't happen with"
                " normal uploaded files. Check for malicious upload activity;"
                " if there is none, report this to the Django developers."
            )


class ChunkIter:
    """
    An iterable that will yield chunks of data. Given a file-like object as the
    constructor, yield chunks of read operations from that object.
    """

    def __init__(self, flo, chunk_size=64 * 1024):
        self.flo = flo
        self.chunk_size = chunk_size

    def __next__(self):
        try:
            data = self.flo.read(self.chunk_size)
        except InputStreamExhausted:
            raise StopIteration()
        if data:
            return data
        else:
            raise StopIteration()

    def __iter__(self):
        return self


class InterBoundaryIter:
    """
    A Producer that will iterate over boundaries.
    """

    def __init__(self, stream, boundary):
        self._stream = stream
        self._boundary = boundary

    def __iter__(self):
        return self

    def __next__(self):
        try:
            return LazyStream(BoundaryIter(self._stream, self._boundary))
        except InputStreamExhausted:
            raise StopIteration()


class BoundaryIter:
    """
    A Producer that is sensitive to boundaries.

    Will happily yield bytes until a boundary is found. Will yield the bytes
    before the boundary, throw away the boundary bytes themselves, and push the
    post-boundary bytes back on the stream.

    The future calls to next() after locating the boundary will raise a
    StopIteration exception.
    """

    def __init__(self, stream, boundary):
        self._stream = stream
        self._boundary = boundary
        self._done = False
        # rollback an additional six bytes because the format is like
        # this: CRLF<boundary>[--CRLF]
        self._rollback = len(boundary) + 6

        # Try to use mx fast string search if available. Otherwise
        # use Python find. Wrap the latter for consistency.
        unused_char = self._stream.read(1)
        if not unused_char:
            raise InputStreamExhausted()
        self._stream.unget(unused_char)

    def __iter__(self):
        return self

    def __next__(self):
        if self._done:
            raise StopIteration()

        stream = self._stream
        rollback = self._rollback

        bytes_read = 0
        chunks = []
        for bytes in stream:
            bytes_read += len(bytes)
            chunks.append(bytes)
            if bytes_read > rollback:
                break
            if not bytes:
                break
        else:
            self._done = True

        if not chunks:
            raise StopIteration()

        chunk = b"".join(chunks)
        boundary = self._find_boundary(chunk)

        if boundary:
            end, next = boundary
            stream.unget(chunk[next:])
            self._done = True
            return chunk[:end]
        else:
            # make sure we don't treat a partial boundary (and
            # its separators) as data
            if not chunk[:-rollback]:  # and len(chunk) >= (len(self._boundary) + 6):
                # There's nothing left, we should just return and mark as done.
                self._done = True
                return chunk
            else:
                stream.unget(chunk[-rollback:])
                return chunk[:-rollback]

    def _find_boundary(self, data):
        """
        Find a multipart boundary in data.

        Should no boundary exist in the data, return None. Otherwise, return
        a tuple containing the indices of the following:
         * the end of current encapsulation
         * the start of the next encapsulation
        """
        index = data.find(self._boundary)
        if index < 0:
            return None
        else:
            end = index
            next = index + len(self._boundary)
            # backup over CRLF
            last = max(0, end - 1)
            if data[last : last + 1] == b"\n":
                end -= 1
            last = max(0, end - 1)
            if data[last : last + 1] == b"\r":
                end -= 1
            return end, next


def exhaust(stream_or_iterable):
    """Exhaust an iterator or stream."""
    try:
        iterator = iter(stream_or_iterable)
    except TypeError:
        iterator = ChunkIter(stream_or_iterable, 16384)
    collections.deque(iterator, maxlen=0)  # consume iterator quickly.


def parse_boundary_stream(stream, max_header_size):
    """
    Parse one and exactly one stream that encapsulates a boundary.
    """

    # Look for the end of headers and if not found extend the search to double
    # the size up to the MAX_TOTAL_HEADER_SIZE.
    headers_chunk_size = 1024
    while True:
        if headers_chunk_size > max_header_size:
            raise MultiPartParserError("Request max total header size exceeded.")

        # Stream at beginning of header, look for end of header and parse it if
        # found. The header must fit within one chunk.
        chunk = stream.read(headers_chunk_size)
        # 'find' returns the top of these four bytes, so munch them later to
        # prevent them from polluting the payload.
        header_end = chunk.find(b"\r\n\r\n")
        if header_end != -1:
            break

        # Find no header, mark this fact and pass on the stream verbatim.
        stream.unget(chunk)
        # No more data to read.
        if len(chunk) < headers_chunk_size:
            return (RAW, {}, stream)
        # Double the chunk size.
        headers_chunk_size *= 2

    header = chunk[:header_end]

    # here we place any excess chunk back onto the stream, as
    # well as throwing away the CRLFCRLF bytes from above.
    stream.unget(chunk[header_end + 4 :])

    TYPE = RAW
    outdict = {}

    # Eliminate blank lines
    for line in header.split(b"\r\n"):
        # This terminology ("main value" and "dictionary of
        # parameters") is from the Python docs.
        try:
            main_value_pair, params = parse_header_parameters(line.decode())
            name, value = main_value_pair.split(":", 1)
            params = {k: v.encode() for k, v in params.items()}
        except ValueError:  # Invalid header.
            continue

        if name == "content-disposition":
            TYPE = FIELD
            if params.get("filename"):
                TYPE = FILE

        outdict[name] = value, params

    if TYPE == RAW:
        stream.unget(chunk)

    return (TYPE, outdict, stream)


class Parser:
    def __init__(self, stream, boundary):
        self._stream = stream
        self._separator = b"--" + boundary

    def __iter__(self):
        boundarystream = InterBoundaryIter(self._stream, self._separator)
        for sub_stream in boundarystream:
            # Iterate over each part
            yield parse_boundary_stream(sub_stream, MAX_TOTAL_HEADER_SIZE)
