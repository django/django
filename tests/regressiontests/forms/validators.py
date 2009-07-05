from unittest import TestCase

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError

class AlwaysFailingValidator(validators.ComplexValidator):
    def __call__(self, value, all_values={}, obj=None):
        raise ValidationError('AlwaysFailingValidator')

class TestFieldWithValidators(TestCase):
    def test_all_errors_get_reported(self):
        field = forms.CharField(
                validators=[validators.validate_integer, validators.validate_email,]
            )
        self.assertRaises(ValidationError, field.clean, 'not int nor mail')
        try:
            field.clean('not int nor mail')
        except ValidationError, e:
            self.assertEqual(2, len(e.messages))

class TestFormWithValidators(TestCase):
    def test_all_complex_validators_get_run_even_if_they_fail(self):
        class MyForm(forms.Form):
            validator_field = forms.CharField(
                    validators=[
                        AlwaysFailingValidator(),
                        AlwaysFailingValidator(),
                    ]
                )
        form = MyForm({'validator_field': 'some value'})
        self.assertFalse(form.is_valid())
        self.assertEqual(['validator_field'], form.errors.keys())
        self.assertEqual(['AlwaysFailingValidator', 'AlwaysFailingValidator'], form.errors['validator_field'])
