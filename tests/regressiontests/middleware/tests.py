# -*- coding: utf-8 -*-

import re

from django.conf import settings
from django.core import mail
from django.http import HttpRequest
from django.http import HttpResponse
from django.middleware.clickjacking import XFrameOptionsMiddleware
from django.middleware.common import CommonMiddleware
from django.middleware.http import ConditionalGetMiddleware
from django.test import TestCase


class CommonMiddlewareTest(TestCase):
    def setUp(self):
        self.append_slash = settings.APPEND_SLASH
        self.prepend_www = settings.PREPEND_WWW
        self.ignorable_404_urls = settings.IGNORABLE_404_URLS
        self.send_broken_email_links = settings.SEND_BROKEN_LINK_EMAILS

    def tearDown(self):
        settings.APPEND_SLASH = self.append_slash
        settings.PREPEND_WWW = self.prepend_www
        settings.IGNORABLE_404_URLS = self.ignorable_404_urls
        settings.SEND_BROKEN_LINK_EMAILS = self.send_broken_email_links

    def _get_request(self, path):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = request.path_info = "/middleware/%s" % path
        return request

    def test_append_slash_have_slash(self):
        """
        Tests that URLs with slashes go unmolested.
        """
        settings.APPEND_SLASH = True
        request = self._get_request('slash/')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_slashless_resource(self):
        """
        Tests that matches to explicit slashless URLs go unmolested.
        """
        settings.APPEND_SLASH = True
        request = self._get_request('noslash')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_slashless_unknown(self):
        """
        Tests that APPEND_SLASH doesn't redirect to unknown resources.
        """
        settings.APPEND_SLASH = True
        request = self._get_request('unknown')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_redirect(self):
        """
        Tests that APPEND_SLASH redirects slashless URLs to a valid pattern.
        """
        settings.APPEND_SLASH = True
        request = self._get_request('slash')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], 'http://testserver/middleware/slash/')

    def test_append_slash_no_redirect_on_POST_in_DEBUG(self):
        """
        Tests that while in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST to an URL which would normally be
        redirected to a slashed version.
        """
        settings.APPEND_SLASH = True
        settings.DEBUG = True
        request = self._get_request('slash')
        request.method = 'POST'
        self.assertRaises(
            RuntimeError,
            CommonMiddleware().process_request,
            request)
        try:
            CommonMiddleware().process_request(request)
        except RuntimeError, e:
            self.assertTrue('end in a slash' in str(e))
        settings.DEBUG = False

    def test_append_slash_disabled(self):
        """
        Tests disabling append slash functionality.
        """
        settings.APPEND_SLASH = False
        request = self._get_request('slash')
        self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_quoted(self):
        """
        Tests that URLs which require quoting are redirected to their slash
        version ok.
        """
        settings.APPEND_SLASH = True
        request = self._get_request('needsquoting#')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r['Location'],
            'http://testserver/middleware/needsquoting%23/')

    def test_prepend_www(self):
        settings.PREPEND_WWW = True
        settings.APPEND_SLASH = False
        request = self._get_request('path/')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(
            r['Location'],
            'http://www.testserver/middleware/path/')

    def test_prepend_www_append_slash_have_slash(self):
        settings.PREPEND_WWW = True
        settings.APPEND_SLASH = True
        request = self._get_request('slash/')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'],
                          'http://www.testserver/middleware/slash/')

    def test_prepend_www_append_slash_slashless(self):
        settings.PREPEND_WWW = True
        settings.APPEND_SLASH = True
        request = self._get_request('slash')
        r = CommonMiddleware().process_request(request)
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'],
                          'http://www.testserver/middleware/slash/')


    # The following tests examine expected behavior given a custom urlconf that
    # overrides the default one through the request object.

    def test_append_slash_have_slash_custom_urlconf(self):
      """
      Tests that URLs with slashes go unmolested.
      """
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/slash/')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_slashless_resource_custom_urlconf(self):
      """
      Tests that matches to explicit slashless URLs go unmolested.
      """
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/noslash')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_slashless_unknown_custom_urlconf(self):
      """
      Tests that APPEND_SLASH doesn't redirect to unknown resources.
      """
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/unknown')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_redirect_custom_urlconf(self):
      """
      Tests that APPEND_SLASH redirects slashless URLs to a valid pattern.
      """
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/slash')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      r = CommonMiddleware().process_request(request)
      self.assertFalse(r is None,
          "CommonMiddlware failed to return APPEND_SLASH redirect using request.urlconf")
      self.assertEqual(r.status_code, 301)
      self.assertEqual(r['Location'], 'http://testserver/middleware/customurlconf/slash/')

    def test_append_slash_no_redirect_on_POST_in_DEBUG_custom_urlconf(self):
      """
      Tests that while in debug mode, an exception is raised with a warning
      when a failed attempt is made to POST to an URL which would normally be
      redirected to a slashed version.
      """
      settings.APPEND_SLASH = True
      settings.DEBUG = True
      request = self._get_request('customurlconf/slash')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      request.method = 'POST'
      self.assertRaises(
          RuntimeError,
          CommonMiddleware().process_request,
          request)
      try:
          CommonMiddleware().process_request(request)
      except RuntimeError, e:
          self.assertTrue('end in a slash' in str(e))
      settings.DEBUG = False

    def test_append_slash_disabled_custom_urlconf(self):
      """
      Tests disabling append slash functionality.
      """
      settings.APPEND_SLASH = False
      request = self._get_request('customurlconf/slash')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      self.assertEqual(CommonMiddleware().process_request(request), None)

    def test_append_slash_quoted_custom_urlconf(self):
      """
      Tests that URLs which require quoting are redirected to their slash
      version ok.
      """
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/needsquoting#')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      r = CommonMiddleware().process_request(request)
      self.assertFalse(r is None,
          "CommonMiddlware failed to return APPEND_SLASH redirect using request.urlconf")
      self.assertEqual(r.status_code, 301)
      self.assertEqual(
          r['Location'],
          'http://testserver/middleware/customurlconf/needsquoting%23/')

    def test_prepend_www_custom_urlconf(self):
      settings.PREPEND_WWW = True
      settings.APPEND_SLASH = False
      request = self._get_request('customurlconf/path/')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      r = CommonMiddleware().process_request(request)
      self.assertEqual(r.status_code, 301)
      self.assertEqual(
          r['Location'],
          'http://www.testserver/middleware/customurlconf/path/')

    def test_prepend_www_append_slash_have_slash_custom_urlconf(self):
      settings.PREPEND_WWW = True
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/slash/')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      r = CommonMiddleware().process_request(request)
      self.assertEqual(r.status_code, 301)
      self.assertEqual(r['Location'],
                        'http://www.testserver/middleware/customurlconf/slash/')

    def test_prepend_www_append_slash_slashless_custom_urlconf(self):
      settings.PREPEND_WWW = True
      settings.APPEND_SLASH = True
      request = self._get_request('customurlconf/slash')
      request.urlconf = 'regressiontests.middleware.extra_urls'
      r = CommonMiddleware().process_request(request)
      self.assertEqual(r.status_code, 301)
      self.assertEqual(r['Location'],
                        'http://www.testserver/middleware/customurlconf/slash/')

    # Tests for the 404 error reporting via email

    def test_404_error_reporting(self):
        settings.IGNORABLE_404_URLS = (re.compile(r'foo'),)
        settings.SEND_BROKEN_LINK_EMAILS = True
        request = self._get_request('regular_url/that/does/not/exist')
        request.META['HTTP_REFERER'] = '/another/url/'
        response = self.client.get(request.path)
        CommonMiddleware().process_response(request, response)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Broken', mail.outbox[0].subject)

    def test_404_error_reporting_no_referer(self):
        settings.IGNORABLE_404_URLS = (re.compile(r'foo'),)
        settings.SEND_BROKEN_LINK_EMAILS = True
        request = self._get_request('regular_url/that/does/not/exist')
        response = self.client.get(request.path)
        CommonMiddleware().process_response(request, response)
        self.assertEqual(len(mail.outbox), 0)

    def test_404_error_reporting_ignored_url(self):
        settings.IGNORABLE_404_URLS = (re.compile(r'foo'),)
        settings.SEND_BROKEN_LINK_EMAILS = True
        request = self._get_request('foo_url/that/does/not/exist/either')
        request.META['HTTP_REFERER'] = '/another/url/'
        response = self.client.get(request.path)
        CommonMiddleware().process_response(request, response)
        self.assertEqual(len(mail.outbox), 0)


