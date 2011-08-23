"""
Multi-part parsing for file uploads.

Exposes one class, ``MultiPartParser``, which feeds chunks of uploaded data to
file upload handlers for processing.
"""

import cgi
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_unicode
from django.utils.text import unescape_entities
from django.core.files.uploadhandler import StopUpload, SkipFile, StopFutureHandlers

__all__ = ('MultiPartParser', 'MultiPartParserError', 'InputStreamExhausted')

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

class MultiPartParser(object):
    """
    A rfc2388 multipart/form-data parser.

    ``MultiValueDict.parse()`` reads the input stream in ``chunk_size`` chunks
    and returns a tuple of ``(MultiValueDict(POST), MultiValueDict(FILES))``. If
    """
    def __init__(self, META, input_data, upload_handlers, encoding=None):
        """
        Initialize the MultiPartParser object.

        :META:
            The standard ``META`` dictionary in Django request objects.
        :input_data:
            The raw post data, as a file-like object.
        :upload_handler:
            An UploadHandler instance that performs operations on the uploaded
            data.
        :encoding:
            The encoding with which to treat the incoming data.
        """

        #
        # Content-Type should containt multipart and the boundary information.
        #

        content_type = META.get('HTTP_CONTENT_TYPE', META.get('CONTENT_TYPE', ''))
        if not content_type.startswith('multipart/'):
            raise MultiPartParserError('Invalid Content-Type: %s' % content_type)

        # Parse the header to get the boundary to split the parts.
        ctypes, opts = parse_header(content_type)
        boundary = opts.get('boundary')
        if not boundary or not cgi.valid_boundary(boundary):
            raise MultiPartParserError('Invalid boundary in multipart: %s' % boundary)


        #
        # Content-Length should contain the length of the body we are about
        # to receive.
        #
        try:
            content_length = int(META.get('HTTP_CONTENT_LENGTH', META.get('CONTENT_LENGTH',0)))
        except (ValueError, TypeError):
            # For now set it to 0; we'll try again later on down.
            content_length = 0

        if content_length < 0:
            # This means we shouldn't continue...raise an error.
            raise MultiPartParserError("Invalid content length: %r" % content_length)

        self._boundary = boundary
        self._input_data = input_data

        # For compatibility with low-level network APIs (with 32-bit integers),
        # the chunk size should be < 2^31, but still divisible by 4.
        possible_sizes = [x.chunk_size for x in upload_handlers if x.chunk_size]
        self._chunk_size = min([2**31-4] + possible_sizes)

        self._meta = META
        self._encoding = encoding or settings.DEFAULT_CHARSET
        self._content_length = content_length
        self._upload_handlers = upload_handlers

    def parse(self):
        """
        Parse the POST data and break it into a FILES MultiValueDict and a POST
        MultiValueDict.

        Returns a tuple containing the POST and FILES dictionary, respectively.
        """
        # We have to import QueryDict down here to avoid a circular import.
        from django.http import QueryDict

        encoding = self._encoding
        handlers = self._upload_handlers

        # HTTP spec says that Content-Length >= 0 is valid
        # handling content-length == 0 before continuing
        if self._content_length == 0:
            return QueryDict(MultiValueDict(), encoding=self._encoding), MultiValueDict()

        limited_input_data = LimitBytes(self._input_data, self._content_length)

        # See if the handler will want to take care of the parsing.
        # This allows overriding everything if somebody wants it.
        for handler in handlers:
            result = handler.handle_raw_input(limited_input_data,
                                              self._meta,
                                              self._content_length,
                                              self._boundary,
                                              encoding)
            if result is not None:
                return result[0], result[1]

        # Create the data structures to be used later.
        self._post = QueryDict('', mutable=True)
        self._files = MultiValueDict()

        # Instantiate the parser and stream:
        stream = LazyStream(ChunkIter(limited_input_data, self._chunk_size))

        # Whether or not to signal a file-completion at the beginning of the loop.
        old_field_name = None
        counters = [0] * len(handlers)

        try:
            for item_type, meta_data, field_stream in Parser(stream, self._boundary):
                if old_field_name:
                    # We run this at the beginning of the next loop
                    # since we cannot be sure a file is complete until
                    # we hit the next boundary/part of the multipart content.
                    self.handle_file_complete(old_field_name, counters)
                    old_field_name = None

                try:
                    disposition = meta_data['content-disposition'][1]
                    field_name = disposition['name'].strip()
                except (KeyError, IndexError, AttributeError):
                    continue

                transfer_encoding = meta_data.get('content-transfer-encoding')
                field_name = force_unicode(field_name, encoding, errors='replace')

                if item_type == FIELD:
                    # This is a post field, we can just set it in the post
                    if transfer_encoding == 'base64':
                        raw_data = field_stream.read()
                        try:
                            data = str(raw_data).decode('base64')
                        except:
                            data = raw_data
                    else:
                        data = field_stream.read()

                    self._post.appendlist(field_name,
                                          force_unicode(data, encoding, errors='replace'))
                elif item_type == FILE:
                    # This is a file, use the handler...
                    file_name = disposition.get('filename')
                    if not file_name:
                        continue
                    file_name = force_unicode(file_name, encoding, errors='replace')
                    file_name = self.IE_sanitize(unescape_entities(file_name))

                    content_type = meta_data.get('content-type', ('',))[0].strip()
                    try:
                        charset = meta_data.get('content-type', (0,{}))[1].get('charset', None)
                    except:
                        charset = None

                    try:
                        content_length = int(meta_data.get('content-length')[0])
                    except (IndexError, TypeError, ValueError):
                        content_length = None

                    counters = [0] * len(handlers)
                    try:
                        for handler in handlers:
                            try:
                                handler.new_file(field_name, file_name,
                                                 content_type, content_length,
                                                 charset)
                            except StopFutureHandlers:
                                break

                        for chunk in field_stream:
                            if transfer_encoding == 'base64':
                                # We only special-case base64 transfer encoding
                                try:
                                    chunk = str(chunk).decode('base64')
                                except Exception, e:
                                    # Since this is only a chunk, any error is an unfixable error.
                                    raise MultiPartParserError("Could not decode base64 data: %r" % e)

                            for i, handler in enumerate(handlers):
                                chunk_length = len(chunk)
                                chunk = handler.receive_data_chunk(chunk,
                                                                   counters[i])
                                counters[i] += chunk_length
                                if chunk is None:
                                    # If the chunk received by the handler is None, then don't continue.
                                    break

                    except SkipFile, e:
                        # Just use up the rest of this file...
                        exhaust(field_stream)
                    else:
                        # Handle file upload completions on next iteration.
                        old_field_name = field_name
                else:
                    # If this is neither a FIELD or a FILE, just exhaust the stream.
                    exhaust(stream)
        except StopUpload, e:
            if not e.connection_reset:
                exhaust(limited_input_data)
        else:
            # Make sure that the request data is all fed
            exhaust(limited_input_data)

        # Signal that the upload has completed.
        for handler in handlers:
            retval = handler.upload_complete()
            if retval:
                break

        return self._post, self._files

    def handle_file_complete(self, old_field_name, counters):
        """
        Handle all the signalling that takes place when a file is complete.
        """
        for i, handler in enumerate(self._upload_handlers):
            file_obj = handler.file_complete(counters[i])
            if file_obj:
                # If it returns a file object, then set the files dict.
                self._files.appendlist(force_unicode(old_field_name,
                                                     self._encoding,
                                                     errors='replace'),
                                       file_obj)
                break

    def IE_sanitize(self, filename):
        """Cleanup filename from Internet Explorer full paths."""
        return filename and filename[filename.rfind("\\")+1:].strip()

