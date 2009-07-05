from unittest import TestCase

from modeltests.validation import ValidationTestCase
from models import *

class TestModelsWithValidators(ValidationTestCase):
    def test_custom_validator_passes_for_correct_value(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=42)
        self.assertEqual(None, mtv.clean())

    def test_custom_validator_raises_error_for_incorrect_value(self):
        mtv = ModelToValidate(number=10, name='Some Name', f_with_custom_validator=12)
        self.assertFailsValidation(mtv.clean, ['f_with_custom_validator'])

