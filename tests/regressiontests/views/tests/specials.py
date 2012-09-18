# coding: utf-8
from __future__ import unicode_literals

from django.test import TestCase


class URLHandling(TestCase):
    """
    Tests for URL handling in views and responses.
    """
    urls = 'regressiontests.views.generic_urls'
    redirect_target = "/%E4%B8%AD%E6%96%87/target/"

    def test_combining_redirect(self):
        """
        Tests that redirecting to an IRI, requiring encoding before we use it
        in an HTTP response, is handled correctly. In this case the arg to
        HttpRedirect is ASCII but the current request path contains non-ASCII
        characters so this test ensures the creation of the full path with a
        base non-ASCII part is handled correctly.
        """
        response = self.client.get('/中文/')
        self.assertRedirects(response, self.redirect_target)

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

    def test_overlapping_urls_reverse(self):
        from django.core import urlresolvers
        url = urlresolvers.reverse('overlapping_view1', kwargs={'title':'sometitle'})
        self.assertEqual(url, '/overlapping_view/sometitle/')
        url = urlresolvers.reverse('overlapping_view2', kwargs={'author':'someauthor'})
        self.assertEqual(url, '/overlapping_view/someauthor/')

    def test_overlapping_urls_resolve(self):
        response = self.client.get('/overlapping_view/sometitle/')
        self.assertContains(response, 'overlapping_view2')

    def test_overlapping_urls_not_resolve(self):
        response = self.client.get('/no_overlapping_view/sometitle/')
        self.assertEqual(response.status_code, 404)
