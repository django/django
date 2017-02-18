# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase, override_settings


@override_settings(ROOT_URLCONF='view_tests.generic_urls')
class URLHandling(SimpleTestCase):
    """
    Tests for URL handling in views and responses.
    """
    redirect_target = "/%E4%B8%AD%E6%96%87/target/"

    def test_nonascii_redirect(self):
        """
        Tests that a non-ASCII argument to HttpRedirect is handled properly.
        """
        response = self.client.get('/nonascii_redirect/')
        self.assertRedirects(response, self.redirect_target)

    def test_permanent_nonascii_redirect(self):
        """
        Tests that a non-ASCII argument to HttpPermanentRedirect is handled
        properly.
        """
        response = self.client.get('/permanent_nonascii_redirect/')
        self.assertRedirects(response, self.redirect_target, status_code=301)
