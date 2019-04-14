from django.core.exceptions import ImproperlyConfigured
from django.core.servers.basehttp import get_internal_wsgi_application
from django.core.signals import request_started
from django.core.wsgi import get_wsgi_application
from django.db import close_old_connections
from django.test import SimpleTestCase, override_settings
from django.test.client import RequestFactory


@override_settings(ROOT_URLCONF='wsgi.urls')
class WSGITest(SimpleTestCase):
    request_factory = RequestFactory()

    def setUp(self):
        request_started.disconnect(close_old_connections)

    def tearDown(self):
        request_started.connect(close_old_connections)

    def test_get_wsgi_application(self):
        """
        get_wsgi_application() returns a functioning WSGI callable.
        """
        application = get_wsgi_application()

        environ = self.request_factory._base_environ(
            PATH_INFO="/",
            CONTENT_TYPE="text/html; charset=utf-8",
            REQUEST_METHOD="GET"
        )

        response_data = {}

        def start_response(status, headers):
            response_data["status"] = status
            response_data["headers"] = headers

        response = application(environ, start_response)

        self.assertEqual(response_data["status"], "200 OK")
        self.assertEqual(
            set(response_data["headers"]),
            {('Content-Length', '12'), ('Content-Type', 'text/html; charset=utf-8')})
        self.assertIn(bytes(response), [
            b"Content-Length: 12\r\nContent-Type: text/html; charset=utf-8\r\n\r\nHello World!",
            b"Content-Type: text/html; charset=utf-8\r\nContent-Length: 12\r\n\r\nHello World!"
        ])

    def test_file_wrapper(self):
        """
        FileResponse uses wsgi.file_wrapper.
        """
        class FileWrapper:
            def __init__(self, filelike, blksize=8192):
                filelike.close()
        application = get_wsgi_application()
        environ = self.request_factory._base_environ(
            PATH_INFO='/file/',
            REQUEST_METHOD='GET',
            **{'wsgi.file_wrapper': FileWrapper}
        )
        response_data = {}

        def start_response(status, headers):
            response_data['status'] = status
            response_data['headers'] = headers
        response = application(environ, start_response)
        self.assertEqual(response_data['status'], '200 OK')
        self.assertIsInstance(response, FileWrapper)


class GetInternalWSGIApplicationTest(SimpleTestCase):
    @override_settings(WSGI_APPLICATION="wsgi.wsgi.application")
    def test_success(self):
        """
        If ``WSGI_APPLICATION`` is a dotted path, the referenced object is
        returned.
        """
        app = get_internal_wsgi_application()

        from .wsgi import application

        self.assertIs(app, application)

    @override_settings(WSGI_APPLICATION=None)
    def test_default(self):
        """
        If ``WSGI_APPLICATION`` is ``None``, the return value of
        ``get_wsgi_application`` is returned.
        """
        # Mock out get_wsgi_application so we know its return value is used
        fake_app = object()

        def mock_get_wsgi_app():
            return fake_app
        from django.core.servers import basehttp
        _orig_get_wsgi_app = basehttp.get_wsgi_application
        basehttp.get_wsgi_application = mock_get_wsgi_app

        try:
            app = get_internal_wsgi_application()

            self.assertIs(app, fake_app)
        finally:
            basehttp.get_wsgi_application = _orig_get_wsgi_app

    @override_settings(WSGI_APPLICATION="wsgi.noexist.app")
    def test_bad_module(self):
        msg = "WSGI application 'wsgi.noexist.app' could not be loaded; Error importing"
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            get_internal_wsgi_application()

    @override_settings(WSGI_APPLICATION="wsgi.wsgi.noexist")
    def test_bad_name(self):
        msg = "WSGI application 'wsgi.wsgi.noexist' could not be loaded; Error importing"
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            get_internal_wsgi_application()
