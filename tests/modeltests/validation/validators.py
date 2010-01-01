from unittest import TestCase

from modeltests.validation import ValidationTestCase
from models import *


class TestModelsWithValidators(ValidationTestCase):
    def test_custom_validator_passes_for_correct_value(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=42)
        self.assertEqual(None, mtv.full_validate())

    def test_custom_validator_raises_error_for_incorrect_value(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=12)
        self.assertFailsValidation(mtv.full_validate, ['f_with_custom_validator'])
        self.assertFieldFailsValidationWithMessage(
                mtv.full_validate,
                'f_with_custom_validator',
                [u'This is not the answer to life, universe and everything!']
            )

    def test_custom_complex_validator_raises_error_for_incorrect_value(self):
        mtv = ModelToValidate(number=42, name='Some Name', f_with_custom_validator=42)
        self.assertFailsValidation(mtv.full_validate, ['f_with_custom_validator'])
        self.assertFieldFailsValidationWithMessage(
                mtv.full_validate,
                'f_with_custom_validator',
                [u"Must not equal to 'number''s value"]
            )

    def test_complex_validator_isnt_run_if_field_doesnt_validate(self):
        mtv = ModelToValidate(number=32, name='Some Name', f_with_custom_validator=32)
        self.assertFieldFailsValidationWithMessage(
                mtv.full_validate,
                'f_with_custom_validator',
                [u'This is not the answer to life, universe and everything!']
            )
