import unittest

from django.test import ignore_warnings
from django.utils.deprecation import RemovedInDjango110Warning


class TestUtilsChecksums(unittest.TestCase):

    def check_output(self, function, value, output=None):
        """
        Check that function(value) equals output.  If output is None,
        check that function(value) equals value.
        """
        if output is None:
            output = value
        self.assertEqual(function(value), output)

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_luhn(self):
        from django.utils import checksums
        f = checksums.luhn
        items = (
            (4111111111111111, True), ('4111111111111111', True),
            (4222222222222, True), (378734493671000, True),
            (5424000000000015, True), (5555555555554444, True),
            (1008, True), ('0000001008', True), ('000000001008', True),
            (4012888888881881, True), (1234567890123456789012345678909, True),
            (4111111111211111, False), (42222222222224, False),
            (100, False), ('100', False), ('0000100', False),
            ('abc', False), (None, False), (object(), False),
        )
        for value, output in items:
            self.check_output(f, value, output)
