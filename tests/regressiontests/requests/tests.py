from datetime import datetime, timedelta
import time
import unittest

from django.conf import settings
from django.http import HttpRequest, HttpResponse, parse_cookie
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.modpython import ModPythonRequest
from django.utils.http import cookie_date


class RequestsTests(unittest.TestCase):

    def test_httprequest(self):
        request = HttpRequest()
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(request.META.keys(), [])

    def test_wsgirequest(self):
        request = WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus'})
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(set(request.META.keys()), set(['PATH_INFO', 'REQUEST_METHOD', 'SCRIPT_NAME']))
        self.assertEqual(request.META['PATH_INFO'], 'bogus')
        self.assertEqual(request.META['REQUEST_METHOD'], 'bogus')
        self.assertEqual(request.META['SCRIPT_NAME'], '')

    def test_modpythonrequest(self):
        class FakeModPythonRequest(ModPythonRequest):
           def __init__(self, *args, **kwargs):
               super(FakeModPythonRequest, self).__init__(*args, **kwargs)
               self._get = self._post = self._meta = self._cookies = {}

        class Dummy:
            def get_options(self):
                return {}

        req = Dummy()
        req.uri = 'bogus'
        request = FakeModPythonRequest(req)
        self.assertEqual(request.path, 'bogus')
        self.assertEqual(request.GET.keys(), [])
        self.assertEqual(request.POST.keys(), [])
        self.assertEqual(request.COOKIES.keys(), [])
        self.assertEqual(request.META.keys(), [])

    def test_parse_cookie(self):
        self.assertEqual(parse_cookie('invalid:key=true'), {})

    def test_httprequest_location(self):
        request = HttpRequest()
        self.assertEqual(request.build_absolute_uri(location="https://www.example.com/asdf"),
            'https://www.example.com/asdf')

        request.get_host = lambda: 'www.example.com'
        request.path = ''
        self.assertEqual(request.build_absolute_uri(location="/path/with:colons"),
            'http://www.example.com/path/with:colons')

    def test_http_get_host(self):
        old_USE_X_FORWARDED_HOST = settings.USE_X_FORWARDED_HOST
        try:
            settings.USE_X_FORWARDED_HOST = False

            # Check if X_FORWARDED_HOST is provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_X_FORWARDED_HOST': u'forward.com',
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            # X_FORWARDED_HOST is ignored.
            self.assertEqual(request.get_host(), 'example.com')

            # Check if X_FORWARDED_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'example.com')

            # Check if HTTP_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'internal.com')

            # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 8042,
            }
            self.assertEqual(request.get_host(), 'internal.com:8042')

        finally:
            settings.USE_X_FORWARDED_HOST = old_USE_X_FORWARDED_HOST

    def test_http_get_host_with_x_forwarded_host(self):
        old_USE_X_FORWARDED_HOST = settings.USE_X_FORWARDED_HOST
        try:
            settings.USE_X_FORWARDED_HOST = True

            # Check if X_FORWARDED_HOST is provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_X_FORWARDED_HOST': u'forward.com',
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            # X_FORWARDED_HOST is obeyed.
            self.assertEqual(request.get_host(), 'forward.com')

            # Check if X_FORWARDED_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'HTTP_HOST': u'example.com',
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'example.com')

            # Check if HTTP_HOST isn't provided.
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 80,
            }
            self.assertEqual(request.get_host(), 'internal.com')

            # Check if HTTP_HOST isn't provided, and we're on a nonstandard port
            request = HttpRequest()
            request.META = {
                u'SERVER_NAME': u'internal.com',
                u'SERVER_PORT': 8042,
            }
            self.assertEqual(request.get_host(), 'internal.com:8042')

        finally:
            settings.USE_X_FORWARDED_HOST = old_USE_X_FORWARDED_HOST
