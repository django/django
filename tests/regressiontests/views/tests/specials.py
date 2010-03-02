# coding: utf-8
from django.test import TestCase

class URLHandling(TestCase):
    """
    Tests for URL handling in views and responses.
    """
    redirect_target = "/views/%E4%B8%AD%E6%96%87/target/"

    def test_combining_redirect(self):
        """
        Tests that redirecting to an IRI, requiring encoding before we use it
        in an HTTP response, is handled correctly. In this case the arg to
        HttpRedirect is ASCII but the current request path contains non-ASCII
        characters so this test ensures the creation of the full path with a
        base non-ASCII part is handled correctly.
        """
        response = self.client.get(u'/views/中文/')
        self.assertRedirects(response, self.redirect_target)

    def test_nonascii_redirect(self):
        """
        Tests that a non-ASCII argument to HttpRedirect is handled properly.
        """
        response = self.client.get('/views/nonascii_redirect/')
        self.assertRedirects(response, self.redirect_target)

    def test_permanent_nonascii_redirect(self):
        """
        Tests that a non-ASCII argument to HttpPermanentRedirect is handled
        properly.
        """
        response = self.client.get('/views/permanent_nonascii_redirect/')
        self.assertRedirects(response, self.redirect_target, status_code=301)

