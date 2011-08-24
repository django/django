from django.contrib.localflavor.za.forms import ZAIDField, ZAPostCodeField

from django.test import SimpleTestCase


class ZALocalFlavorTests(SimpleTestCase):
    def test_ZAIDField(self):
        error_invalid = [u'Enter a valid South African ID number']
        valid = {
            '0002290001003': '0002290001003',
            '000229 0001 003': '0002290001003',
        }
        invalid = {
            '0102290001001': error_invalid,
            '811208': error_invalid,
            '0002290001004': error_invalid,
        }
        self.assertFieldOutput(ZAIDField, valid, invalid)

    def test_ZAPostCodeField(self):
        error_invalid = [u'Enter a valid South African postal code']
        valid = {
            '0000': '0000',
        }
        invalid = {
            'abcd': error_invalid,
            ' 7530': error_invalid,
        }
        self.assertFieldOutput(ZAPostCodeField, valid, invalid)
