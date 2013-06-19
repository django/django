# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import gzip
from io import BytesIO
import random
import re
import warnings

from django.conf import settings
from django.core import mail
from django.db import (transaction, connections, DEFAULT_DB_ALIAS,
                       IntegrityError)
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.middleware.common import CommonMiddleware, BrokenLinkEmailsMiddleware
from django.middleware.http import ConditionalGetMiddleware
from django.middleware.gzip import GZipMiddleware
from django.middleware.transaction import TransactionMiddleware
from django.test import TransactionTestCase, TestCase, RequestFactory
from django.test.utils import override_settings, IgnorePendingDeprecationWarningsMixin
from django.utils import six
from django.utils.encoding import force_str
from django.utils.six.moves import xrange
from django.utils.unittest import expectedFailure, skipIf

from .models import Band


class CommonMiddlewareTest(TestCase):

    def _get_request(self, path):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = request.path_info = "/middleware/%s" % path
        return request

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_have_slash(self):
        """
        Tests that URLs with slashes go unmolested.
        """
        request = self._get_request('slash/')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_resource(self):
        """
        Tests that matches to explicit slashless URLs go unmolested.
        """
        request = self._get_request('noslash')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_unknown(self):
        """
        Tests that APPEND_SLASH doesn't redirect to unknown resources.
        """
        request = self._get_request('unknown')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_redirect(self):
        """
        Tests that APPEND_SLASH redirects slashless URLs to a valid pattern.
        """
        request = self._get_request('slash')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://testserver/middleware/slash/')

    @override_settings(APPEND_SLASH=True, DEBUG=True)
    def test_append_slash_no_redirect_on_POST_in_DEBUG(self):
        """
        Tests that while in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST to an URL which would normally be
        redirected to a slashed version.
        """
        request = self._get_request('slash')
        request.method = 'POST'
        with six.assertRaisesRegex(self, RuntimeError, 'end in a slash'):
            CommonMiddleware().process_request(request)

    @override_settings(APPEND_SLASH=False)
    def test_append_slash_disabled(self):
        """
        Tests disabling append slash functionality.
        """
        request = self._get_request('slash')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_quoted(self):
        """
        Tests that URLs which require quoting are redirected to their slash
        version ok.
        """
        request = self._get_request('needsquoting#')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r.url,
            'http://testserver/middleware/needsquoting%23/')

    @override_settings(APPEND_SLASH=False, PREPEND_WWW=True)
    def test_prepend_www(self):
        request = self._get_request('path/')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r.url,
            'http://www.testserver/middleware/path/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_have_slash(self):
        request = self._get_request('slash/')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url,
                          'http://www.testserver/middleware/slash/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_slashless(self):
        request = self._get_request('slash')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url,
                          'http://www.testserver/middleware/slash/')


    # The following tests examine expected behavior given a custom urlconf that
    # overrides the default one through the request object.

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_have_slash_custom_urlconf(self):
        """
        Tests that URLs with slashes go unmolested.
        """
        request = self._get_request('customurlconf/slash/')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_resource_custom_urlconf(self):
        """
        Tests that matches to explicit slashless URLs go unmolested.
        """
        request = self._get_request('customurlconf/noslash')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_unknown_custom_urlconf(self):
        """
        Tests that APPEND_SLASH doesn't redirect to unknown resources.
        """
        request = self._get_request('customurlconf/unknown')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_redirect_custom_urlconf(self):
        """
        Tests that APPEND_SLASH redirects slashless URLs to a valid pattern.
        """
        request = self._get_request('customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertFalse(r is None,
            "CommonMiddlware failed to return APPEND_SLASH redirect using request.urlconf")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://testserver/middleware/customurlconf/slash/')

    @override_settings(APPEND_SLASH=True, DEBUG=True)
    def test_append_slash_no_redirect_on_POST_in_DEBUG_custom_urlconf(self):
        """
        Tests that while in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST to an URL which would normally be
        redirected to a slashed version.
        """
        request = self._get_request('customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        request.method = 'POST'
        with six.assertRaisesRegex(self, RuntimeError, 'end in a slash'):
            CommonMiddleware().process_request(request)

    @override_settings(APPEND_SLASH=False)
    def test_append_slash_disabled_custom_urlconf(self):
        """
        Tests disabling append slash functionality.
        """
        request = self._get_request('customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_quoted_custom_urlconf(self):
        """
        Tests that URLs which require quoting are redirected to their slash
        version ok.
        """
        request = self._get_request('customurlconf/needsquoting#')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertFalse(r is None,
            "CommonMiddlware failed to return APPEND_SLASH redirect using request.urlconf")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r.url,
            'http://testserver/middleware/customurlconf/needsquoting%23/')

    @override_settings(APPEND_SLASH=False, PREPEND_WWW=True)
    def test_prepend_www_custom_urlconf(self):
        request = self._get_request('customurlconf/path/')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r.url,
            'http://www.testserver/middleware/customurlconf/path/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_have_slash_custom_urlconf(self):
        request = self._get_request('customurlconf/slash/')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url,
                          'http://www.testserver/middleware/customurlconf/slash/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_slashless_custom_urlconf(self):
        request = self._get_request('customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url,
                          'http://www.testserver/middleware/customurlconf/slash/')

    # Legacy tests for the 404 error reporting via email (to be removed in 1.8)

    @override_settings(IGNORABLE_404_URLS=(re.compile(r'foo'),),
                       SEND_BROKEN_LINK_EMAILS=True,
                       MANAGERS=('PHB@dilbert.com',))
    def test_404_error_reporting(self):
        request = self._get_request('regular_url/that/does/not/exist')
        request.META['HTTP_REFERER'] = '/another/url/'
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PendingDeprecationWarning)
            response = self.client.get(request.path)
            CommonMiddleware().process_response(request, response)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Broken', mail.outbox[0].subject)

    @override_settings(IGNORABLE_404_URLS=(re.compile(r'foo'),),
                       SEND_BROKEN_LINK_EMAILS=True,
                       MANAGERS=('PHB@dilbert.com',))
    def test_404_error_reporting_no_referer(self):
        request = self._get_request('regular_url/that/does/not/exist')
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PendingDeprecationWarning)
            response = self.client.get(request.path)
            CommonMiddleware().process_response(request, response)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(IGNORABLE_404_URLS=(re.compile(r'foo'),),
                       SEND_BROKEN_LINK_EMAILS=True,
                       MANAGERS=('PHB@dilbert.com',))
    def test_404_error_reporting_ignored_url(self):
        request = self._get_request('foo_url/that/does/not/exist/either')
        request.META['HTTP_REFERER'] = '/another/url/'
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", PendingDeprecationWarning)
            response = self.client.get(request.path)
            CommonMiddleware().process_response(request, response)
        self.assertEqual(len(mail.outbox), 0)

    # Other tests

    def test_non_ascii_query_string_does_not_crash(self):
        """Regression test for #15152"""
        request = self._get_request('slash')
        request.META['QUERY_STRING'] = force_str('drink=café')
        response = CommonMiddleware().process_request(request)
        self.assertEqual(response.status_code, 301)


