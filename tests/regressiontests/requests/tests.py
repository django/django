from datetime import datetime, timedelta
import time
import unittest

from django.http import HttpRequest, HttpResponse, parse_cookie
from django.core.handlers.wsgi import WSGIRequest
from django.core.handlers.modpython import ModPythonRequest
from django.utils.http import cookie_date

class RequestsTests(unittest.TestCase):

    def test_httprequest(self):
        self.assertEquals(repr(HttpRequest()),
            "<HttpRequest\n"\
            "GET:{},\n"\
            "POST:{},\n"\
            "COOKIES:{},\n"\
            "META:{}>"
        )

    def test_wsgirequest(self):
        self.assertEquals(repr(WSGIRequest({'PATH_INFO': 'bogus', 'REQUEST_METHOD': 'bogus'})),
            "<WSGIRequest\n"\
            "GET:<QueryDict: {}>,\n"\
            "POST:<QueryDict: {}>,\n"\
            "COOKIES:{},\n"\
            "META:{'PATH_INFO': u'bogus', 'REQUEST_METHOD': 'bogus', 'SCRIPT_NAME': u''}>"
        )

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
        self.assertEquals(repr(FakeModPythonRequest(req)),
            "<ModPythonRequest\n"\
            "path:bogus,\n"\
            "GET:{},\n"\
            "POST:{},\n"\
            "COOKIES:{},\n"\
            "META:{}>")

    def test_parse_cookie(self):
        self.assertEquals(parse_cookie('invalid:key=true'), {})

    def test_httprequest_location(self):
        request = HttpRequest()
        self.assertEquals(request.build_absolute_uri(location="https://www.example.com/asdf"),
            'https://www.example.com/asdf')

        request.get_host = lambda: 'www.example.com'
        request.path = ''
        self.assertEquals(request.build_absolute_uri(location="/path/with:colons"),
            'http://www.example.com/path/with:colons')
