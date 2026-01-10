from django.contrib.admin.utils import label_for_field
from django.db import models
from django.test import SimpleTestCase


class Ticket27752Model(models.Model):
    class Meta:
        app_label = "admin_utils"
        verbose_name = "Test Model"

    def __str__(self):
        return "instance"


class Ticket27752Tests(SimpleTestCase):
    def test_label_for_field_str_method(self):
        """
        Regression test for Ticket #27752.
        label_for_field should return the model's
        __str__ method (not the str type)
        when name is '__str__', allowing attributes like
        admin_order_field to be detected.
        """

        Ticket27752Model.__str__.admin_order_field = "dummy_field"
        label, attr = label_for_field("__str__", Ticket27752Model, return_attr=True)
        self.assertNotEqual(attr, str, "Should not return the 'str' class")
        self.assertEqual(attr, Ticket27752Model.__str__)
        self.assertTrue(hasattr(attr, "admin_order_field"))
        self.assertEqual(attr.admin_order_field, "dummy_field")
