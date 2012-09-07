# -*- encoding: utf-8 -*-
from __future__ import unicode_literals

from django.utils import unittest
from django.utils.encoding import force_bytes


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
