# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import gzip
import random
import re
from io import BytesIO
from unittest import skipIf

from django.conf import settings
from django.core import mail
from django.core.exceptions import PermissionDenied
from django.http import (
    FileResponse, HttpRequest, HttpResponse, HttpResponseNotFound,
    HttpResponsePermanentRedirect, HttpResponseRedirect, StreamingHttpResponse,
)
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.middleware.common import (
    BrokenLinkEmailsMiddleware, CommonMiddleware,
)
from django.middleware.gzip import GZipMiddleware
from django.middleware.http import ConditionalGetMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.utils import six
from django.utils.encoding import force_str
from django.utils.six.moves import range
from django.utils.six.moves.urllib.parse import quote


@override_settings(ROOT_URLCONF='middleware.urls')
class CommonMiddlewareTest(SimpleTestCase):

    rf = RequestFactory()

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_have_slash(self):
        """
        URLs with slashes should go unmolested.
        """
        request = self.rf.get('/slash/')
        self.assertEqual(CommonMiddleware().process_request(request), None)
        response = HttpResponseNotFound()
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_resource(self):
        """
        Matches to explicit slashless URLs should go unmolested.
        """
        request = self.rf.get('/noslash')
        self.assertEqual(CommonMiddleware().process_request(request), None)
        response = HttpResponse("Here's the text of the Web page.")
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_unknown(self):
        """
        APPEND_SLASH should not redirect to unknown resources.
        """
        request = self.rf.get('/unknown')
        response = HttpResponseNotFound()
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_redirect(self):
        """
        APPEND_SLASH should redirect slashless URLs to a valid pattern.
        """
        request = self.rf.get('/slash')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_redirect_querystring(self):
        """
        APPEND_SLASH should preserve querystrings when redirecting.
        """
        request = self.rf.get('/slash?test=1')
        response = HttpResponseNotFound()
        r = CommonMiddleware().process_response(request, response)
        self.assertEqual(r.url, '/slash/?test=1')

    @override_settings(APPEND_SLASH=True, DEBUG=True)
    def test_append_slash_no_redirect_on_POST_in_DEBUG(self):
        """
        Tests that while in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST, PUT, or PATCH to an URL which
        would normally be redirected to a slashed version.
        """
        msg = "maintaining %s data. Change your form to point to testserver/slash/"
        request = self.rf.get('/slash')
        request.method = 'POST'
        response = HttpResponseNotFound()
        with self.assertRaisesMessage(RuntimeError, msg % request.method):
            CommonMiddleware().process_response(request, response)
        request = self.rf.get('/slash')
        request.method = 'PUT'
        with self.assertRaisesMessage(RuntimeError, msg % request.method):
            CommonMiddleware().process_response(request, response)
        request = self.rf.get('/slash')
        request.method = 'PATCH'
        with self.assertRaisesMessage(RuntimeError, msg % request.method):
            CommonMiddleware().process_response(request, response)

    @override_settings(APPEND_SLASH=False)
    def test_append_slash_disabled(self):
        """
        Disabling append slash functionality should leave slashless URLs alone.
        """
        request = self.rf.get('/slash')
        response = HttpResponseNotFound()
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_quoted(self):
        """
        URLs which require quoting should be redirected to their slash version.
        """
        request = self.rf.get(quote('/needsquoting#'))
        response = HttpResponseNotFound()
        r = CommonMiddleware().process_response(request, response)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, '/needsquoting%23/')

    @override_settings(APPEND_SLASH=False, PREPEND_WWW=True)
    def test_prepend_www(self):
        request = self.rf.get('/path/')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://www.testserver/path/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_have_slash(self):
        request = self.rf.get('/slash/')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://www.testserver/slash/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_slashless(self):
        request = self.rf.get('/slash')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://www.testserver/slash/')

    # The following tests examine expected behavior given a custom URLconf that
    # overrides the default one through the request object.

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_have_slash_custom_urlconf(self):
        """
        URLs with slashes should go unmolested.
        """
        request = self.rf.get('/customurlconf/slash/')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)
        response = HttpResponseNotFound()
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_resource_custom_urlconf(self):
        """
        Matches to explicit slashless URLs should go unmolested.
        """
        request = self.rf.get('/customurlconf/noslash')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)
        response = HttpResponse("Here's the text of the Web page.")
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_slashless_unknown_custom_urlconf(self):
        """
        APPEND_SLASH should not redirect to unknown resources.
        """
        request = self.rf.get('/customurlconf/unknown')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)
        response = HttpResponseNotFound()
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_redirect_custom_urlconf(self):
        """
        APPEND_SLASH should redirect slashless URLs to a valid pattern.
        """
        request = self.rf.get('/customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        response = HttpResponseNotFound()
        r = CommonMiddleware().process_response(request, response)
        self.assertIsNotNone(r, "CommonMiddleware failed to return APPEND_SLASH redirect using request.urlconf")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, '/customurlconf/slash/')

    @override_settings(APPEND_SLASH=True, DEBUG=True)
    def test_append_slash_no_redirect_on_POST_in_DEBUG_custom_urlconf(self):
        """
        Tests that while in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST to an URL which would normally be
        redirected to a slashed version.
        """
        request = self.rf.get('/customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        request.method = 'POST'
        response = HttpResponseNotFound()
        with self.assertRaisesMessage(RuntimeError, 'end in a slash'):
            CommonMiddleware().process_response(request, response)

    @override_settings(APPEND_SLASH=False)
    def test_append_slash_disabled_custom_urlconf(self):
        """
        Disabling append slash functionality should leave slashless URLs alone.
        """
        request = self.rf.get('/customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        self.assertEqual(CommonMiddleware().process_request(request), None)
        response = HttpResponseNotFound()
        self.assertEqual(CommonMiddleware().process_response(request, response), response)

    @override_settings(APPEND_SLASH=True)
    def test_append_slash_quoted_custom_urlconf(self):
        """
        URLs which require quoting should be redirected to their slash version.
        """
        request = self.rf.get(quote('/customurlconf/needsquoting#'))
        request.urlconf = 'middleware.extra_urls'
        response = HttpResponseNotFound()
        r = CommonMiddleware().process_response(request, response)
        self.assertIsNotNone(r, "CommonMiddleware failed to return APPEND_SLASH redirect using request.urlconf")
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, '/customurlconf/needsquoting%23/')

    @override_settings(APPEND_SLASH=False, PREPEND_WWW=True)
    def test_prepend_www_custom_urlconf(self):
        request = self.rf.get('/customurlconf/path/')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://www.testserver/customurlconf/path/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_have_slash_custom_urlconf(self):
        request = self.rf.get('/customurlconf/slash/')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://www.testserver/customurlconf/slash/')

    @override_settings(APPEND_SLASH=True, PREPEND_WWW=True)
    def test_prepend_www_append_slash_slashless_custom_urlconf(self):
        request = self.rf.get('/customurlconf/slash')
        request.urlconf = 'middleware.extra_urls'
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, 'http://www.testserver/customurlconf/slash/')

    # ETag + If-Not-Modified support tests

    @override_settings(USE_ETAGS=True)
    def test_etag(self):
        req = HttpRequest()
        res = HttpResponse('content')
        self.assertTrue(CommonMiddleware().process_response(req, res).has_header('ETag'))

    @override_settings(USE_ETAGS=True)
    def test_etag_streaming_response(self):
        req = HttpRequest()
        res = StreamingHttpResponse(['content'])
        res['ETag'] = 'tomatoes'
        self.assertEqual(CommonMiddleware().process_response(req, res).get('ETag'), 'tomatoes')

    @override_settings(USE_ETAGS=True)
    def test_no_etag_streaming_response(self):
        req = HttpRequest()
        res = StreamingHttpResponse(['content'])
        self.assertFalse(CommonMiddleware().process_response(req, res).has_header('ETag'))

    @override_settings(USE_ETAGS=True)
    def test_if_none_match(self):
        first_req = HttpRequest()
        first_res = CommonMiddleware().process_response(first_req, HttpResponse('content'))
        second_req = HttpRequest()
        second_req.method = 'GET'
        second_req.META['HTTP_IF_NONE_MATCH'] = first_res['ETag']
        second_res = CommonMiddleware().process_response(second_req, HttpResponse('content'))
        self.assertEqual(second_res.status_code, 304)

    # Other tests

    @override_settings(DISALLOWED_USER_AGENTS=[re.compile(r'foo')])
    def test_disallowed_user_agents(self):
        request = self.rf.get('/slash')
        request.META['HTTP_USER_AGENT'] = 'foo'
        with self.assertRaisesMessage(PermissionDenied, 'Forbidden user agent'):
            CommonMiddleware().process_request(request)

    def test_non_ascii_query_string_does_not_crash(self):
        """Regression test for #15152"""
        request = self.rf.get('/slash')
        request.META['QUERY_STRING'] = force_str('drink=café')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)

    def test_response_redirect_class(self):
        request = self.rf.get('/slash')
        response = HttpResponseNotFound()
        r = CommonMiddleware().process_response(request, response)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r.url, '/slash/')
        self.assertIsInstance(r, HttpResponsePermanentRedirect)

    def test_response_redirect_class_subclass(self):
        class MyCommonMiddleware(CommonMiddleware):
            response_redirect_class = HttpResponseRedirect

        request = self.rf.get('/slash')
        response = HttpResponseNotFound()
        r = MyCommonMiddleware().process_response(request, response)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/slash/')
        self.assertIsInstance(r, HttpResponseRedirect)


