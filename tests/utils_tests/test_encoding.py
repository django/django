# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import unittest
from django.utils.encoding import force_bytes, filepath_to_uri, python_2_unicode_compatible
from django.utils import six


class TestEncodingUtils(unittest.TestCase):
    def test_force_bytes_exception(self):
        """
        Test that force_bytes knows how to convert to bytes an exception
        containing non-ASCII characters in its args.
        """
        error_msg = "This is an exception, voilà"
        exc = ValueError(error_msg)
        result = force_bytes(exc)
        self.assertEqual(result, error_msg.encode('utf-8'))

    def test_filepath_to_uri(self):
        self.assertEqual(filepath_to_uri('upload\\чубака.mp4'),
            'upload/%D1%87%D1%83%D0%B1%D0%B0%D0%BA%D0%B0.mp4')
        self.assertEqual(filepath_to_uri('upload\\чубака.mp4'.encode('utf-8')),
            'upload/%D1%87%D1%83%D0%B1%D0%B0%D0%BA%D0%B0.mp4')

    @unittest.skipIf(six.PY3, "tests a class not defining __str__ under Python 2")
    def test_decorated_class_without_str(self):
        with self.assertRaises(ValueError):
            @python_2_unicode_compatible
            class NoStr(object):
                pass
