from . import ValidationTestCase
from .models import ModelToValidate


class TestModelsWithValidators(ValidationTestCase):
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
