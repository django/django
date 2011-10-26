from __future__ import with_statement

from django.core.exceptions import ImproperlyConfigured
from django.core.servers.basehttp import get_internal_wsgi_application
from django.core.wsgi import get_wsgi_application
from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.utils import unittest


class WSGITest(TestCase):
    urls = "regressiontests.wsgi.urls"

    def test_get_wsgi_application(self):
        """
        Verify that ``get_wsgi_application`` returns a functioning WSGI
        callable.

        """
        application = get_wsgi_application()

        environ = RequestFactory()._base_environ(
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
            response_data["headers"],
            [('Content-Type', 'text/html; charset=utf-8')])
        self.assertEqual(
            unicode(response),
            u"Content-Type: text/html; charset=utf-8\n\nHello World!")


class GetInternalWSGIApplicationTest(unittest.TestCase):
    @override_settings(WSGI_APPLICATION="regressiontests.wsgi.wsgi.application")
    def test_success(self):
        """
        If ``WSGI_APPLICATION`` is a dotted path, the referenced object is
        returned.

        """
        app = get_internal_wsgi_application()

        from .wsgi import application

        self.assertTrue(app is application)


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

            self.assertTrue(app is fake_app)
        finally:
            basehttp.get_wsgi_application = _orig_get_wsgi_app


    @override_settings(WSGI_APPLICATION="regressiontests.wsgi.noexist.app")
    def test_bad_module(self):
        with self.assertRaisesRegexp(
            ImproperlyConfigured,
            r"^WSGI application 'regressiontests.wsgi.noexist.app' could not be loaded; could not import module 'regressiontests.wsgi.noexist':"):

            get_internal_wsgi_application()


    @override_settings(WSGI_APPLICATION="regressiontests.wsgi.wsgi.noexist")
    def test_bad_name(self):
        with self.assertRaisesRegexp(
            ImproperlyConfigured,
            r"^WSGI application 'regressiontests.wsgi.wsgi.noexist' could not be loaded; can't find 'noexist' in module 'regressiontests.wsgi.wsgi':"):

            get_internal_wsgi_application()
