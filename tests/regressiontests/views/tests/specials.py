# coding: utf-8
from django.test import TestCase

class URLHandling(TestCase):
    """
    Tests for URL handling in views and responses.
    """
    def test_iri_redirect(self):
        """
        Tests that redirecting to an IRI, requiring encoding before we use it
        in an HTTP response, is handled correctly.
        """
        response = self.client.get(u'/views/中文/')
        self.assertRedirects(response, "/views/%E4%B8%AD%E6%96%87/target/")