class LazyStream(object):
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
        self._leftover = ''
        self.length = length
        self.position = 0
        self._remaining = length
        self._unget_history = []

    def tell(self):
        return self.position

    def read(self, size=None):
        def parts():
            remaining = (size is not None and [size] or [self._remaining])[0]
            # do the whole thing in one shot if no limit was provided.
            if remaining is None:
                yield ''.join(self)
                return

            # otherwise do some bookkeeping to return exactly enough
            # of the stream and stashing any extra content we get from
            # the producer
            while remaining != 0:
                assert remaining > 0, 'remaining bytes to read should never go negative'

                chunk = self.next()

                emitting = chunk[:remaining]
                self.unget(chunk[remaining:])
                remaining -= len(emitting)
                yield emitting

        out = ''.join(parts())
        return out

    def next(self):
        """
        Used when the exact number of bytes to read is unimportant.

        This procedure just returns whatever is chunk is conveniently returned
        from the iterator instead. Useful to avoid unnecessary bookkeeping if
        performance is an issue.
        """
        if self._leftover:
            output = self._leftover
            self._leftover = ''
        else:
            output = self._producer.next()
            self._unget_history = []
        self.position += len(output)
        return output

    def close(self):
        """
        Used to invalidate/disable this lazy stream.

        Replaces the producer with an empty list. Any leftover bytes that have
        already been read will still be reported upon read() and/or next().
        """
        self._producer = []

    def __iter__(self):
        return self

    def unget(self, bytes):
        """
        Places bytes back onto the front of the lazy stream.

        Future calls to read() will return those bytes first. The
        stream position and thus tell() will be rewound.
        """
        if not bytes:
            return
        self._update_unget_history(len(bytes))
        self.position -= len(bytes)
        self._leftover = ''.join([bytes, self._leftover])

    def _update_unget_history(self, num_bytes):
        """
        Updates the unget history as a sanity check to see if we've pushed
        back the same number of bytes in one chunk. If we keep ungetting the
        same number of bytes many times (here, 50), we're mostly likely in an
        infinite loop of some sort. This is usually caused by a
        maliciously-malformed MIME request.
        """
        self._unget_history = [num_bytes] + self._unget_history[:49]
        number_equal = len([current_number for current_number in self._unget_history
                            if current_number == num_bytes])

        if number_equal > 40:
            raise SuspiciousOperation(
                "The multipart parser got stuck, which shouldn't happen with"
                " normal uploaded files. Check for malicious upload activity;"
                " if there is none, report this to the Django developers."
            )