@override_settings(
    IGNORABLE_404_URLS=[re.compile(r'foo')],
    MANAGERS=['PHB@dilbert.com'],
)
class BrokenLinkEmailsMiddlewareTest(SimpleTestCase):

    rf = RequestFactory()

    def setUp(self):
        self.req = self.rf.get('/regular_url/that/does/not/exist')
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

    @skipIf(six.PY3, "HTTP_USER_AGENT is str type on Python 3")
    def test_404_error_nonascii_user_agent(self):
        # Such user agent strings should not happen, but anyway, if it happens,
        # let's not crash
        self.req.META['HTTP_REFERER'] = '/another/url/'
        self.req.META['HTTP_USER_AGENT'] = b'\xd0\xbb\xd0\xb8\xff\xff'
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('User agent: \u043b\u0438\ufffd\ufffd\n', mail.outbox[0].body)

    def test_custom_request_checker(self):
        class SubclassedMiddleware(BrokenLinkEmailsMiddleware):
            ignored_user_agent_patterns = (re.compile(r'Spider.*'), re.compile(r'Robot.*'))

            def is_ignorable_request(self, request, uri, domain, referer):
                '''Check user-agent in addition to normal checks.'''
                if super(SubclassedMiddleware, self).is_ignorable_request(request, uri, domain, referer):
                    return True
                user_agent = request.META['HTTP_USER_AGENT']
                return any(pattern.search(user_agent) for pattern in self.ignored_user_agent_patterns)

        self.req.META['HTTP_REFERER'] = '/another/url/'
        self.req.META['HTTP_USER_AGENT'] = 'Spider machine 3.4'
        SubclassedMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)
        self.req.META['HTTP_USER_AGENT'] = 'My user agent'
        SubclassedMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)

    def test_referer_equal_to_requested_url(self):
        """
        Some bots set the referer to the current URL to avoid being blocked by
        an referer check (#25302).
        """
        self.req.META['HTTP_REFERER'] = self.req.path
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)

        # URL with scheme and domain should also be ignored
        self.req.META['HTTP_REFERER'] = 'http://testserver%s' % self.req.path
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)

        # URL with a different scheme should be ignored as well because bots
        # tend to use http:// in referers even when browsing HTTPS websites.
        self.req.META['HTTP_X_PROTO'] = 'https'
        self.req.META['SERVER_PORT'] = 443
        with self.settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_PROTO', 'https')):
            BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)

    def test_referer_equal_to_requested_url_on_another_domain(self):
        self.req.META['HTTP_REFERER'] = 'http://anotherserver%s' % self.req.path
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(APPEND_SLASH=True)
    def test_referer_equal_to_requested_url_without_trailing_slash_when_append_slash_is_set(self):
        self.req.path = self.req.path_info = '/regular_url/that/does/not/exist/'
        self.req.META['HTTP_REFERER'] = self.req.path_info[:-1]
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(APPEND_SLASH=False)
    def test_referer_equal_to_requested_url_without_trailing_slash_when_append_slash_is_unset(self):
        self.req.path = self.req.path_info = '/regular_url/that/does/not/exist/'
        self.req.META['HTTP_REFERER'] = self.req.path_info[:-1]
        BrokenLinkEmailsMiddleware().process_response(self.req, self.resp)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(ROOT_URLCONF='middleware.cond_get_urls')
