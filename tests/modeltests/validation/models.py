from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

class ModelToValidate(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(default=datetime.now)
    number = models.IntegerField()

    def validate(self):
        super(ModelToValidate, self).validate()
        if self.number == 11:
            raise ValidationError('Invalid number supplied!')

class BaseModelValidationTests(TestCase):
    def test_missing_required_field_raises_error(self):
        mtv = ModelToValidate()
        self.assertRaises(ValidationError, mtv.clean)
    
    def test_with_correct_value_model_validates(self):
        mtv = ModelToValidate(number=10)
        self.assertEqual(None, mtv.clean())

    def test_custom_validate_method_is_called(self):
        mtv = ModelToValidate(number=11)
        self.assertRaises(ValidationError, mtv.clean)
