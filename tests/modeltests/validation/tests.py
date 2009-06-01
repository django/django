from django.core.exceptions import ValidationError
from django.test import TestCase

from models import ModelToValidate

class BaseModelValidationTests(TestCase):
    def test_missing_required_field_raises_error(self):
        mtv = ModelToValidate()
        self.assertRaises(ValidationError, mtv.clean)
        try:
            mtv.clean()
        except ValidationError, e:
            self.assertEquals(['name', 'number'], sorted(e.message_dict.keys()))
    
    def test_with_correct_value_model_validates(self):
        mtv = ModelToValidate(number=10, name='Some Name')
        self.assertEqual(None, mtv.clean())

    def test_custom_validate_method_is_called(self):
        mtv = ModelToValidate(number=11)
        self.assertRaises(ValidationError, mtv.clean)