class ConditionalGetMiddlewareTest(SimpleTestCase):

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.resp = self.client.get(self.req.path_info)

    # Tests for the Date header

    def test_date_header_added(self):
        self.assertNotIn('Date', self.resp)
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertIn('Date', self.resp)

    # Tests for the Content-Length header

    def test_content_length_header_added(self):
        content_length = len(self.resp.content)
        self.assertNotIn('Content-Length', self.resp)
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertIn('Content-Length', self.resp)
        self.assertEqual(int(self.resp['Content-Length']), content_length)

    def test_content_length_header_not_added(self):
        resp = StreamingHttpResponse('content')
        self.assertNotIn('Content-Length', resp)
        resp = ConditionalGetMiddleware().process_response(self.req, resp)
        self.assertNotIn('Content-Length', resp)

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

    def test_if_none_match_and_same_etag_with_quotes(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = self.resp['ETag'] = '"spam"'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 304)

    def test_if_none_match_and_different_etag(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = 'spam'
        self.resp['ETag'] = 'eggs'
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 200)

    def test_if_none_match_and_redirect(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = self.resp['ETag'] = 'spam'
        self.resp['Location'] = '/'
        self.resp.status_code = 301
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 301)

    def test_if_none_match_and_client_error(self):
        self.req.META['HTTP_IF_NONE_MATCH'] = self.resp['ETag'] = 'spam'
        self.resp.status_code = 400
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 400)

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

    def test_if_modified_since_and_redirect(self):
        self.req.META['HTTP_IF_MODIFIED_SINCE'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp['Last-Modified'] = 'Sat, 12 Feb 2011 17:35:44 GMT'
        self.resp['Location'] = '/'
        self.resp.status_code = 301
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 301)

    def test_if_modified_since_and_client_error(self):
        self.req.META['HTTP_IF_MODIFIED_SINCE'] = 'Sat, 12 Feb 2011 17:38:44 GMT'
        self.resp['Last-Modified'] = 'Sat, 12 Feb 2011 17:35:44 GMT'
        self.resp.status_code = 400
        self.resp = ConditionalGetMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.resp.status_code, 400)


