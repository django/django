from django.test import SimpleTestCase

from . import ValidationAssertions
from .models import ModelToValidate, MultipleValidators


class TestModelsWithValidators(ValidationAssertions, SimpleTestCase):
    def test_custom_validator_passes_for_correct_value(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=42,
                              f_with_iterable_of_validators=42)
        self.assertIsNone(mtv.full_clean())

    def test_custom_validator_raises_error_for_incorrect_value(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=12,
                              f_with_iterable_of_validators=42)
        self.assertFailsValidation(mtv.full_clean, ['f_with_custom_validator'])
        self.assertFieldFailsValidationWithMessage(
            mtv.full_clean,
            'f_with_custom_validator',
            ['This is not the answer to life, universe and everything!']
        )

    def test_field_validators_can_be_any_iterable(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=42,
                              f_with_iterable_of_validators=12)
        self.assertFailsValidation(mtv.full_clean, ['f_with_iterable_of_validators'])
        self.assertFieldFailsValidationWithMessage(
            mtv.full_clean,
            'f_with_iterable_of_validators',
            ['This is not the answer to life, universe and everything!']
        )


class TestMultipleValidators(ValidationAssertions, SimpleTestCase):
    def test_both_field_validator_run_successfully(self):
        instance = MultipleValidators(
            final_message='We apologize for the inconvenience'
        )
        self.assertIsNone(instance.full_clean())

    def test_firsts_field_validator_run_if_second_failed(self):
        instance = MultipleValidators(
            final_message='We not apologize for the inconvenience'
        )
        self.assertFieldFailsValidationWithMessage(
            instance.full_clean,
            'final_message',
            ['This is not God\'s final message to his creation']
        )

    def test_second_field_validator_not_run_if_first_failed(self):
        instance = MultipleValidators(
            final_message='42?'
        )
        self.assertFieldFailsValidationWithMessage(
            instance.full_clean,
            'final_message',
            ['Ensure this value has at least 34 characters (it has 3).']
        )