@override_settings(
    IGNORABLE_404_URLS=(re.compile(r'foo'),),
    MANAGERS=('PHB@dilbert.com',),
)
class BrokenLinkEmailsMiddlewareTest(TestCase):

    def setUp(self):
        self.req = HttpRequest()
        self.req.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        self.req.path = self.req.path_info = 'regular_url/that/does/not/exist'
        self.resp = self.client.get(self.req.path)

    def test_404_error_reporting(self):
        self.req.META['HTTP_REFERER'] = '/another/url/'
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Broken', mail.outbox[0].subject)

    def test_404_error_reporting_no_referer(self):
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)

    def test_404_error_reporting_ignored_url(self):
        self.req.path = self.req.path_info = 'foo_url/that/does/not/exist'
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)

    @skipIf(six.PY3, "HTTP_REFERER is str type on Python 3")
    def test_404_error_nonascii_referrer(self):
        # Such referer strings should not happen, but anyway, if it happens,
        # let's not crash
        self.req.META['HTTP_REFERER'] = b'http://testserver/c/\xd0\xbb\xd0\xb8/'
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)

    def test_custom_request_checker(self):
        class SubclassedMiddleware(BrokenLinkEmailsMiddleware):
            ignored_user_agent_patterns = (re.compile(r'Spider.*'),
                                           re.compile(r'Robot.*'))
            def is_ignorable_request(self, request, uri, domain, referer):
                '''Check user-agent in addition to normal checks.'''
                if super(SubclassedMiddleware, self).is_ignorable_request(request, uri, domain, referer):
                    return True
                user_agent = request.META['HTTP_USER_AGENT']
                return any(pattern.search(user_agent) for pattern in
                               self.ignored_user_agent_patterns)

        self.req.META['HTTP_REFERER'] = '/another/url/'
        self.req.META['HTTP_USER_AGENT'] = 'Spider machine 3.4'
        SubclassedMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)
        self.req.META['HTTP_USER_AGENT'] = 'My user agent'
        SubclassedMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)

