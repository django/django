from __future__ import unicode_literals

from django.test import SimpleTestCase
from django.utils.glob import glob_escape


class TestUtilsGlob(SimpleTestCase):
    def test_glob_escape(self):
        filename = '/my/file?/name[with special chars*'
        expected = '/my/file[?]/name[[]with special chars[*]'
        filename_b = b'/my/file?/name[with special chars*'
        expected_b = b'/my/file[?]/name[[]with special chars[*]'

        self.assertEqual(glob_escape(filename), expected)
        self.assertEqual(glob_escape(filename_b), expected_b)
