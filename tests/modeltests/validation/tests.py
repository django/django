from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.test import TestCase
from django.db import models

from models import *

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
        try:
            mtv.clean()
        except ValidationError, e:
            self.assertEquals(sorted([NON_FIELD_ERRORS, 'name']), sorted(e.message_dict.keys()))

    def test_wrong_FK_value_raises_error(self):
        mtv=ModelToValidate(number=10, name='Some Name', parent_id=3)
        self.assertRaises(ValidationError, mtv.clean)
        try:
            mtv.clean()
        except ValidationError, e:
            self.assertEquals(['parent'], e.message_dict.keys())

    def test_correct_FK_value_cleans(self):
        parent = ModelToValidate.objects.create(number=10, name='Some Name')
        mtv=ModelToValidate(number=10, name='Some Name', parent_id=parent.pk)
        self.assertEqual(None, mtv.clean())

class GetUniqueCheckTests(TestCase):
    def test_unique_fields_get_collected(self):
        m = UniqueFieldsModel()
        self.assertEqual(([('id',), ('unique_charfield',), ('unique_integerfield',)], []), m._get_unique_checks())

    def test_unique_together_gets_picked_up(self):
        m = UniqueTogetherModel()
        self.assertEqual(([('ifield', 'cfield',),('ifield', 'efield'), ('id',), ], []), m._get_unique_checks())

    def test_primary_key_is_considered_unique(self):
        m = CustomPKModel()
        self.assertEqual(([('my_pk_field',)], []), m._get_unique_checks())

    def test_unique_for_date_gets_picked_up(self):
        m = UniqueForDateModel()
        self.assertEqual((
                [('id',)],
                [('date', 'count', 'start_date'), ('year', 'count', 'end_date'), ('month', 'order', 'end_date')]
            ), m._get_unique_checks()
        )


