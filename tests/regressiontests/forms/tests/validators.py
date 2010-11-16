from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.unittest import TestCase


class TestFieldWithValidators(TestCase):
    def test_all_errors_get_reported(self):
        field = forms.CharField(
            validators=[validators.validate_integer, validators.validate_email]
        )
        self.assertRaises(ValidationError, field.clean, 'not int nor mail')
        try:
            field.clean('not int nor mail')
        except ValidationError, e:
            self.assertEqual(2, len(e.messages))
