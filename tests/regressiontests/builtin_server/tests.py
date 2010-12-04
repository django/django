from StringIO import StringIO

from django.core.servers.basehttp import ServerHandler
from django.utils.unittest import TestCase

#
# Tests for #9659: wsgi.file_wrapper in the builtin server.
# We need to mock a couple of of handlers and keep track of what
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
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return ['Hello World!']

def wsgi_app_file_wrapper(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return environ['wsgi.file_wrapper'](StringIO('foo'))

class WSGIFileWrapperTests(TestCase):
    """
    Test that the wsgi.file_wrapper works for the builting server.
    """

    def test_file_wrapper_uses_sendfile(self):
        env = {'SERVER_PROTOCOL': 'HTTP/1.0'}
        err = StringIO()
        handler = FileWrapperHandler(None, StringIO(), err, env)
        handler.run(wsgi_app_file_wrapper)
        self.assert_(handler._used_sendfile)

    def test_file_wrapper_no_sendfile(self):
        env = {'SERVER_PROTOCOL': 'HTTP/1.0'}
        err = StringIO()
        handler = FileWrapperHandler(None, StringIO(), err, env)
        handler.run(wsgi_app)
        self.assertFalse(handler._used_sendfile)
        self.assertEqual(handler.stdout.getvalue().splitlines()[-1],'Hello World!')
