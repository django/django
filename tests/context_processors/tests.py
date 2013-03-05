"""
Tests for Django's bundled context processors.
"""
from django.test import TestCase


class RequestContextProcessorTests(TestCase):
    """
    Tests for the ``django.core.context_processors.request`` processor.
    """

    urls = 'context_processors.urls'

    def test_request_attributes(self):
        """
        Test that the request object is available in the template and that its
        attributes can't be overridden by GET and POST parameters (#3828).
        """
        url = '/request_attrs/'
        # We should have the request object in the template.
        response = self.client.get(url)
        self.assertContains(response, 'Have request')
        # Test is_secure.
        response = self.client.get(url)
        self.assertContains(response, 'Not secure')
        response = self.client.get(url, {'is_secure': 'blah'})
        self.assertContains(response, 'Not secure')
        response = self.client.post(url, {'is_secure': 'blah'})
        self.assertContains(response, 'Not secure')
        # Test path.
        response = self.client.get(url)
        self.assertContains(response, url)
        response = self.client.get(url, {'path': '/blah/'})
        self.assertContains(response, url)
        response = self.client.post(url, {'path': '/blah/'})
        self.assertContains(response, url)

