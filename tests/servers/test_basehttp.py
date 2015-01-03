from django.core.handlers.wsgi import WSGIRequest
from django.core.servers.basehttp import WSGIRequestHandler
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import captured_stderr
from django.utils.six import BytesIO


class WSGIRequestHandlerTestCase(TestCase):
    def test_https(self):
        request = WSGIRequest(RequestFactory().get('/').environ)
        request.makefile = lambda *args, **kwargs: BytesIO()

        handler = WSGIRequestHandler(request, '192.168.0.2', None)

        with captured_stderr() as stderr:
            handler.log_message("GET %s %s", str('\x16\x03'), "4")
            self.assertIn(
                "You're accessing the developement server over HTTPS, "
                "but it only supports HTTP.",
                stderr.getvalue()
            )
