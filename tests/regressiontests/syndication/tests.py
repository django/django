# -*- coding: utf-8 -*-

from django.test import TestCase
from django.test.client import Client

class SyndicationFeedTest(TestCase):
    def test_complex_base_url(self):
        """
        Tests that that the base url for a complex feed doesn't raise a 500
        exception.
        """
        c = Client()
        response = c.get('/syndication/feeds/complex/')
        self.assertEquals(response.status_code, 404)
