# Tests for the contrib/localflavor/ TR form fields.

from django.contrib.localflavor.tr import forms as trforms
from django.core.exceptions import ValidationError
from django.utils.unittest import TestCase

class TRLocalFlavorTests(TestCase):
    def test_TRPostalCodeField(self):
        f = trforms.TRPostalCodeField()
        self.assertEqual(f.clean("06531"), "06531")
        self.assertEqual(f.clean("12345"), "12345")
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "a1234")
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "1234")
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "82123")
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "00123")
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX.",
            f.clean, "123456")
        self.assertRaisesRegexp(ValidationError,
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
        self.assertRaisesRegexp(ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "1234 233 1234")
        self.assertRaisesRegexp(ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "0312 233 12345")
        self.assertRaisesRegexp(ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "0312 233 123")
        self.assertRaisesRegexp(ValidationError,
            'Phone numbers must be in 0XXX XXX XXXX format.',
            f.clean, "0312 233 xxxx")

    def test_TRIdentificationNumberField(self):
        f = trforms.TRIdentificationNumberField()
        self.assertEqual(f.clean("10000000146"), "10000000146")
        self.assertRaisesRegexp(ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "10000000136")
        self.assertRaisesRegexp(ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "10000000147")
        self.assertRaisesRegexp(ValidationError,
            'Turkish Identification number must be 11 digits.',
            f.clean, "123456789")
        self.assertRaisesRegexp(ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "1000000014x")
        self.assertRaisesRegexp(ValidationError,
            'Enter a valid Turkish Identification number.',
            f.clean, "x0000000146")
