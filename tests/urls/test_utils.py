from __future__ import unicode_literals

from django.core.urls import URL
from django.test import SimpleTestCase


class URLTests(SimpleTestCase):
    def test_path(self):
        self.assertEqual(URL().path, '/')
        self.assertEqual(URL(script_name='/').path, '/')
        self.assertEqual(URL(path_info='/').path, '/')
        self.assertEqual(URL(script_name='/test/', path_info='/path/').path, '/test/path/')
        self.assertEqual(URL(path_info='//').path, '//')

