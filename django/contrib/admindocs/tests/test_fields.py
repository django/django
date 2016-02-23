from __future__ import unicode_literals

import unittest

from django.contrib.admindocs import views
from django.db import models
from django.db.models import fields
from django.test import ignore_warnings
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.translation import ugettext as _


class CustomField(models.Field):
    description = "A custom field type"


class DescriptionLackingField(models.Field):
    pass


# Removedindjango20warning
class PercentDescriptionField(models.CharField):
    description = _('String (up to %(max_length)s)')


class TestFieldType(unittest.TestCase):
    def setUp(self):
        pass

    def test_field_name(self):
        self.assertRaises(
            AttributeError,
            views.get_readable_field_data_type, "NotAField"
        )

    def test_builtin_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(fields.BooleanField()),
            _('Boolean (Either True or False)')
        )

    def test_custom_fields(self):
        self.assertEqual(
            views.get_readable_field_data_type(CustomField()),
            'A custom field type'
        )
        self.assertEqual(
            views.get_readable_field_data_type(DescriptionLackingField()),
            _('Field of type: %(field_type)s') % {
                'field_type': 'DescriptionLackingField'
            }
        )

    def test_format_description(self):
        self.assertEqual(
            views.get_readable_field_data_type(models.CharField(max_length=100)),
            'String (up to 100)',
        )

    @ignore_warnings(category=RemovedInDjango20Warning)
    def test_format_description_percent_placeholder(self):
        self.assertEqual(
            views.get_readable_field_data_type(PercentDescriptionField(max_length=100)),
            'String (up to 100)',
        )
