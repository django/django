from __future__ import absolute_import

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
            _(u'Boolean (Either True or False)')
        )

    def test_custom_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(fields.CustomField()),
            _(u'A custom field type')
        )
        self.assertEqual(
            views.get_readable_field_data_type(fields.DescriptionLackingField()),
            _(u'Field of type: %(field_type)s') % {
                'field_type': 'DescriptionLackingField'
            }
        )
