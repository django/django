from datetime import datetime
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib.admin import helpers
from django.contrib.admin.utils import (
    NestedObjects, display_for_field, display_for_value, flatten,
    flatten_fieldsets, label_for_field, lookup_field, quote,
)
from django.db import DEFAULT_DB_ALIAS, models
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils.formats import localize
from django.utils.safestring import mark_safe

from .models import (
    Article, Car, Count, Event, EventGuide, Location, Site, Vehicle,
)


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

    def test_on_delete_do_nothing(self):
        """
        The nested collector doesn't query for DO_NOTHING objects.
        """
        n = NestedObjects(using=DEFAULT_DB_ALIAS)
        objs = [Event.objects.create()]
        EventGuide.objects.create(event=objs[0])
        with self.assertNumQueries(2):
            # One for Location, one for Guest, and no query for EventGuide
            n.collect(objs)

    def test_relation_on_abstract(self):
        """
        NestedObjects.collect() doesn't trip (AttributeError) on the special
        notation for relations on abstract models (related_name that contains
        %(app_label)s and/or %(class)s) (#21846).
        """
        n = NestedObjects(using=DEFAULT_DB_ALIAS)
        Car.objects.create()
        n.collect([Vehicle.objects.first()])


class UtilsTests(SimpleTestCase):

    empty_value = '-empty-'

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

        class MockModelAdmin:
            def get_admin_value(self, obj):
                return ADMIN_METHOD

        def simple_function(obj):
            return SIMPLE_FUNCTION

        site_obj = Site(domain=SITE_NAME)
        article = Article(
            site=site_obj,
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
                resolved_value = display_for_field(resolved_value, field, self.empty_value)

            self.assertEqual(value, resolved_value)

    def test_null_display_for_field(self):
        """
        Regression test for #12550: display_for_field should handle None
        value.
        """
        display_value = display_for_field(None, models.CharField(), self.empty_value)
        self.assertEqual(display_value, self.empty_value)

        display_value = display_for_field(None, models.CharField(
            choices=(
                (None, "test_none"),
            )
        ), self.empty_value)
        self.assertEqual(display_value, "test_none")

        display_value = display_for_field(None, models.DateField(), self.empty_value)
        self.assertEqual(display_value, self.empty_value)

        display_value = display_for_field(None, models.TimeField(), self.empty_value)
        self.assertEqual(display_value, self.empty_value)

        # Regression test for #13071: NullBooleanField has special
        # handling.
        display_value = display_for_field(None, models.NullBooleanField(), self.empty_value)
        expected = '<img src="%sadmin/img/icon-unknown.svg" alt="None">' % settings.STATIC_URL
        self.assertHTMLEqual(display_value, expected)

        display_value = display_for_field(None, models.BooleanField(null=True), self.empty_value)
        expected = '<img src="%sadmin/img/icon-unknown.svg" alt="None" />' % settings.STATIC_URL
        self.assertHTMLEqual(display_value, expected)

        display_value = display_for_field(None, models.DecimalField(), self.empty_value)
        self.assertEqual(display_value, self.empty_value)

        display_value = display_for_field(None, models.FloatField(), self.empty_value)
        self.assertEqual(display_value, self.empty_value)

    def test_number_formats_display_for_field(self):
        display_value = display_for_field(12345.6789, models.FloatField(), self.empty_value)
        self.assertEqual(display_value, '12345.6789')

        display_value = display_for_field(Decimal('12345.6789'), models.DecimalField(), self.empty_value)
        self.assertEqual(display_value, '12345.6789')

        display_value = display_for_field(12345, models.IntegerField(), self.empty_value)
        self.assertEqual(display_value, '12345')

    @override_settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_number_formats_with_thousand_separator_display_for_field(self):
        display_value = display_for_field(12345.6789, models.FloatField(), self.empty_value)
        self.assertEqual(display_value, '12,345.6789')

        display_value = display_for_field(Decimal('12345.6789'), models.DecimalField(), self.empty_value)
        self.assertEqual(display_value, '12,345.6789')

        display_value = display_for_field(12345, models.IntegerField(), self.empty_value)
        self.assertEqual(display_value, '12,345')

    def test_list_display_for_value(self):
        display_value = display_for_value([1, 2, 3], self.empty_value)
        self.assertEqual(display_value, '1, 2, 3')

        display_value = display_for_value([1, 2, 'buckle', 'my', 'shoe'], self.empty_value)
        self.assertEqual(display_value, '1, 2, buckle, my, shoe')

    @override_settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True)
    def test_list_display_for_value_boolean(self):
        self.assertEqual(
            display_for_value(True, '', boolean=True),
            '<img src="/static/admin/img/icon-yes.svg" alt="True">'
        )
        self.assertEqual(
            display_for_value(False, '', boolean=True),
            '<img src="/static/admin/img/icon-no.svg" alt="False">'
        )
        self.assertEqual(display_for_value(True, ''), 'True')
        self.assertEqual(display_for_value(False, ''), 'False')

    def test_label_for_field(self):
        """
        Tests for label_for_field
        """
        self.assertEqual(
            label_for_field("title", Article),
            "title"
        )
        self.assertEqual(
            label_for_field("hist", Article),
            "History"
        )
        self.assertEqual(
            label_for_field("hist", Article, return_attr=True),
            ("History", None)
        )

        self.assertEqual(
            label_for_field("__str__", Article),
            "article"
        )

        with self.assertRaisesMessage(AttributeError, "Unable to lookup 'unknown' on Article"):
            label_for_field("unknown", Article)

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
        self.assertEqual(label_for_field('site_id', Article), 'Site id')

        class MockModelAdmin:
            def test_from_model(self, obj):
                return "nothing"
            test_from_model.short_description = "not Really the Model"

        self.assertEqual(
            label_for_field("test_from_model", Article, model_admin=MockModelAdmin),
            "not Really the Model"
        )
        self.assertEqual(
            label_for_field("test_from_model", Article, model_admin=MockModelAdmin, return_attr=True),
            ("not Really the Model", MockModelAdmin.test_from_model)
        )

    def test_label_for_property(self):
        # NOTE: cannot use @property decorator, because of
        # AttributeError: 'property' object has no attribute 'short_description'
        class MockModelAdmin:
            def my_property(self):
                return "this if from property"
            my_property.short_description = 'property short description'
            test_from_property = property(my_property)

        self.assertEqual(
            label_for_field("test_from_property", Article, model_admin=MockModelAdmin),
            'property short description'
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

    def test_safestring_in_field_label(self):
        # safestring should not be escaped
        class MyForm(forms.Form):
            text = forms.CharField(label=mark_safe('<i>text</i>'))
            cb = forms.BooleanField(label=mark_safe('<i>cb</i>'))

        form = MyForm()
        self.assertHTMLEqual(helpers.AdminField(form, 'text', is_first=False).label_tag(),
                             '<label for="id_text" class="required inline"><i>text</i>:</label>')
        self.assertHTMLEqual(helpers.AdminField(form, 'cb', is_first=False).label_tag(),
                             '<label for="id_cb" class="vCheckboxLabel required inline"><i>cb</i></label>')

        # normal strings needs to be escaped
        class MyForm(forms.Form):
            text = forms.CharField(label='&text')
            cb = forms.BooleanField(label='&cb')

        form = MyForm()
        self.assertHTMLEqual(helpers.AdminField(form, 'text', is_first=False).label_tag(),
                             '<label for="id_text" class="required inline">&amp;text:</label>')
        self.assertHTMLEqual(helpers.AdminField(form, 'cb', is_first=False).label_tag(),
                             '<label for="id_cb" class="vCheckboxLabel required inline">&amp;cb</label>')

    def test_flatten(self):
        flat_all = ['url', 'title', 'content', 'sites']
        inputs = (
            ((), []),
            (('url', 'title', ('content', 'sites')), flat_all),
            (('url', 'title', 'content', 'sites'), flat_all),
            ((('url', 'title'), ('content', 'sites')), flat_all)
        )
        for orig, expected in inputs:
            self.assertEqual(flatten(orig), expected)

    def test_flatten_fieldsets(self):
        """
        Regression test for #18051
        """
        fieldsets = (
            (None, {
                'fields': ('url', 'title', ('content', 'sites'))
            }),
        )
        self.assertEqual(flatten_fieldsets(fieldsets), ['url', 'title', 'content', 'sites'])

        fieldsets = (
            (None, {
                'fields': ('url', 'title', ['content', 'sites'])
            }),
        )
        self.assertEqual(flatten_fieldsets(fieldsets), ['url', 'title', 'content', 'sites'])

    def test_quote(self):
        self.assertEqual(quote('something\nor\nother'), 'something_0Aor_0Aother')
