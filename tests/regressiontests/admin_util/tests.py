from __future__ import absolute_import

from datetime import datetime

from django.conf import settings
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.util import (display_for_field, label_for_field,
    lookup_field, NestedObjects)
from django.contrib.admin.views.main import EMPTY_CHANGELIST_VALUE
from django.contrib.sites.models import Site
from django.db import models, DEFAULT_DB_ALIAS
from django import forms
from django.test import TestCase
from django.utils import unittest
from django.utils.formats import localize
from django.utils.safestring import mark_safe

from .models import Article, Count, Event, Location


class NestedObjectsTests(TestCase):
    """
    Tests for ``NestedObject`` utility collection.

    """
    def setUp(self):
        self.n = NestedObjects(using=DEFAULT_DB_ALIAS)
        self.objs = [Count.objects.create(num=i) for i in range(5)]

    def _check(self, target):
        self.assertEqual(self.n.nested(lambda obj: obj.num), target)

    def _connect(self, i, j):
        self.objs[i].parent = self.objs[j]
        self.objs[i].save()

    def _collect(self, *indices):
        self.n.collect([self.objs[i] for i in indices])

    def test_unrelated_roots(self):
        self._connect(2, 1)
        self._collect(0)
        self._collect(1)
        self._check([0, 1, [2]])

    def test_siblings(self):
        self._connect(1, 0)
        self._connect(2, 0)
        self._collect(0)
        self._check([0, [1, 2]])

    def test_non_added_parent(self):
        self._connect(0, 1)
        self._collect(0)
        self._check([0])

    def test_cyclic(self):
        self._connect(0, 2)
        self._connect(1, 0)
        self._connect(2, 1)
        self._collect(0)
        self._check([0, [1, [2]]])

    def test_queries(self):
        self._connect(1, 0)
        self._connect(2, 0)
        # 1 query to fetch all children of 0 (1 and 2)
        # 1 query to fetch all children of 1 and 2 (none)
        # Should not require additional queries to populate the nested graph.
        self.assertNumQueries(2, self._collect, 0)

