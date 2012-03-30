from django.core.exceptions import ValidationError
from django.test import TestCase


class ValidationTestCase(TestCase):
    def assertFailsValidation(self, clean, failed_fields):
        with self.assertRaises(ValidationError) as cm:
            clean()
        self.assertEqual(sorted(failed_fields), sorted(cm.exception.message_dict))

    def assertFieldFailsValidationWithMessage(self, clean, field_name, message):
        with self.assertRaises(ValidationError) as cm:
            clean()
        self.assertIn(field_name, cm.exception.message_dict)
        self.assertEqual(message, cm.exception.message_dict[field_name])

