from io import BytesIO
from socketserver import ThreadingMixIn

from django.core.handlers.wsgi import WSGIRequest
from django.core.servers.basehttp import WSGIRequestHandler, WSGIServer
from django.test import SimpleTestCase
from django.test.client import RequestFactory
from django.test.utils import captured_stderr


class Stub(ThreadingMixIn):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def sendall(self, data):
        self.makefile("wb").write(data)


class UnclosableBytesIO(BytesIO):
    def close(self):
        # WSGIRequestHandler closes the output file; we need to make this a
        # no-op so we can still read its contents.
        pass


class WSGIRequestHandlerTestCase(SimpleTestCase):
    request_factory = RequestFactory()

    def test_log_message(self):
        request = WSGIRequest(self.request_factory.get("/").environ)
        request.makefile = lambda *args, **kwargs: BytesIO()
        handler = WSGIRequestHandler(request, "192.168.0.2", None)
        level_status_codes = {
            "info": [200, 301, 304],
            "warning": [400, 403, 404],
            "error": [500, 503],
        }
        for level, status_codes in level_status_codes.items():
            for status_code in status_codes:
                # The correct level gets the message.
                with self.assertLogs("django.server", level.upper()) as cm:
                    handler.log_message("GET %s %s", "A", str(status_code))
                self.assertIn("GET A %d" % status_code, cm.output[0])
                # Incorrect levels don't have any messages.
                for wrong_level in level_status_codes:
                    if wrong_level != level:
                        with self.assertLogs("django.server", "INFO") as cm:
                            handler.log_message("GET %s %s", "A", str(status_code))
                        self.assertNotEqual(
                            cm.records[0].levelname, wrong_level.upper()
                        )

    def test_https(self):
        request = WSGIRequest(self.request_factory.get("/").environ)
        request.makefile = lambda *args, **kwargs: BytesIO()

        handler = WSGIRequestHandler(request, "192.168.0.2", None)

        with self.assertLogs("django.server", "ERROR") as cm:
            handler.log_message("GET %s %s", "\x16\x03", "4")
        self.assertEqual(
            "You're accessing the development server over HTTPS, "
            "but it only supports HTTP.",
            cm.records[0].getMessage(),
        )

    def test_strips_underscore_headers(self):
        """WSGIRequestHandler ignores headers containing underscores.

        This follows the lead of nginx and Apache 2.4, and is to avoid
        ambiguity between dashes and underscores in mapping to WSGI environ,
        which can have security implications.
        """

        def test_app(environ, start_response):
            """A WSGI app that just reflects its HTTP environ."""
            start_response("200 OK", [])
            http_environ_items = sorted(
                "%s:%s" % (k, v) for k, v in environ.items() if k.startswith("HTTP_")
            )
            yield (",".join(http_environ_items)).encode()

        rfile = BytesIO()
        rfile.write(b"GET / HTTP/1.0\r\n")
        rfile.write(b"Some-Header: good\r\n")
        rfile.write(b"Some_Header: bad\r\n")
        rfile.write(b"Other_Header: bad\r\n")
        rfile.seek(0)

        wfile = UnclosableBytesIO()

        def makefile(mode, *a, **kw):
            if mode == "rb":
                return rfile
            elif mode == "wb":
                return wfile

        request = Stub(makefile=makefile)
        server = Stub(base_environ={}, get_app=lambda: test_app)

        # Prevent logging from appearing in test output.
        with self.assertLogs("django.server", "INFO"):
            # instantiating a handler runs the request as side effect
            WSGIRequestHandler(request, "192.168.0.2", server)

        wfile.seek(0)
        body = list(wfile.readlines())[-1]

        self.assertEqual(body, b"HTTP_SOME_HEADER:good")

    def test_no_body_returned_for_head_requests(self):
        hello_world_body = b"<!DOCTYPE html><html><body>Hello World</body></html>"
        content_length = len(hello_world_body)

        def test_app(environ, start_response):
            """A WSGI app that returns a hello world."""
            start_response("200 OK", [])
            return [hello_world_body]

        rfile = BytesIO(b"GET / HTTP/1.0\r\n")
        rfile.seek(0)

        wfile = UnclosableBytesIO()

        def makefile(mode, *a, **kw):
            if mode == "rb":
                return rfile
            elif mode == "wb":
                return wfile

        request = Stub(makefile=makefile)
        server = Stub(base_environ={}, get_app=lambda: test_app)

        # Prevent logging from appearing in test output.
        with self.assertLogs("django.server", "INFO"):
            # Instantiating a handler runs the request as side effect.
            WSGIRequestHandler(request, "192.168.0.2", server)

        wfile.seek(0)
        lines = list(wfile.readlines())
        body = lines[-1]
        # The body is returned in a GET response.
        self.assertEqual(body, hello_world_body)
        self.assertIn(f"Content-Length: {content_length}\r\n".encode(), lines)
        self.assertNotIn(b"Connection: close\r\n", lines)

        rfile = BytesIO(b"HEAD / HTTP/1.0\r\n")
        rfile.seek(0)
        wfile = UnclosableBytesIO()

        with self.assertLogs("django.server", "INFO"):
            WSGIRequestHandler(request, "192.168.0.2", server)

        wfile.seek(0)
        lines = list(wfile.readlines())
        body = lines[-1]
        # The body is not returned in a HEAD response.
        self.assertEqual(body, b"\r\n")
        self.assertIs(
            any([line.startswith(b"Content-Length:") for line in lines]), False
        )
        self.assertNotIn(b"Connection: close\r\n", lines)


class WSGIServerTestCase(SimpleTestCase):
    request_factory = RequestFactory()

    def test_broken_pipe_errors(self):
        """WSGIServer handles broken pipe errors."""
        request = WSGIRequest(self.request_factory.get("/").environ)
        client_address = ("192.168.2.0", 8080)
        msg = f"- Broken pipe from {client_address}"
        tests = [
            BrokenPipeError,
            ConnectionAbortedError,
            ConnectionResetError,
        ]
        for exception in tests:
            with self.subTest(exception=exception):
                try:
                    server = WSGIServer(("localhost", 0), WSGIRequestHandler)
                    try:
                        raise exception()
                    except Exception:
                        with captured_stderr() as err:
                            with self.assertLogs("django.server", "INFO") as cm:
                                server.handle_error(request, client_address)
                        self.assertEqual(err.getvalue(), "")
                        self.assertEqual(cm.records[0].getMessage(), msg)
                finally:
                    server.server_close()
