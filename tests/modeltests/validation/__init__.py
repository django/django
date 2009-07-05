import unittest

from django.core.exceptions import ValidationError

class ValidationTestCase(unittest.TestCase):
    def assertFailsValidation(self, clean, failed_fields):
        self.assertRaises(ValidationError, clean)
        try:
            clean()
        except ValidationError, e:
            self.assertEquals(sorted(failed_fields), sorted(e.message_dict.keys()))