class ConditionalGetMiddlewareTest(TestCase):
    urls = 'middleware.cond_get_urls'
    def setUp(self):
        self.req = HttpRequest()
        self.req.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        self.req.path = self.req.path_info = "/"
        self.resp = self.client.get(self.req.path)

    # Tests for the Date header

    def test_date_header_added(self):
        self.assertFalse('Date' in self.resp)
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertTrue('Date' in self.resp)

    # Tests for the Content-Length header

    def test_content_length_header_added(self):
        content_length = len(self.resp.content)
        self.assertFalse('Content-Length' in self.resp)
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertTrue('Content-Length' in self.resp)
        self.assertEqual(int(self.resp['Content-Length']), content_length)

    def test_content_length_header_not_added(self):
        resp = StreamingHttpResponse('content')
        self.assertFalse('Content-Length' in resp)
        resp = ConditionalGetMiddleware().process_response(self.req, resp)
        self.assertFalse('Content-Length' in resp)

    def test_content_length_header_not_changed(self):
        bad_content_length = len(self.resp.content) + 10
        self.resp['Content-Length'] = bad_content_length
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(int(self.resp['Content-Length']), bad_content_length)

    # Tests for the ETag header

    def test_if_none_match_and_no_etag(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = 'spam'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)

    def test_no_if_none_match_and_etag(self):
        self.resp['ETag'] = 'eggs'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)

    def test_if_none_match_and_same_etag(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = self.resp['ETag'] = 'spam'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 304)

    def test_if_none_match_and_different_etag(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = 'spam'
        self.resp['ETag'] = 'eggs'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)

    @override_settings(USE_ETAGS=True)
    def test_etag(self):
        req = HttpRequest()
        res = HttpResponse('content')
        self.assertTrue(
            CommonMiddleware().process_response(req, res).has_header('ETag'))

    @override_settings(USE_ETAGS=True)
    def test_etag_streaming_response(self):
        req = HttpRequest()
        res = StreamingHttpResponse(['content'])
        res['ETag'] = 'tomatoes'
        self.assertEqual(
            CommonMiddleware().process_response(req, res).get('ETag'),
            'tomatoes')

    @override_settings(USE_ETAGS=True)
    def test_no_etag_streaming_response(self):
        req = HttpRequest()
        res = StreamingHttpResponse(['content'])
        self.assertFalse(
            CommonMiddleware().process_response(req, res).has_header('ETag'))

    # Tests for the Last-Modified header

    def test_if_modified_since_and_no_last_modified(self):
        self.req.META['HTTP_IF_MODIFIED_SINCE'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)

    def test_no_if_modified_since_and_last_modified(self):
        self.resp['Last-Modified'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)

    def test_if_modified_since_and_same_last_modified(self):
        self.req.META['HTTP_IF_MODIFIED_SINCE'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp['Last-Modified'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 304)

    def test_if_modified_since_and_last_modified_in_the_past(self):
        self.req.META['HTTP_IF_MODIFIED_SINCE'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp['Last-Modified'] = 'Sat, 12 Feb 2011 17:35:44 GMT'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 304)

    def test_if_modified_since_and_last_modified_in_the_future(self):
        self.req.META['HTTP_IF_MODIFIED_SINCE'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp['Last-Modified'] = 'Sat, 12 Feb 2011 17:41:44 GMT'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)


class XFrameOptionsMiddlewareTest(TestCase):
    """
    Tests for the X-Frame-Options clickjacking prevention middleware.
    """

    def test_same_origin(self):
        """
        Tests that the X_FRAME_OPTIONS setting can be set to SAMEORIGIN to
        have the middleware use that value for the HTTP header.
        """
        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        with override_settings(X_FRAME_OPTIONS='sameorigin'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_deny(self):
        """
        Tests that the X_FRAME_OPTIONS setting can be set to DENY to
        have the middleware use that value for the HTTP header.
        """
        with override_settings(X_FRAME_OPTIONS='DENY'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'DENY')

        with override_settings(X_FRAME_OPTIONS='deny'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_defaults_sameorigin(self):
        """
        Tests that if the X_FRAME_OPTIONS setting is not set then it defaults
        to SAMEORIGIN.
        """
        with override_settings(X_FRAME_OPTIONS=None):
            del settings.X_FRAME_OPTIONS    # restored by override_settings
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_dont_set_if_set(self):
        """
        Tests that if the X-Frame-Options header is already set then the
        middleware does not attempt to override it.
        """
        with override_settings(X_FRAME_OPTIONS='DENY'):
            response = HttpResponse()
            response['X-Frame-Options'] = 'SAMEORIGIN'
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           response)
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            response = HttpResponse()
            response['X-Frame-Options'] = 'DENY'
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           response)
            self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_response_exempt(self):
        """
        Tests that if the response has a xframe_options_exempt attribute set
        to False then it still sets the header, but if it's set to True then
        it does not.
        """
        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            response = HttpResponse()
            response.xframe_options_exempt = False
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           response)
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

            response = HttpResponse()
            response.xframe_options_exempt = True
            r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                           response)
            self.assertEqual(r.get('X-Frame-Options', None), None)

    def test_is_extendable(self):
        """
        Tests that the XFrameOptionsMiddleware method that determines the
        X-Frame-Options header value can be overridden based on something in
        the request or response.
        """
        class OtherXFrameOptionsMiddleware(XFrameOptionsMiddleware):
            # This is just an example for testing purposes...
            def get_xframe_options_value(self, request, response):
                if getattr(request, 'sameorigin', False):
                    return 'SAMEORIGIN'
                if getattr(response, 'sameorigin', False):
                    return 'SAMEORIGIN'
                return 'DENY'

        with override_settings(X_FRAME_OPTIONS='DENY'):
            response = HttpResponse()
            response.sameorigin = True
            r = OtherXFrameOptionsMiddleware().process_response(HttpRequest(),
                                                                response)
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

            request = HttpRequest()
            request.sameorigin = True
            r = OtherXFrameOptionsMiddleware().process_response(request,
                                                                HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            r = OtherXFrameOptionsMiddleware().process_response(HttpRequest(),
                                                                HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'DENY')


class GZipMiddlewareTest(TestCase):
    """
    Tests the GZip middleware.
    """
    short_string = b"This string is too short to be worth compressing."
    compressible_string = b'a' * 500
    uncompressible_string = b''.join(six.int2byte(random.randint(0, 255)) for _ in xrange(500))
    sequence = [b'a' * 500, b'b' * 200, b'a' * 300]

    def setUp(self):
        self.req = HttpRequest()
        self.req.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        self.req.path = self.req.path_info = "/"
        self.req.META['HTTP_ACCEPT_ENCODING'] = 'gzip, deflate'
        self.req.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 5.1; rv:9.0.1) Gecko/20100101 Firefox/9.0.1'
        self.resp = HttpResponse()
        self.resp.status_code = 200
        self.resp.content = self.compressible_string
        self.resp['Content-Type'] = 'text/html; charset=UTF-8'
        self.stream_resp = StreamingHttpResponse(self.sequence)
        self.stream_resp['Content-Type'] = 'text/html; charset=UTF-8'

    @staticmethod
    def decompress(gzipped_string):
        return gzip.GzipFile(mode='rb', fileobj=BytesIO(gzipped_string)).read()

    def test_compress_response(self):
        """
        Tests that compression is performed on responses with compressible content.
        """
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.decompress(r.content), self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), 'gzip')
        self.assertEqual(r.get('Content-Length'), str(len(r.content)))

    def test_compress_streaming_response(self):
        """
        Tests that compression is performed on responses with streaming content.
        """
        r = GZipMiddleware().process_response(self.req, self.stream_resp)
        self.assertEqual(self.decompress(b''.join(r)), b''.join(self.sequence))
        self.assertEqual(r.get('Content-Encoding'), 'gzip')
        self.assertFalse(r.has_header('Content-Length'))

    def test_compress_non_200_response(self):
        """
        Tests that compression is performed on responses with a status other than 200.
        See #10762.
        """
        self.resp.status_code = 404
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.decompress(r.content), self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), 'gzip')

    def test_no_compress_short_response(self):
        """
        Tests that compression isn't performed on responses with short content.
        """
        self.resp.content = self.short_string
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.short_string)
        self.assertEqual(r.get('Content-Encoding'), None)

    def test_no_compress_compressed_response(self):
        """
        Tests that compression isn't performed on responses that are already compressed.
        """
        self.resp['Content-Encoding'] = 'deflate'
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), 'deflate')

    def test_no_compress_ie_js_requests(self):
        """
        Tests that compression isn't performed on JavaScript requests from Internet Explorer.
        """
        self.req.META['HTTP_USER_AGENT'] = 'Mozilla/4.0 (compatible; MSIE 5.00; Windows 98)'
        self.resp['Content-Type'] = 'application/javascript; charset=UTF-8'
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), None)

    def test_no_compress_uncompressible_response(self):
        """
        Tests that compression isn't performed on responses with uncompressible content.
        """
        self.resp.content = self.uncompressible_string
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.uncompressible_string)
        self.assertEqual(r.get('Content-Encoding'), None)


