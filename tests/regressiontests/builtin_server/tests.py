from __future__ import unicode_literals

from io import BytesIO

from django.core.servers.basehttp import ServerHandler
from django.utils.unittest import TestCase

#
# Tests for #9659: wsgi.file_wrapper in the builtin server.
# We need to mock a couple of handlers and keep track of what
# gets called when using a couple kinds of WSGI apps.
#

class DummyHandler(object):
    def log_request(*args, **kwargs):
        pass

class FileWrapperHandler(ServerHandler):
    def __init__(self, *args, **kwargs):
        ServerHandler.__init__(self, *args, **kwargs)
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
