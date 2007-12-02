# -*- coding: utf-8 -*-

import unittest

from django.test import TestCase 
from django.http import HttpRequest
from django.middleware.common import CommonMiddleware
from django.conf import settings

class CommonMiddlewareTest(TestCase):
    def _get_request(self, path):
        request = HttpRequest()
        request.META = {
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
        }
        request.path = "/middleware/%s" % path
        return request

    def test_append_slash_have_slash(self):
        """
        tests that urls with slashes go unmolested
        """
        settings.APPEND_SLASH = True
        request = self._get_request('slash/')
        self.assertEquals(CommonMiddleware().process_request(request), None)

    def test_append_slash_slashless_resource(self):
        """
        tests that matches to explicit slashless urls go unmolested
        """
        settings.APPEND_SLASH = True
        request = self._get_request('noslash')
        self.assertEquals(CommonMiddleware().process_request(request), None)

    def test_append_slash_slashless_unknown(self):
        """
        tests that APPEND_SLASH doesn't redirect to unknown resources
        """
        settings.APPEND_SLASH = True
        request = self._get_request('unknown')
        self.assertEquals(CommonMiddleware().process_request(request), None)

    def test_append_slash_redirect(self):
        """
        tests that APPEND_SLASH redirects slashless urls to a valid pattern
        """
        settings.APPEND_SLASH = True
        request = self._get_request('slash')
        r = CommonMiddleware().process_request(request)
        self.assertEquals(r.status_code, 301)
        self.assertEquals(r['Location'], 'http://testserver/middleware/slash/')

    def test_append_slash_no_redirect_on_POST_in_DEBUG(self):
        """
        tests that while in debug mode, an exception is raised with a warning
        when a failed attempt is made to POST to an url which would normally be
        redirected to a slashed version
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

    def test_append_slash_disabled(self):
        """
        tests disabling append slash functionality
        """
        settings.APPEND_SLASH = False
        request = self._get_request('slash')
        self.assertEquals(CommonMiddleware().process_request(request), None)

    def test_append_slash_quoted(self):
        """
        tests that urls which require quoting are redirected to their slash
        version ok
        """
        settings.APPEND_SLASH = True
        request = self._get_request('needsquoting#')
        r = CommonMiddleware().process_request(request)
        self.assertEquals(r.status_code, 301)
        self.assertEquals(
            r['Location'],
            'http://testserver/middleware/needsquoting%23/')