@override_settings(USE_ETAGS=True)
class ETagGZipMiddlewareTest(TestCase):
    """
    Tests if the ETag middleware behaves correctly with GZip middleware.
    """
    compressible_string = b'a' * 500

    def setUp(self):
        self.rf = RequestFactory()

    def test_compress_response(self):
        """
        Tests that ETag is changed after gzip compression is performed.
        """
        request = self.rf.get('/', HTTP_ACCEPT_ENCODING='gzip, deflate')
        response = GZipMiddleware().process_response(request,
            CommonMiddleware().process_response(request,
                HttpResponse(self.compressible_string)))
        gzip_etag = response.get('ETag')

        request = self.rf.get('/', HTTP_ACCEPT_ENCODING='')
        response = GZipMiddleware().process_response(request,
            CommonMiddleware().process_response(request,
                HttpResponse(self.compressible_string)))
        nogzip_etag = response.get('ETag')

        self.assertNotEqual(gzip_etag, nogzip_etag)

class TransactionMiddlewareTest(IgnorePendingDeprecationWarningsMixin, TransactionTestCase):
    """
    Test the transaction middleware.
    """

    available_apps = ['middleware']

    def setUp(self):
        super(TransactionMiddlewareTest, self).setUp()
        self.request = HttpRequest()
        self.request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        self.request.path = self.request.path_info = "/"
        self.response = HttpResponse()
        self.response.status_code = 200

    def tearDown(self):
        transaction.abort()
        super(TransactionMiddlewareTest, self).tearDown()

    def test_request(self):
        TransactionMiddleware().process_request(self.request)
        self.assertFalse(transaction.get_autocommit())

    def test_managed_response(self):
        transaction.enter_transaction_management()
        Band.objects.create(name='The Beatles')
        self.assertTrue(transaction.is_dirty())
        TransactionMiddleware().process_response(self.request, self.response)
        self.assertFalse(transaction.is_dirty())
        self.assertEqual(Band.objects.count(), 1)

    def test_exception(self):
        transaction.enter_transaction_management()
        Band.objects.create(name='The Beatles')
        self.assertTrue(transaction.is_dirty())
        TransactionMiddleware().process_exception(self.request, None)
        self.assertFalse(transaction.is_dirty())
        self.assertEqual(Band.objects.count(), 0)

    def test_failing_commit(self):
        # It is possible that connection.commit() fails. Check that
        # TransactionMiddleware handles such cases correctly.
        try:
            def raise_exception():
                raise IntegrityError()
            connections[DEFAULT_DB_ALIAS].commit = raise_exception
            transaction.enter_transaction_management()
            Band.objects.create(name='The Beatles')
            self.assertTrue(transaction.is_dirty())
            with self.assertRaises(IntegrityError):
                TransactionMiddleware().process_response(self.request, None)
            self.assertFalse(transaction.is_dirty())
            self.assertEqual(Band.objects.count(), 0)
            self.assertFalse(transaction.is_managed())
        finally:
            del connections[DEFAULT_DB_ALIAS].commit
