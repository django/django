import unittest

from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db import models

from modeltests.validation import ValidationTestCase
from models import *

from validators import TestModelsWithValidators
from test_unique import GetUniqueCheckTests

class BaseModelValidationTests(ValidationTestCase):

    def test_missing_required_field_raises_error(self):
        mtv = ModelToValidate(f_with_custom_validator=42)
        self.assertFailsValidation(mtv.clean, ['name', 'number'])
    
    def test_with_correct_value_model_validates(self):
        mtv = ModelToValidate(number=10, name='Some Name')
        self.assertEqual(None, mtv.clean())

    def test_custom_validate_method_is_called(self):
        mtv = ModelToValidate(number=11)
        self.assertFailsValidation(mtv.clean, [NON_FIELD_ERRORS, 'name'])

    def test_wrong_FK_value_raises_error(self):
        mtv=ModelToValidate(number=10, name='Some Name', parent_id=3)
        self.assertFailsValidation(mtv.clean, ['parent'])

    def test_correct_FK_value_cleans(self):
        parent = ModelToValidate.objects.create(number=10, name='Some Name')
        mtv=ModelToValidate(number=10, name='Some Name', parent_id=parent.pk)
        self.assertEqual(None, mtv.clean())

    def test_wrong_email_value_raises_error(self):
        mtv = ModelToValidate(number=10, name='Some Name', email='not-an-email')
        self.assertFailsValidation(mtv.clean, ['email'])

    def test_correct_email_value_passes(self):
        mtv = ModelToValidate(number=10, name='Some Name', email='valid@email.com')
        self.assertEqual(None, mtv.clean())

    def test_text_greater_that_charfields_max_length_eaises_erros(self):
        mtv = ModelToValidate(number=10, name='Some Name'*100)
        self.assertFailsValidation(mtv.clean, ['name',])

