from __future__ import unicode_literals

from io import BytesIO

from django.core.servers.basehttp import ServerHandler, MAX_SOCKET_CHUNK_SIZE
from django.utils.unittest import TestCase


class DummyHandler(object):
    def log_request(self, *args, **kwargs):
        pass


class FileWrapperHandler(ServerHandler):
    def __init__(self, *args, **kwargs):
        super(FileWrapperHandler, self).__init__(*args, **kwargs)
        self.request_handler = DummyHandler()
        self._used_sendfile = False

    def sendfile(self):
        self._used_sendfile = True
        return True


def wsgi_app(environ, start_response):
    start_response(str('200 OK'), [(str('Content-Type'), str('text/plain'))])
    return [b'Hello World!']


def wsgi_app_file_wrapper(environ, start_response):
    start_response(str('200 OK'), [(str('Content-Type'), str('text/plain'))])
    return environ['wsgi.file_wrapper'](BytesIO(b'foo'))


class WSGIFileWrapperTests(TestCase):
    """
    Test that the wsgi.file_wrapper works for the builting server.

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
        super(WriteChunkCounterHandler, self).__init__(*args, **kwargs)
        self.request_handler = DummyHandler()
        self.headers_written = False
        self.write_chunk_counter = 0

    def send_headers(self):
        super(WriteChunkCounterHandler, self).send_headers()
        self.headers_written = True

    def _write(self, data):
        if self.headers_written:
            self.write_chunk_counter += 1
        self.stdout.write(data)


def send_big_data_app(environ, start_response):
    start_response(str('200 OK'), [(str('Content-Type'), str('text/plain'))])
    # Return a blob of data that is 1.5 times the maximum chunk size.
    return [b'x' * (MAX_SOCKET_CHUNK_SIZE + MAX_SOCKET_CHUNK_SIZE // 2)]


class ServerHandlerChunksProperly(TestCase):
    """
    Test that the ServerHandler chunks data properly.

    Tests for #18972: The logic that performs the math to break data into
    32MB (MAX_SOCKET_CHUNK_SIZE) chunks was flawed, BUT it didn't actually
    cause any problems.
    """

    def test_chunked_data(self):
        env = {'SERVER_PROTOCOL': 'HTTP/1.0'}
        handler = WriteChunkCounterHandler(None, BytesIO(), BytesIO(), env)
        handler.run(send_big_data_app)
        self.assertEqual(handler.write_chunk_counter, 2)
