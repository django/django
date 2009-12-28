import unittest
import fields
from django.contrib.admindocs import views
from django.db.models import fields as builtin_fields


class TestFieldType(unittest.TestCase):
    def setUp(self):
        pass

    def test_field_name(self):
        self.assertRaises(AttributeError,
            views.get_readable_field_data_type, "NotAField"
        )

    def test_builtin_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(builtin_fields.BooleanField()),
            u'Boolean (Either True or False)'
        )

    def test_custom_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(fields.CustomField()),
            u'A custom field type'
        )
        self.assertEqual(
            views.get_readable_field_data_type(fields.DescriptionLackingField()),
            u'Field of type: DescriptionLackingField'
        )
