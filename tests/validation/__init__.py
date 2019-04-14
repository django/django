from django.core.exceptions import ValidationError


class ValidationAssertions:
    def assertFailsValidation(self, clean, failed_fields, **kwargs):
        with self.assertRaises(ValidationError) as cm:
            clean(**kwargs)
        self.assertEqual(sorted(failed_fields), sorted(cm.exception.message_dict))

    def assertFieldFailsValidationWithMessage(self, clean, field_name, message):
        with self.assertRaises(ValidationError) as cm:
            clean()
        self.assertIn(field_name, cm.exception.message_dict)
        self.assertEqual(message, cm.exception.message_dict[field_name])