class XFrameOptionsMiddlewareTest(SimpleTestCase):
    """
    Tests for the X-Frame-Options clickjacking prevention middleware.
    """

    def test_same_origin(self):
        """
        The X_FRAME_OPTIONS setting can be set to SAMEORIGIN to have the
        middleware use that value for the HTTP header.
        """
        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        with override_settings(X_FRAME_OPTIONS='sameorigin'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_deny(self):
        """
        The X_FRAME_OPTIONS setting can be set to DENY to have the middleware
        use that value for the HTTP header.
        """
        with override_settings(X_FRAME_OPTIONS='DENY'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'DENY')

        with override_settings(X_FRAME_OPTIONS='deny'):
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_defaults_sameorigin(self):
        """
        If the X_FRAME_OPTIONS setting is not set then it defaults to
        SAMEORIGIN.
        """
        with override_settings(X_FRAME_OPTIONS=None):
            del settings.X_FRAME_OPTIONS    # restored by override_settings
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_dont_set_if_set(self):
        """
        If the X-Frame-Options header is already set then the middleware does
        not attempt to override it.
        """
        with override_settings(X_FRAME_OPTIONS='DENY'):
            response = HttpResponse()
            response['X-Frame-Options'] = 'SAMEORIGIN'
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), response)
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            response = HttpResponse()
            response['X-Frame-Options'] = 'DENY'
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), response)
            self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_response_exempt(self):
        """
        If the response has an xframe_options_exempt attribute set to False
        then it still sets the header, but if it's set to True then it doesn't.
        """
        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            response = HttpResponse()
            response.xframe_options_exempt = False
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), response)
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

            response = HttpResponse()
            response.xframe_options_exempt = True
            r = XFrameOptionsMiddleware().process_response(HttpRequest(), response)
            self.assertIsNone(r.get('X-Frame-Options'))

    def test_is_extendable(self):
        """
        The XFrameOptionsMiddleware method that determines the X-Frame-Options
        header value can be overridden based on something in the request or
        response.
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
            r = OtherXFrameOptionsMiddleware().process_response(HttpRequest(), response)
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

            request = HttpRequest()
            request.sameorigin = True
            r = OtherXFrameOptionsMiddleware().process_response(request, HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        with override_settings(X_FRAME_OPTIONS='SAMEORIGIN'):
            r = OtherXFrameOptionsMiddleware().process_response(HttpRequest(), HttpResponse())
            self.assertEqual(r['X-Frame-Options'], 'DENY')


class GZipMiddlewareTest(SimpleTestCase):
    """
    Tests the GZipMiddleware.
    """
    short_string = b"This string is too short to be worth compressing."
    compressible_string = b'a' * 500
    incompressible_string = b''.join(six.int2byte(random.randint(0, 255)) for _ in range(500))
    sequence = [b'a' * 500, b'b' * 200, b'a' * 300]
    sequence_unicode = ['a' * 500, 'é' * 200, 'a' * 300]

    def setUp(self):
        self.req = RequestFactory().get('/')
        self.req.META['HTTP_ACCEPT_ENCODING'] = 'gzip, deflate'
        self.req.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 5.1; rv:9.0.1) Gecko/20100101 Firefox/9.0.1'
        self.resp = HttpResponse()
        self.resp.status_code = 200
        self.resp.content = self.compressible_string
        self.resp['Content-Type'] = 'text/html; charset=UTF-8'
        self.stream_resp = StreamingHttpResponse(self.sequence)
        self.stream_resp['Content-Type'] = 'text/html; charset=UTF-8'
        self.stream_resp_unicode = StreamingHttpResponse(self.sequence_unicode)
        self.stream_resp_unicode['Content-Type'] = 'text/html; charset=UTF-8'

    @staticmethod
    def decompress(gzipped_string):
        with gzip.GzipFile(mode='rb', fileobj=BytesIO(gzipped_string)) as f:
            return f.read()

    def test_compress_response(self):
        """
        Compression is performed on responses with compressible content.
        """
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.decompress(r.content), self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), 'gzip')
        self.assertEqual(r.get('Content-Length'), str(len(r.content)))

    def test_compress_streaming_response(self):
        """
        Compression is performed on responses with streaming content.
        """
        r = GZipMiddleware().process_response(self.req, self.stream_resp)
        self.assertEqual(self.decompress(b''.join(r)), b''.join(self.sequence))
        self.assertEqual(r.get('Content-Encoding'), 'gzip')
        self.assertFalse(r.has_header('Content-Length'))

    def test_compress_streaming_response_unicode(self):
        """
        Compression is performed on responses with streaming Unicode content.
        """
        r = GZipMiddleware().process_response(self.req, self.stream_resp_unicode)
        self.assertEqual(
            self.decompress(b''.join(r)),
            b''.join(x.encode('utf-8') for x in self.sequence_unicode)
        )
        self.assertEqual(r.get('Content-Encoding'), 'gzip')
        self.assertFalse(r.has_header('Content-Length'))

    def test_compress_file_response(self):
        """
        Compression is performed on FileResponse.
        """
        with open(__file__, 'rb') as file1:
            file_resp = FileResponse(file1)
            file_resp['Content-Type'] = 'text/html; charset=UTF-8'
            r = GZipMiddleware().process_response(self.req, file_resp)
            with open(__file__, 'rb') as file2:
                self.assertEqual(self.decompress(b''.join(r)), file2.read())
            self.assertEqual(r.get('Content-Encoding'), 'gzip')
            self.assertIsNot(r.file_to_stream, file1)

    def test_compress_non_200_response(self):
        """
        Compression is performed on responses with a status other than 200
        (#10762).
        """
        self.resp.status_code = 404
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(self.decompress(r.content), self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), 'gzip')

    def test_no_compress_short_response(self):
        """
        Compression isn't performed on responses with short content.
        """
        self.resp.content = self.short_string
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.short_string)
        self.assertIsNone(r.get('Content-Encoding'))

    def test_no_compress_compressed_response(self):
        """
        Compression isn't performed on responses that are already compressed.
        """
        self.resp['Content-Encoding'] = 'deflate'
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.compressible_string)
        self.assertEqual(r.get('Content-Encoding'), 'deflate')

    def test_no_compress_incompressible_response(self):
        """
        Compression isn't performed on responses with incompressible content.
        """
        self.resp.content = self.incompressible_string
        r = GZipMiddleware().process_response(self.req, self.resp)
        self.assertEqual(r.content, self.incompressible_string)
        self.assertIsNone(r.get('Content-Encoding'))


@override_settings(USE_ETAGS=True)
class ETagGZipMiddlewareTest(SimpleTestCase):
    """
    Tests if the ETagMiddleware behaves correctly with GZipMiddleware.
    """
    rf = RequestFactory()
    compressible_string = b'a' * 500

    def test_compress_response(self):
        """
        ETag is changed after gzip compression is performed.
        """
        request = self.rf.get('/', HTTP_ACCEPT_ENCODING='gzip, deflate')
        response = GZipMiddleware().process_response(
            request,
            CommonMiddleware().process_response(request, HttpResponse(self.compressible_string))
        )
        gzip_etag = response.get('ETag')

        request = self.rf.get('/', HTTP_ACCEPT_ENCODING='')
        response = GZipMiddleware().process_response(
            request,
            CommonMiddleware().process_response(request, HttpResponse(self.compressible_string))
        )
        nogzip_etag = response.get('ETag')

        self.assertNotEqual(gzip_etag, nogzip_etag)
