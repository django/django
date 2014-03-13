from __future__ import unicode_literals

from unittest import TestCase
import re

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError


class UserForm(forms.Form):
    full_name = forms.CharField(
        max_length=50,
        validators=[
            validators.validate_integer,
            validators.validate_email,
        ]
    )
    string = forms.CharField(
        max_length=50,
        validators=[
            validators.RegexValidator(
                regex='^[a-zA-Z]*$',
                message="Letters only.",
            )
        ]
    )
    ignore_case_string = forms.CharField(
        max_length=50,
        validators=[
            validators.RegexValidator(
                    regex='^[a-z]*$',
                    message="Letters only.",
                    flags=re.IGNORECASE,
                )
        ]

    )


class TestFieldWithValidators(TestCase):
    def test_all_errors_get_reported(self):
        form = UserForm({'full_name': 'not int nor mail', 'string': '2 is not correct', 'ignore_case_string': "IgnORE Case strIng"})
        self.assertRaises(ValidationError, form.fields['full_name'].clean, 'not int nor mail')

        try:
            form.fields['full_name'].clean('not int nor mail')
        except ValidationError as e:
            self.assertEqual(2, len(e.messages))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['string'], ["Letters only."])
        self.assertEqual(form.errors['string'], ["Letters only."])
