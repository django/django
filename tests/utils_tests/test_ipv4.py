from __future__ import unicode_literals

import unittest

from django.utils.ipv4 import clean_ipv4_address


class TestUtilsIPv4(unittest.TestCase):

    def test_cleanes_plain_address(self):
        self.assertEqual(clean_ipv4_address('127.0.00.010'), '127.0.0.10')
        self.assertEqual(clean_ipv4_address('127.0.00.001'), '127.0.0.1')
