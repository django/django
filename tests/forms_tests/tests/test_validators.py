import re
import types
from unittest import TestCase

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError


class TestFieldWithValidators(TestCase):
    def test_all_errors_get_reported(self):
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

        form = UserForm({
            'full_name': 'not int nor mail',
            'string': '2 is not correct',
            'ignore_case_string': "IgnORE Case strIng",
        })
        with self.assertRaises(ValidationError) as e:
            form.fields['full_name'].clean('not int nor mail')
        self.assertEqual(2, len(e.exception.messages))

        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['string'], ["Letters only."])
        self.assertEqual(form.errors['string'], ["Letters only."])

    def test_field_validators_can_be_any_iterable(self):
        class UserForm(forms.Form):
            full_name = forms.CharField(
                max_length=50,
                validators=(
                    validators.validate_integer,
                    validators.validate_email,
                )
            )

        form = UserForm({'full_name': 'not int nor mail'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['full_name'], ['Enter a valid integer.', 'Enter a valid email address.'])


class ValidatorCustomMessageTests(TestCase):
    def test_value_placeholder_with_char_field(self):
        cases = [
            (validators.MaxLengthValidator(10), 11 * 'x', 'max_length'),
            (validators.MinLengthValidator(10), 9 * 'x', 'min_length'),
        ]
        for validator, value, code in cases:
            if isinstance(validator, types.FunctionType):
                name = validator.__name__
            else:
                name = type(validator).__name__
            with self.subTest(name, value=value):
                class MyForm(forms.Form):
                    field = forms.CharField(
                        validators=[validator],
                        error_messages={code: '%(value)s'},
                    )

                form = MyForm({'field': value})
                self.assertIs(form.is_valid(), False)
                self.assertEqual(form.errors, {'field': [value]})

    def test_value_placeholder_with_integer_field(self):
        cases = [
            (validators.MaxValueValidator(0), 1, 'max_value'),
            (validators.MinValueValidator(0), -1, 'min_value'),
        ]
        for validator, value, code in cases:
            with self.subTest(type(validator).__name__, value=value):
                class MyForm(forms.Form):
                    field = forms.IntegerField(
                        validators=[validator],
                        error_messages={code: '%(value)s'},
                    )

                form = MyForm({'field': value})
                self.assertIs(form.is_valid(), False)
                self.assertEqual(form.errors, {'field': [str(value)]})