class UtilTests(unittest.TestCase):
    def test_values_from_lookup_field(self):
        """
        Regression test for #12654: lookup_field
        """
        SITE_NAME = 'example.com'
        TITLE_TEXT = 'Some title'
        CREATED_DATE = datetime.min
        ADMIN_METHOD = 'admin method'
        SIMPLE_FUNCTION = 'function'
        INSTANCE_ATTRIBUTE = 'attr'

        class MockModelAdmin(object):
            def get_admin_value(self, obj):
                return ADMIN_METHOD

        simple_function = lambda obj: SIMPLE_FUNCTION

        article = Article(
            site=Site(domain=SITE_NAME),
            title=TITLE_TEXT,
            created=CREATED_DATE,
        )
        article.non_field = INSTANCE_ATTRIBUTE

        verifications = (
            ('site', SITE_NAME),
            ('created', localize(CREATED_DATE)),
            ('title', TITLE_TEXT),
            ('get_admin_value', ADMIN_METHOD),
            (simple_function, SIMPLE_FUNCTION),
            ('test_from_model', article.test_from_model()),
            ('non_field', INSTANCE_ATTRIBUTE)
        )

        mock_admin = MockModelAdmin()
        for name, value in verifications:
            field, attr, resolved_value = lookup_field(name, article, mock_admin)

            if field is not None:
                resolved_value = display_for_field(resolved_value, field)

            self.assertEqual(value, resolved_value)

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

        # Regression test for #13071: NullBooleanField has special
        # handling.
        display_value = display_for_field(None, models.NullBooleanField())
        expected = u'<img src="%sadmin/img/icon-unknown.gif" alt="None" />' % settings.STATIC_URL
        self.assertEqual(display_value, expected)

        display_value = display_for_field(None, models.DecimalField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

        display_value = display_for_field(None, models.FloatField())
        self.assertEqual(display_value, EMPTY_CHANGELIST_VALUE)

    def test_label_for_field(self):
        """
        Tests for label_for_field
        """
        self.assertEqual(
            label_for_field("title", Article),
            "title"
        )
        self.assertEqual(
            label_for_field("title2", Article),
            "another name"
        )
        self.assertEqual(
            label_for_field("title2", Article, return_attr=True),
            ("another name", None)
        )

        self.assertEqual(
            label_for_field("__unicode__", Article),
            "article"
        )
        self.assertEqual(
            label_for_field("__str__", Article),
            "article"
        )

        self.assertRaises(
            AttributeError,
            lambda: label_for_field("unknown", Article)
        )

        def test_callable(obj):
            return "nothing"
        self.assertEqual(
            label_for_field(test_callable, Article),
            "Test callable"
        )
        self.assertEqual(
            label_for_field(test_callable, Article, return_attr=True),
            ("Test callable", test_callable)
        )

        self.assertEqual(
            label_for_field("test_from_model", Article),
            "Test from model"
        )
        self.assertEqual(
            label_for_field("test_from_model", Article, return_attr=True),
            ("Test from model", Article.test_from_model)
        )
        self.assertEqual(
            label_for_field("test_from_model_with_override", Article),
            "not What you Expect"
        )

        self.assertEqual(
            label_for_field(lambda x: "nothing", Article),
            "--"
        )

        class MockModelAdmin(object):
            def test_from_model(self, obj):
                return "nothing"
            test_from_model.short_description = "not Really the Model"

        self.assertEqual(
            label_for_field("test_from_model", Article, model_admin=MockModelAdmin),
            "not Really the Model"
        )
        self.assertEqual(
            label_for_field("test_from_model", Article,
                model_admin = MockModelAdmin,
                return_attr = True
            ),
            ("not Really the Model", MockModelAdmin.test_from_model)
        )

    def test_related_name(self):
        """
        Regression test for #13963
        """
        self.assertEqual(
            label_for_field('location', Event, return_attr=True),
            ('location', None),
        )
        self.assertEqual(
            label_for_field('event', Location, return_attr=True),
            ('awesome event', None),
        )
        self.assertEqual(
            label_for_field('guest', Event, return_attr=True),
            ('awesome guest', None),
        )

    def test_logentry_unicode(self):
        """
        Regression test for #15661
        """
        log_entry = admin.models.LogEntry()

        log_entry.action_flag = admin.models.ADDITION
        self.assertTrue(
            unicode(log_entry).startswith('Added ')
        )

        log_entry.action_flag = admin.models.CHANGE
        self.assertTrue(
            unicode(log_entry).startswith('Changed ')
        )

        log_entry.action_flag = admin.models.DELETION
        self.assertTrue(
            unicode(log_entry).startswith('Deleted ')
        )

    def test_safestring_in_field_label(self):
        # safestring should not be escaped
        class MyForm(forms.Form):
            text = forms.CharField(label=mark_safe('<i>text</i>'))
            cb   = forms.BooleanField(label=mark_safe('<i>cb</i>'))

        form = MyForm()
        self.assertEqual(helpers.AdminField(form, 'text', is_first=False).label_tag(),
                         '<label for="id_text" class="required inline"><i>text</i>:</label>')
        self.assertEqual(helpers.AdminField(form, 'cb', is_first=False).label_tag(),
                         '<label for="id_cb" class="vCheckboxLabel required inline"><i>cb</i></label>')

        # normal strings needs to be escaped
        class MyForm(forms.Form):
            text = forms.CharField(label='&text')
            cb   = forms.BooleanField(label='&cb')

        form = MyForm()
        self.assertEqual(helpers.AdminField(form, 'text', is_first=False).label_tag(),
                         '<label for="id_text" class="required inline">&amp;text:</label>')
        self.assertEqual(helpers.AdminField(form, 'cb', is_first=False).label_tag(),
                         '<label for="id_cb" class="vCheckboxLabel required inline">&amp;cb</label>')
