import json
import unittest

from django import forms
from django.core import serializers
from django.db import connection, models
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils.encoding import force_str

from .models import (
    Foo, ModelWithReadonlyField, RenamedField, VerboseNameField, Whiz,
    WhizIter, WhizIterEmpty,
)


class BasicFieldTests(TestCase):

    def test_show_hidden_initial(self):
        """
        Fields with choices respect show_hidden_initial as a kwarg to
        formfield().
        """
        choices = [(0, 0), (1, 1)]
        model_field = models.Field(choices=choices)
        form_field = model_field.formfield(show_hidden_initial=True)
        self.assertTrue(form_field.show_hidden_initial)

        form_field = model_field.formfield(show_hidden_initial=False)
        self.assertFalse(form_field.show_hidden_initial)

    def test_field_repr(self):
        """
        __repr__() of a field displays its name.
        """
        f = Foo._meta.get_field('a')
        self.assertEqual(repr(f), '<django.db.models.fields.CharField: a>')
        f = models.fields.CharField()
        self.assertEqual(repr(f), '<django.db.models.fields.CharField>')

    def test_field_name(self):
        """
        A defined field name (name="fieldname") is used instead of the model
        model's attribute name (modelname).
        """
        instance = RenamedField()
        self.assertTrue(hasattr(instance, 'get_fieldname_display'))
        self.assertFalse(hasattr(instance, 'get_modelname_display'))

    def test_field_verbose_name(self):
        m = VerboseNameField
        for i in range(1, 24):
            self.assertEqual(m._meta.get_field('field%d' % i).verbose_name, 'verbose field%d' % i)

        self.assertEqual(m._meta.get_field('id').verbose_name, 'verbose pk')

    def test_choices_form_class(self):
        """Can supply a custom choices form class to Field.formfield()"""
        choices = [('a', 'a')]
        field = models.CharField(choices=choices)
        klass = forms.TypedMultipleChoiceField
        self.assertIsInstance(field.formfield(choices_form_class=klass), klass)

    def test_field_str(self):
        f = Foo._meta.get_field('a')
        self.assertEqual(force_str(f), 'model_fields.Foo.a')


class ReadonlyTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super(ReadonlyTests, cls).setUpClass()

        if connection.vendor == 'sqlite':
            connection.cursor().execute(
                '''DROP TABLE model_fields_modelwithreadonlyfield''')
            connection.cursor().execute(
                '''CREATE TABLE model_fields_modelwithreadonlyfield
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    not_readonly TEXT,
                    readonly_int1 INTEGER DEFAULT 1,
                    readonly_int2 INTEGER DEFAULT 2
                )''')
        else:
            connection.cursor().execute(
                '''ALTER TABLE model_fields_modelwithreadonlyfield ALTER COLUMN readonly_int1 SET DEFAULT 1''')
            connection.cursor().execute(
                '''ALTER TABLE model_fields_modelwithreadonlyfield ALTER COLUMN readonly_int2 SET DEFAULT 2''')

    def test_readonly_option(self):
        # Default value
        self.assertFalse(ModelWithReadonlyField._meta.get_field('not_readonly').readonly)

        # When the readonly attribute is set
        self.assertTrue(ModelWithReadonlyField._meta.get_field('readonly_int1').readonly)

    def test_create(self):
        with CaptureQueriesContext(connection=connection) as capture:
            inst = ModelWithReadonlyField.objects.create(
                not_readonly='not_readonly',
                readonly_int1=3,
            )

        self.assertEqual(len(capture.captured_queries), 2)
        query = capture.captured_queries[0]

        self.assertIn('not_readonly', query['sql'])
        self.assertNotIn('readonly_int1', query['sql'])
        self.assertNotIn('readonly_int2', query['sql'])
        self.assertEqual(inst.readonly_int1, 1)
        self.assertEqual(inst.readonly_int2, 2)

    def test_save_new(self):
        with CaptureQueriesContext(connection=connection) as capture:
            inst = ModelWithReadonlyField(
                not_readonly='not_readonly',
                readonly_int1=1,
            )
            inst.save()

        self.assertEqual(len(capture.captured_queries), 2)
        query = capture.captured_queries[0]

        self.assertIn('not_readonly', query['sql'])
        self.assertNotIn('readonly_int1', query['sql'])
        self.assertNotIn('readonly_int2', query['sql'])
        self.assertEqual(inst.readonly_int1, 1)
        self.assertEqual(inst.readonly_int2, 2)

    def test_save_update(self):
        inst = ModelWithReadonlyField.objects.create(
            not_readonly="not_readonly",
            readonly_int1=5,
        )
        inst.not_readonly = 'foo'
        inst.readonly_int1 = 42

        with CaptureQueriesContext(connection=connection) as capture:
            inst.save()

        query = capture.captured_queries[0]

        self.assertIn('not_readonly', query['sql'])
        self.assertNotIn('readonly_int1', query['sql'])
        self.assertNotIn('readonly_int2', query['sql'])
        self.assertEqual(inst.readonly_int1, 1)
        self.assertEqual(inst.readonly_int2, 2)

    def test_update(self):
        inst = ModelWithReadonlyField.objects.create(
            not_readonly='not_readonly',
            readonly_int1=1,
        )
        qs = ModelWithReadonlyField.objects.filter(pk=inst.pk)

        with CaptureQueriesContext(connection=connection) as capture:
            qs.update(
                not_readonly='foo',
                readonly_int1=42,
            )

        query = capture.captured_queries[0]

        self.assertIn('not_readonly', query['sql'])
        self.assertNotIn('readonly_int1', query['sql'])
        self.assertNotIn('readonly_int2', query['sql'])

    def test_get_or_create(self):
        with CaptureQueriesContext(connection=connection) as capture:
            inst, _ = ModelWithReadonlyField.objects.get_or_create(
                not_readonly='not_readonly',
                readonly_int1=3,
            )
        insert_queries = [
            query for query in capture.captured_queries
            if query['sql'].startswith('INSERT')]

        self.assertEqual(len(insert_queries), 1)
        query = insert_queries[0]
        self.assertTrue(query['sql'].startswith('INSERT'), '{} is not INSERT'.format(query['sql']))

        self.assertIn('not_readonly', query['sql'])
        self.assertNotIn('readonly_int1', query['sql'])
        self.assertNotIn('readonly_int2', query['sql'])
        self.assertEqual(inst.readonly_int1, 1)
        self.assertEqual(inst.readonly_int2, 2)

    def test_bulk_create(self):
        with CaptureQueriesContext(connection=connection) as capture:
            ModelWithReadonlyField.objects.bulk_create([
                ModelWithReadonlyField(
                    not_readonly='not_readonly',
                    readonly_int1=1,
                ),
                ModelWithReadonlyField(
                    not_readonly='rabble rabble',
                    readonly_int2=9001,
                )
            ])

        self.assertEqual(len(capture.captured_queries), 1)
        query = capture.captured_queries[0]

        self.assertIn('not_readonly', query['sql'])
        self.assertNotIn('readonly_int1', query['sql'])
        self.assertNotIn('readonly_int2', query['sql'])

        # bulk_create won't fetch the database computed
        # values so it's no use trying to check it.

    def test_deserialize(self):
        try:
            pk = ModelWithReadonlyField.objects.latest('id').id + 1
        except ModelWithReadonlyField.DoesNotExist:
            pk = 1

        json_inst = json.dumps(
            [{
                'model': 'model_fields.modelwithreadonlyfield',
                'pk': pk,
                'fields': {
                    'not_readonly': 'All your base',
                    'readonly_int1': 12,
                },
            }]
        )

        # Check that the save works
        deserialized = serializers.deserialize('json', json_inst)
        inst = next(deserialized)
        with CaptureQueriesContext(connection=connection) as capture:
            inst.save()

        # Because a pk is specified, Django will try to do an UPDATE and then
        # an INSERT when the UPDATE returns with 0 rows affected
        self.assertEqual(len(capture.captured_queries), 3)
        query_1 = capture.captured_queries[0]['sql']

        self.assertTrue(query_1.startswith('UPDATE'), '{} is not UPDATE'.format(query_1))
        self.assertIn('not_readonly', query_1)
        self.assertNotIn('readonly_int1', query_1)
        self.assertNotIn('readonly_int2', query_1)

        query_2 = capture.captured_queries[1]['sql']
        self.assertTrue(query_2.startswith('INSERT'), '{} is not INSERT'.format(query_2))
        self.assertIn('not_readonly', query_2)
        self.assertNotIn('readonly_int1', query_2)
        self.assertNotIn('readonly_int2', query_2)


class ChoicesTests(SimpleTestCase):

    def test_choices_and_field_display(self):
        """
        get_choices() interacts with get_FIELD_display() to return the expected
        values.
        """
        self.assertEqual(Whiz(c=1).get_c_display(), 'First')    # A nested value
        self.assertEqual(Whiz(c=0).get_c_display(), 'Other')    # A top level value
        self.assertEqual(Whiz(c=9).get_c_display(), 9)          # Invalid value
        self.assertIsNone(Whiz(c=None).get_c_display())         # Blank value
        self.assertEqual(Whiz(c='').get_c_display(), '')        # Empty value

    def test_iterator_choices(self):
        """
        get_choices() works with Iterators.
        """
        self.assertEqual(WhizIter(c=1).c, 1)          # A nested value
        self.assertEqual(WhizIter(c=9).c, 9)          # Invalid value
        self.assertIsNone(WhizIter(c=None).c)         # Blank value
        self.assertEqual(WhizIter(c='').c, '')        # Empty value

    def test_empty_iterator_choices(self):
        """
        get_choices() works with empty iterators.
        """
        self.assertEqual(WhizIterEmpty(c="a").c, "a")  # A nested value
        self.assertEqual(WhizIterEmpty(c="b").c, "b")  # Invalid value
        self.assertIsNone(WhizIterEmpty(c=None).c)  # Blank value
        self.assertEqual(WhizIterEmpty(c='').c, '')  # Empty value
