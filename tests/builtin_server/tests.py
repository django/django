import sys
import traceback
from io import BytesIO
from unittest import TestCase
from wsgiref import simple_server

# If data is too large, socket will choke, so write chunks no larger than 32MB
# at a time. The rationale behind the 32MB can be found in #5596#comment:4.
MAX_SOCKET_CHUNK_SIZE = 32 * 1024 * 1024  # 32 MB


class ServerHandler(simple_server.ServerHandler):
    error_status = "500 INTERNAL SERVER ERROR"

    def write(self, data):
        """'write()' callable as specified by PEP 3333"""

        assert isinstance(data, bytes), "write() argument must be bytestring"

        if not self.status:
            raise AssertionError("write() before start_response()")

        elif not self.headers_sent:
            # Before the first output, send the stored headers
            self.bytes_sent = len(data)    # make sure we know content-length
            self.send_headers()
        else:
            self.bytes_sent += len(data)

        # XXX check Content-Length and truncate if too many bytes written?
        data = BytesIO(data)
        for chunk in iter(lambda: data.read(MAX_SOCKET_CHUNK_SIZE), b''):
            self._write(chunk)
            self._flush()

    def error_output(self, environ, start_response):
        super().error_output(environ, start_response)
        return ['\n'.join(traceback.format_exception(*sys.exc_info()))]


class DummyHandler:
    def log_request(self, *args, **kwargs):
        pass


class FileWrapperHandler(ServerHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_handler = DummyHandler()
        self._used_sendfile = False

    def sendfile(self):
        self._used_sendfile = True
        return True


def wsgi_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello World!']


def wsgi_app_file_wrapper(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return environ['wsgi.file_wrapper'](BytesIO(b'foo'))


class WSGIFileWrapperTests(TestCase):
    """
    The wsgi.file_wrapper works for the builtin server.

    Tests for #9659: wsgi.file_wrapper in the builtin server.
    We need to mock a couple of handlers and keep track of what
    gets called when using a couple kinds of WSGI apps.
    """

    def test_file_wrapper_uses_sendfile(self):
        env = {'SERVER_PROTOCOL': 'HTTP/1.0'}
        handler = FileWrapperHandler(None, BytesIO(), BytesIO(), env)
        handler.run(wsgi_app_file_wrapper)
        self.assertTrue(handler._used_sendfile)
        self.assertEqual(handler.stdout.getvalue(), b'')
        self.assertEqual(handler.stderr.getvalue(), b'')

    def test_file_wrapper_no_sendfile(self):
        env = {'SERVER_PROTOCOL': 'HTTP/1.0'}
        handler = FileWrapperHandler(None, BytesIO(), BytesIO(), env)
        handler.run(wsgi_app)
        self.assertFalse(handler._used_sendfile)
        self.assertEqual(handler.stdout.getvalue().splitlines()[-1], b'Hello World!')
        self.assertEqual(handler.stderr.getvalue(), b'')


class WriteChunkCounterHandler(ServerHandler):
    """
    Server handler that counts the number of chunks written after headers were
    sent. Used to make sure large response body chunking works properly.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_handler = DummyHandler()
        self.headers_written = False
        self.write_chunk_counter = 0

    def send_headers(self):
        super().send_headers()
        self.headers_written = True

    def _write(self, data):
        if self.headers_written:
            self.write_chunk_counter += 1
        self.stdout.write(data)


def send_big_data_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    # Return a blob of data that is 1.5 times the maximum chunk size.
    return [b'x' * (MAX_SOCKET_CHUNK_SIZE + MAX_SOCKET_CHUNK_SIZE // 2)]


class ServerHandlerChunksProperly(TestCase):
    """
    The ServerHandler chunks data properly.

    Tests for #18972: The logic that performs the math to break data into
    32MB (MAX_SOCKET_CHUNK_SIZE) chunks was flawed, BUT it didn't actually
    cause any problems.
    """

    def test_chunked_data(self):
        env = {'SERVER_PROTOCOL': 'HTTP/1.0'}
        handler = WriteChunkCounterHandler(None, BytesIO(), BytesIO(), env)
        handler.run(send_big_data_app)
        self.assertEqual(handler.write_chunk_counter, 2)
