import unittest

from django.db import models

from django.contrib import admin
from django.contrib.admin.util import display_for_field
from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE



class UtilTests(unittest.TestCase):
    def test_null_display_for_field(self):
        """
        Regression test for #12550: display_for_field should handle None
        value.
        """
        display_value = display_for_field(None, models.CharField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

        display_value = display_for_field(None, models.CharField(
            choices=(
                (None, "test_none"),
            )
        ))
        self.assertEqual(display_value, "test_none")

        display_value = display_for_field(None, models.DateField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

        display_value = display_for_field(None, models.TimeField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

        display_value = display_for_field(None, models.NullBooleanField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

        display_value = display_for_field(None, models.DecimalField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

        display_value = display_for_field(None, models.FloatField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)
