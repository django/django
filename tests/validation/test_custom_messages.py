from django.test import SimpleTestCase

from . import ValidationAssertions
from .models import CustomMessagesModel


class CustomMessagesTests(ValidationAssertions, SimpleTestCase):
    def test_custom_simple_validator_message(self):
        cmm = CustomMessagesModel(number=12)
        self.assertFieldFailsValidationWithMessage(cmm.full_clean, "number", ["AAARGH"])

    def test_custom_null_message(self):
        cmm = CustomMessagesModel()
        self.assertFieldFailsValidationWithMessage(cmm.full_clean, "number", ["NULL"])
