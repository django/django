# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import datetime

from django.utils import six
from django.utils.encoding import (force_bytes, force_text, filepath_to_uri,
        python_2_unicode_compatible)


class TestEncodingUtils(unittest.TestCase):
    def test_force_text_exception(self):
        """
        Check that broken __unicode__/__str__ actually raises an error.
        """
        class MyString(object):
            def __str__(self):
                return b'\xc3\xb6\xc3\xa4\xc3\xbc'

            __unicode__ = __str__

        # str(s) raises a TypeError on python 3 if the result is not a text type.
        # python 2 fails when it tries converting from str to unicode (via ASCII).
        exception = TypeError if six.PY3 else UnicodeError
        self.assertRaises(exception, force_text, MyString())

    def test_force_bytes_exception(self):
        """
        Test that force_bytes knows how to convert to bytes an exception
        containing non-ASCII characters in its args.
        """
        error_msg = "This is an exception, voilà"
        exc = ValueError(error_msg)
        result = force_bytes(exc)
        self.assertEqual(result, error_msg.encode('utf-8'))

    def test_force_bytes_strings_only(self):
        today = datetime.date.today()
        self.assertEqual(force_bytes(today, strings_only=True), today)

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
