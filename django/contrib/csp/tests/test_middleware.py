from django.http import HttpResponse, HttpResponseServerError
from django.test import RequestFactory, TestCase
from django.test.utils import override_settings

from nose.tools import eq_

from csp.middleware import CSPMiddleware


HEADER = 'Content-Security-Policy'
mw = CSPMiddleware()
rf = RequestFactory()


class MiddlewareTests(TestCase):
    def test_add_header(self):
        request = rf.get('/')
        response = HttpResponse()
        mw.process_response(request, response)
        assert HEADER in response

    def test_exempt(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_exempt = True
        mw.process_response(request, response)
        assert HEADER not in response

    def text_exclude(self):
        request = rf.get('/admin/foo')
        response = HttpResponse()
        mw.process_response(request, response)
        assert HEADER not in response

    @override_settings(CSP_REPORT_ONLY=True)
    def test_report_only(self):
        request = rf.get('/')
        response = HttpResponse()
        mw.process_response(request, response)
        assert HEADER not in response
        assert HEADER + '-Report-Only' in response

    def test_dont_replace(self):
        request = rf.get('/')
        response = HttpResponse()
        response[HEADER] = 'default-src example.com'
        mw.process_response(request, response)
        eq_(response[HEADER], 'default-src example.com')

    def test_use_config(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_config = {'default-src': ['example.com']}
        mw.process_response(request, response)
        eq_(response[HEADER], 'default-src example.com')

    def test_use_update(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_update = {'default-src': ['example.com']}
        mw.process_response(request, response)
        eq_(response[HEADER], "default-src 'self' example.com")

    @override_settings(CSP_IMG_SRC=['foo.com'])
    def test_use_replace(self):
        request = rf.get('/')
        response = HttpResponse()
        response._csp_replace = {'img-src': ['bar.com']}
        mw.process_response(request, response)
        eq_(response[HEADER], "default-src 'self'; img-src bar.com")

    @override_settings(DEBUG=True)
    def test_debug_exempt(self):
        request = rf.get('/')
        response = HttpResponseServerError()
        mw.process_response(request, response)
        assert HEADER not in response
