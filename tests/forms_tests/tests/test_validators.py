from __future__ import unicode_literals

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.unittest import TestCase


class UserForm(forms.Form):
    full_name = forms.CharField(
        max_length = 50,
        validators = [
            validators.validate_integer,
            validators.validate_email,
        ]
    )
    string = forms.CharField(
        max_length = 50,
        validators = [
            validators.RegexValidator(
                regex='^[a-zA-Z]*$',
                message="Letters only.",
            )
        ]
    )


class TestFieldWithValidators(TestCase):
    def test_all_errors_get_reported(self):
        form = UserForm({'full_name': 'not int nor mail', 'string': '2 is not correct'})
        self.assertRaises(ValidationError, form.fields['full_name'].clean, 'not int nor mail')

        try:
            form.fields['full_name'].clean('not int nor mail')
        except ValidationError as e:
            self.assertEqual(2, len(e.messages))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['string'], ["Letters only."])