class ChunkIter(object):
    """
    An iterable that will yield chunks of data. Given a file-like object as the
    constructor, this object will yield chunks of read operations from that
    object.
    """
    def __init__(self, flo, chunk_size=64 * 1024):
        self.flo = flo
        self.chunk_size = chunk_size

    def next(self):
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

class LimitBytes(object):
    """ Limit bytes for a file object. """
    def __init__(self, fileobject, length):
        self._file = fileobject
        self.remaining = length

    def read(self, num_bytes=None):
        """
        Read data from the underlying file.
        If you ask for too much or there isn't anything left,
        this will raise an InputStreamExhausted error.
        """
        if self.remaining <= 0:
            raise InputStreamExhausted()
        if num_bytes is None:
            num_bytes = self.remaining
        else:
            num_bytes = min(num_bytes, self.remaining)
        self.remaining -= num_bytes
        return self._file.read(num_bytes)

class InterBoundaryIter(object):
    """
    A Producer that will iterate over boundaries.
    """
    def __init__(self, stream, boundary):
        self._stream = stream
        self._boundary = boundary

    def __iter__(self):
        return self

    def next(self):
        try:
            return LazyStream(BoundaryIter(self._stream, self._boundary))
        except InputStreamExhausted:
            raise StopIteration()

class BoundaryIter(object):
    """
    A Producer that is sensitive to boundaries.

    Will happily yield bytes until a boundary is found. Will yield the bytes
    before the boundary, throw away the boundary bytes themselves, and push the
    post-boundary bytes back on the stream.

    The future calls to .next() after locating the boundary will raise a
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
        try:
            from mx.TextTools import FS
            self._fs = FS(boundary).find
        except ImportError:
            self._fs = lambda data: data.find(boundary)

    def __iter__(self):
        return self

    def next(self):
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

        chunk = ''.join(chunks)
        boundary = self._find_boundary(chunk, len(chunk) < self._rollback)

        if boundary:
            end, next = boundary
            stream.unget(chunk[next:])
            self._done = True
            return chunk[:end]
        else:
            # make sure we dont treat a partial boundary (and
            # its separators) as data
            if not chunk[:-rollback]:# and len(chunk) >= (len(self._boundary) + 6):
                # There's nothing left, we should just return and mark as done.
                self._done = True
                return chunk
            else:
                stream.unget(chunk[-rollback:])
                return chunk[:-rollback]

    def _find_boundary(self, data, eof = False):
        """
        Finds a multipart boundary in data.

        Should no boundry exist in the data None is returned instead. Otherwise
        a tuple containing the indices of the following are returned:

         * the end of current encapsulation
         * the start of the next encapsulation
        """
        index = self._fs(data)
        if index < 0:
            return None
        else:
            end = index
            next = index + len(self._boundary)
            # backup over CRLF
            if data[max(0,end-1)] == '\n':
                end -= 1
            if data[max(0,end-1)] == '\r':
                end -= 1
            return end, next

def exhaust(stream_or_iterable):
    """
    Completely exhausts an iterator or stream.

    Raise a MultiPartParserError if the argument is not a stream or an iterable.
    """
    iterator = None
    try:
        iterator = iter(stream_or_iterable)
    except TypeError:
        iterator = ChunkIter(stream_or_iterable, 16384)

    if iterator is None:
        raise MultiPartParserError('multipartparser.exhaust() was passed a non-iterable or stream parameter')

    for __ in iterator:
        pass

def parse_boundary_stream(stream, max_header_size):
    """
    Parses one and exactly one stream that encapsulates a boundary.
    """
    # Stream at beginning of header, look for end of header
    # and parse it if found. The header must fit within one
    # chunk.
    chunk = stream.read(max_header_size)

    # 'find' returns the top of these four bytes, so we'll
    # need to munch them later to prevent them from polluting
    # the payload.
    header_end = chunk.find('\r\n\r\n')

    def _parse_header(line):
        main_value_pair, params = parse_header(line)
        try:
            name, value = main_value_pair.split(':', 1)
        except:
            raise ValueError("Invalid header: %r" % line)
        return name, (value, params)

    if header_end == -1:
        # we find no header, so we just mark this fact and pass on
        # the stream verbatim
        stream.unget(chunk)
        return (RAW, {}, stream)

    header = chunk[:header_end]

    # here we place any excess chunk back onto the stream, as
    # well as throwing away the CRLFCRLF bytes from above.
    stream.unget(chunk[header_end + 4:])

    TYPE = RAW
    outdict = {}

    # Eliminate blank lines
    for line in header.split('\r\n'):
        # This terminology ("main value" and "dictionary of
        # parameters") is from the Python docs.
        try:
            name, (value, params) = _parse_header(line)
        except:
            continue

        if name == 'content-disposition':
            TYPE = FIELD
            if params.get('filename'):
                TYPE = FILE

        outdict[name] = value, params

    if TYPE == RAW:
        stream.unget(chunk)

    return (TYPE, outdict, stream)

class Parser(object):
    def __init__(self, stream, boundary):
        self._stream = stream
        self._separator = '--' + boundary

    def __iter__(self):
        boundarystream = InterBoundaryIter(self._stream, self._separator)
        for sub_stream in boundarystream:
            # Iterate over each part
            yield parse_boundary_stream(sub_stream, 1024)

def parse_header(line):
    """ Parse the header into a key-value. """
    plist = _parse_header_params(';' + line)
    key = plist.pop(0).lower()
    pdict = {}
    for p in plist:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i+1:].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict

def _parse_header_params(s):
    plist = []
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and s.count('"', 0, end) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        plist.append(f.strip())
        s = s[end:]
    return plist
