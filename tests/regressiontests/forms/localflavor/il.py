from django.contrib.localflavor.il.forms import (ILPostalCodeField,
    ILIDNumberField)
from django.core.exceptions import ValidationError
from django.utils.unittest import TestCase


class IsraelLocalFlavorTests(TestCase):
    def test_postal_code_field(self):
        f = ILPostalCodeField()
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX",
            f.clean, "84545x"
        )
        self.assertEqual(f.clean("69973"), "69973")
        self.assertEqual(f.clean("699 73"), "69973")
        self.assertEqual(f.clean("12345"), "12345")
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX",
            f.clean, "123456"
        )
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX",
            f.clean, "1234"
        )
        self.assertRaisesRegexp(ValidationError,
            "Enter a postal code in the format XXXXX",
            f.clean, "123 4"
        )
        self.assertRaises(ValidationError, f.clean, None)

    def test_id_number_field(self):
        f = ILIDNumberField()
        self.assertEqual(f.clean("3933742-3"), "39337423")
        self.assertEqual(f.clean("39337423"), "39337423")
        self.assertEqual(f.clean("039337423"), "039337423")
        self.assertEqual(f.clean("03933742-3"), "039337423")
        self.assertEqual(f.clean("0091"), "0091")
        self.assertRaisesRegexp(ValidationError,
            "Enter a valid ID number.",
            f.clean, "123456789"
        )
        self.assertRaisesRegexp(ValidationError,
            "Enter a valid ID number.",
            f.clean, "12345678-9"
        )
        self.assertRaisesRegexp(ValidationError,
            "Enter a valid ID number.",
            f.clean, "012346578"
        )
        self.assertRaisesRegexp(ValidationError,
            "Enter a valid ID number.",
            f.clean, "012346578-"
        )
        self.assertRaisesRegexp(ValidationError,
            "Enter a valid ID number.",
            f.clean, "0001"
        )
