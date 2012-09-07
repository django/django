# Tests for the contrib/localflavor/ TR form fields.

from django.contrib.localflavor.tr import forms as trforms
from django.core.exceptions import ValidationError
from django.utils import six
from django.utils.unittest import TestCase


class TRLocalFlavorTests(TestCase):
    def test_TRPostalCodeField(self):
        f = trforms.TRPostalCodeField()
        self.assertEqual(f.clean("06531"), "06531")
        self.assertEqual(f.clean("12345"), "12345")
        six.assertRaisesRegex(self, ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "a1234")
        six.assertRaisesRegex(self, ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "1234")
        six.assertRaisesRegex(self, ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "82123")
        six.assertRaisesRegex(self, ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "00123")
        six.assertRaisesRegex(self, ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "123456")
        six.assertRaisesRegex(self, ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "12 34")
        self.assertRaises(ValidationError, f.clean, None)

    def test_TRPhoneNumberField(self):
        f = trforms.TRPhoneNumberField()
        self.assertEqual(f.clean("312 455 56 78"), "3124555678")
        self.assertEqual(f.clean("312 4555678"), "3124555678")
        self.assertEqual(f.clean("3124555678"), "3124555678")
        self.assertEqual(f.clean("0312 455 5678"), "3124555678")
        self.assertEqual(f.clean("0 312 455 5678"), "3124555678")
        self.assertEqual(f.clean("0 (312) 455 5678"), "3124555678")
        self.assertEqual(f.clean("+90 312 455 4567"), "3124554567")
        self.assertEqual(f.clean("+90 312 455 45 67"), "3124554567")
        self.assertEqual(f.clean("+90 (312) 4554567"), "3124554567")
        six.assertRaisesRegex(self, ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "1234 233 1234")
        six.assertRaisesRegex(self, ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "0312 233 12345")
        six.assertRaisesRegex(self, ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "0312 233 123")
        six.assertRaisesRegex(self, ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "0312 233 xxxx")

    def test_TRIdentificationNumberField(self):
        f = trforms.TRIdentificationNumberField()
        self.assertEqual(f.clean("10000000146"), "10000000146")
        six.assertRaisesRegex(self, ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "10000000136")
        six.assertRaisesRegex(self, ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "10000000147")
        six.assertRaisesRegex(self, ValidationError,
            'Turkish Identification number must be 11 digits.',
            f.clean, "123456789")
        six.assertRaisesRegex(self, ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "1000000014x")
        six.assertRaisesRegex(self, ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "x0000000146")