class ConditionalGetMiddlewareTest(TestCase):
    urls = 'regressiontests.middleware.cond_get_urls'
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
    def setUp(self):
        self.x_frame_options = settings.X_FRAME_OPTIONS

    def tearDown(self):
        settings.X_FRAME_OPTIONS = self.x_frame_options

    def test_same_origin(self):
        """
        Tests that the X_FRAME_OPTIONS setting can be set to SAMEORIGIN to
        have the middleware use that value for the HTTP header.
        """
        settings.X_FRAME_OPTIONS = 'SAMEORIGIN'
        r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        settings.X_FRAME_OPTIONS = 'sameorigin'
        r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_deny(self):
        """
        Tests that the X_FRAME_OPTIONS setting can be set to DENY to
        have the middleware use that value for the HTTP header.
        """
        settings.X_FRAME_OPTIONS = 'DENY'
        r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
        self.assertEqual(r['X-Frame-Options'], 'DENY')

        settings.X_FRAME_OPTIONS = 'deny'
        r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
        self.assertEqual(r['X-Frame-Options'], 'DENY')

    def test_defaults_sameorigin(self):
        """
        Tests that if the X_FRAME_OPTIONS setting is not set then it defaults
        to SAMEORIGIN.
        """
        del settings.X_FRAME_OPTIONS
        r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

    def test_dont_set_if_set(self):
        """
        Tests that if the X-Frame-Options header is already set then the
        middleware does not attempt to override it.
        """
        settings.X_FRAME_OPTIONS = 'DENY'
        response = HttpResponse()
        response['X-Frame-Options'] = 'SAMEORIGIN'
        r = XFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       response)
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')

        settings.X_FRAME_OPTIONS = 'SAMEORIGIN'
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
        settings.X_FRAME_OPTIONS = 'SAMEORIGIN'
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

        settings.X_FRAME_OPTIONS = 'DENY'
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

        settings.X_FRAME_OPTIONS = 'SAMEORIGIN'
        r = OtherXFrameOptionsMiddleware().process_response(HttpRequest(),
                                                       HttpResponse())
        self.assertEqual(r['X-Frame-Options'], 'DENY')
