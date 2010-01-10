import unittest

from django.db import models

from django.contrib import admin
from django.contrib.admin.util import display_for_field, label_for_field
from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE

from models import Article



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

    def test_label_for_field(self):
        """
        Tests for label_for_field
        """
        self.assertEquals(
            label_for_field("title", Article),
            "title"
        )
        self.assertEquals(
            label_for_field("title2", Article),
            "another name"
        )
        self.assertEquals(
            label_for_field("title2", Article, return_attr=True), 
            ("another name", None)
        )

        self.assertEquals(
            label_for_field("__unicode__", Article),
            "article"
        )
        self.assertEquals(
            label_for_field("__str__", Article),
            "article"
        )

        self.assertRaises(
            AttributeError,
            lambda: label_for_field("unknown", Article)
        )

        def test_callable(obj):
            return "nothing"
        self.assertEquals(
            label_for_field(test_callable, Article),
            "test_callable"
        )
        self.assertEquals(
            label_for_field(test_callable, Article, return_attr=True),
            ("test_callable", test_callable)
        )

        self.assertEquals(
            label_for_field("test_from_model", Article),
            "test_from_model"
        )
        self.assertEquals(
            label_for_field("test_from_model", Article, return_attr=True),
            ("test_from_model", Article.test_from_model)
        )
        self.assertEquals(
            label_for_field("test_from_model_with_override", Article),
            "not what you expect"
        )

        self.assertEquals(
            label_for_field(lambda x: "nothing", Article),
            "--"
        )

        class MockModelAdmin(object):
            def test_from_model(self, obj):
                return "nothing"
            test_from_model.short_description = "not really the model"
        self.assertEquals(
            label_for_field("test_from_model", Article, model_admin=MockModelAdmin),
            "not really the model"
        )
        self.assertEquals(
            label_for_field("test_from_model", Article,
                model_admin = MockModelAdmin,
                return_attr = True
            ),
            ("not really the model", MockModelAdmin.test_from_model)
        )
