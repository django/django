from __future__ import absolute_import, unicode_literals

from django.contrib.admindocs import views
from django.db.models import fields as builtin_fields
from django.utils import unittest
from django.utils.translation import ugettext as _

from . import fields


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
            _('Boolean (Either True or False)')
        )

    def test_custom_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(fields.CustomField()),
            'A custom field type'
        )
        self.assertEqual(
            views.get_readable_field_data_type(fields.DescriptionLackingField()),
            _('Field of type: %(field_type)s') % {
                'field_type': 'DescriptionLackingField'
            }
        )
