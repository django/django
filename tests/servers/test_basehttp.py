from django.core.handlers.wsgi import WSGIRequest
from django.core.servers.basehttp import WSGIRequestHandler
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import captured_stderr
from django.utils.six import BytesIO


class Stub(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class WSGIRequestHandlerTestCase(TestCase):

    def test_log_message(self):
        request = WSGIRequest(RequestFactory().get('/').environ)
        request.makefile = lambda *args, **kwargs: BytesIO()
        handler = WSGIRequestHandler(request, '192.168.0.2', None)

        with captured_stderr() as stderr:
            handler.log_message('GET %s %s', 'A', 'B')
        self.assertIn('] GET A B', stderr.getvalue())

    def test_https(self):
        request = WSGIRequest(RequestFactory().get('/').environ)
        request.makefile = lambda *args, **kwargs: BytesIO()

        handler = WSGIRequestHandler(request, '192.168.0.2', None)

        with captured_stderr() as stderr:
            handler.log_message("GET %s %s", str('\x16\x03'), "4")
            self.assertIn(
                "You're accessing the development server over HTTPS, "
                "but it only supports HTTP.",
                stderr.getvalue()
            )

    def test_strips_underscore_headers(self):
        """WSGIRequestHandler ignores headers containing underscores.

        This follows the lead of nginx and Apache 2.4, and is to avoid
        ambiguity between dashes and underscores in mapping to WSGI environ,
        which can have security implications.
        """
        def test_app(environ, start_response):
            """A WSGI app that just reflects its HTTP environ."""
            start_response('200 OK', [])
            http_environ_items = sorted(
                '%s:%s' % (k, v) for k, v in environ.items()
                if k.startswith('HTTP_')
            )
            yield (','.join(http_environ_items)).encode('utf-8')

        rfile = BytesIO()
        rfile.write(b"GET / HTTP/1.0\r\n")
        rfile.write(b"Some-Header: good\r\n")
        rfile.write(b"Some_Header: bad\r\n")
        rfile.write(b"Other_Header: bad\r\n")
        rfile.seek(0)

        # WSGIRequestHandler closes the output file; we need to make this a
        # no-op so we can still read its contents.
        class UnclosableBytesIO(BytesIO):
            def close(self):
                pass

        wfile = UnclosableBytesIO()

        def makefile(mode, *a, **kw):
            if mode == 'rb':
                return rfile
            elif mode == 'wb':
                return wfile

        request = Stub(makefile=makefile)
        server = Stub(base_environ={}, get_app=lambda: test_app)

        # We don't need to check stderr, but we don't want it in test output
        with captured_stderr():
            # instantiating a handler runs the request as side effect
            WSGIRequestHandler(request, '192.168.0.2', server)

        wfile.seek(0)
        body = list(wfile.readlines())[-1]

        self.assertEqual(body, b'HTTP_SOME_HEADER:good')
