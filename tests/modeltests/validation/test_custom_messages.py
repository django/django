from modeltests.validation import ValidationTestCase

from models import CustomMessagesModel
class CustomMessagesTest(ValidationTestCase):
    def test_custom_complex_validator_message(self):
        cmm = CustomMessagesModel(number=42, other=42)
        self.assertFieldFailsValidationWithMessage(cmm.clean, 'number', ['other != me'])

    def test_custom_simple_validator_message(self):
        cmm = CustomMessagesModel(number=12)
        self.assertFieldFailsValidationWithMessage(cmm.clean, 'number', ['AAARGH'])

    def test_custom_null_message(self):
        cmm = CustomMessagesModel()
        self.assertFieldFailsValidationWithMessage(cmm.clean, 'number', ['NULL'])

