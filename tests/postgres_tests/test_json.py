import datetime
import operator
import uuid
from decimal import Decimal

from django.core import checks, exceptions, serializers
from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.db.models.expressions import RawSQL
from django.db.models.functions import Cast
from django.forms import CharField, Form, widgets
from django.test.utils import CaptureQueriesContext, isolate_apps
from django.utils.html import escape

from . import PostgreSQLSimpleTestCase, PostgreSQLTestCase
from .models import JSONModel, PostgreSQLModel

try:
    from django.contrib.postgres import forms
    from django.contrib.postgres.fields import JSONField
    from django.contrib.postgres.fields.jsonb import KeyTextTransform, KeyTransform
except ImportError:
    pass


class TestSaveLoad(PostgreSQLTestCase):
    def test_null(self):
        instance = JSONModel()
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertIsNone(loaded.field)

    def test_empty_object(self):
        instance = JSONModel(field={})
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertEqual(loaded.field, {})

    def test_empty_list(self):
        instance = JSONModel(field=[])
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertEqual(loaded.field, [])

    def test_boolean(self):
        instance = JSONModel(field=True)
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertIs(loaded.field, True)

    def test_string(self):
        instance = JSONModel(field='why?')
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertEqual(loaded.field, 'why?')

    def test_number(self):
        instance = JSONModel(field=1)
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertEqual(loaded.field, 1)

    def test_realistic_object(self):
        obj = {
            'a': 'b',
            'c': 1,
            'd': ['e', {'f': 'g'}],
            'h': True,
            'i': False,
            'j': None,
        }
        instance = JSONModel(field=obj)
        instance.save()
        loaded = JSONModel.objects.get()
        self.assertEqual(loaded.field, obj)

    def test_custom_encoding(self):
        """
        JSONModel.field_custom has a custom DjangoJSONEncoder.
        """
        some_uuid = uuid.uuid4()
        obj_before = {
            'date': datetime.date(2016, 8, 12),
            'datetime': datetime.datetime(2016, 8, 12, 13, 44, 47, 575981),
            'decimal': Decimal('10.54'),
            'uuid': some_uuid,
        }
        obj_after = {
            'date': '2016-08-12',
            'datetime': '2016-08-12T13:44:47.575',
            'decimal': '10.54',
            'uuid': str(some_uuid),
        }
        JSONModel.objects.create(field_custom=obj_before)
        loaded = JSONModel.objects.get()
        self.assertEqual(loaded.field_custom, obj_after)


class TestQuerying(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = JSONModel.objects.bulk_create([
            JSONModel(field=None),
            JSONModel(field=True),
            JSONModel(field=False),
            JSONModel(field='yes'),
            JSONModel(field=7),
            JSONModel(field=[]),
            JSONModel(field={}),
            JSONModel(field={
                'a': 'b',
                'c': 1,
            }),
            JSONModel(field={
                'a': 'b',
                'c': 1,
                'd': ['e', {'f': 'g'}],
                'h': True,
                'i': False,
                'j': None,
                'k': {'l': 'm'},
            }),
            JSONModel(field=[1, [2]]),
            JSONModel(field={
                'k': True,
                'l': False,
            }),
            JSONModel(field={
                'foo': 'bar',
                'baz': {'a': 'b', 'c': 'd'},
                'bar': ['foo', 'bar'],
                'bax': {'foo': 'bar'},
            }),
        ])

    def test_exact(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__exact={}),
            [self.objs[6]]
        )

    def test_exact_complex(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__exact={'a': 'b', 'c': 1}),
            [self.objs[7]]
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__isnull=True),
            [self.objs[0]]
        )

    def test_ordering_by_transform(self):
        objs = [
            JSONModel.objects.create(field={'ord': 93, 'name': 'bar'}),
            JSONModel.objects.create(field={'ord': 22.1, 'name': 'foo'}),
            JSONModel.objects.create(field={'ord': -1, 'name': 'baz'}),
            JSONModel.objects.create(field={'ord': 21.931902, 'name': 'spam'}),
            JSONModel.objects.create(field={'ord': -100291029, 'name': 'eggs'}),
        ]
        query = JSONModel.objects.filter(field__name__isnull=False).order_by('field__ord')
        self.assertSequenceEqual(query, [objs[4], objs[2], objs[3], objs[1], objs[0]])

    def test_ordering_grouping_by_key_transform(self):
        base_qs = JSONModel.objects.filter(field__d__0__isnull=False)
        for qs in (
            base_qs.order_by('field__d__0'),
            base_qs.annotate(key=KeyTransform('0', KeyTransform('d', 'field'))).order_by('key'),
        ):
            self.assertSequenceEqual(qs, [self.objs[8]])
        qs = JSONModel.objects.filter(field__isnull=False)
        self.assertQuerysetEqual(
            qs.values('field__d__0').annotate(count=Count('field__d__0')).order_by('count'),
            [1, 10],
            operator.itemgetter('count'),
        )
        self.assertQuerysetEqual(
            qs.filter(field__isnull=False).annotate(
                key=KeyTextTransform('f', KeyTransform('1', KeyTransform('d', 'field'))),
            ).values('key').annotate(count=Count('key')).order_by('count'),
            [(None, 0), ('g', 1)],
            operator.itemgetter('key', 'count'),
        )

    def test_key_transform_raw_expression(self):
        expr = RawSQL('%s::jsonb', ['{"x": "bar"}'])
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__foo=KeyTransform('x', expr)),
            [self.objs[-1]],
        )

    def test_key_transform_expression(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__d__0__isnull=False).annotate(
                key=KeyTransform('d', 'field'),
            ).annotate(
                chain=KeyTransform('0', 'key'),
                expr=KeyTransform('0', Cast('key', JSONField())),
            ).filter(chain=F('expr')),
            [self.objs[8]],
        )

    def test_deep_values(self):
        query = JSONModel.objects.values_list('field__k__l')
        self.assertSequenceEqual(
            query,
            [
                (None,), (None,), (None,), (None,), (None,), (None,),
                (None,), (None,), ('m',), (None,), (None,), (None,),
            ]
        )

    def test_deep_distinct(self):
        query = JSONModel.objects.distinct('field__k__l').values_list('field__k__l')
        self.assertSequenceEqual(query, [('m',), (None,)])

    def test_isnull_key(self):
        # key__isnull works the same as has_key='key'.
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__a__isnull=True),
            self.objs[:7] + self.objs[9:]
        )
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__a__isnull=False),
            [self.objs[7], self.objs[8]]
        )

    def test_none_key(self):
        self.assertSequenceEqual(JSONModel.objects.filter(field__j=None), [self.objs[8]])

    def test_none_key_exclude(self):
        obj = JSONModel.objects.create(field={'j': 1})
        self.assertSequenceEqual(JSONModel.objects.exclude(field__j=None), [obj])

    def test_isnull_key_or_none(self):
        obj = JSONModel.objects.create(field={'a': None})
        self.assertSequenceEqual(
            JSONModel.objects.filter(Q(field__a__isnull=True) | Q(field__a=None)),
            self.objs[:7] + self.objs[9:] + [obj]
        )

    def test_contains(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__contains={'a': 'b'}),
            [self.objs[7], self.objs[8]]
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__contained_by={'a': 'b', 'c': 1, 'h': True}),
            [self.objs[6], self.objs[7]]
        )

    def test_has_key(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__has_key='a'),
            [self.objs[7], self.objs[8]]
        )

    def test_has_keys(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__has_keys=['a', 'c', 'h']),
            [self.objs[8]]
        )

    def test_has_any_keys(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__has_any_keys=['c', 'l']),
            [self.objs[7], self.objs[8], self.objs[10]]
        )

    def test_shallow_list_lookup(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__0=1),
            [self.objs[9]]
        )

    def test_shallow_obj_lookup(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__a='b'),
            [self.objs[7], self.objs[8]]
        )

    def test_obj_subquery_lookup(self):
        qs = JSONModel.objects.annotate(
            value=Subquery(JSONModel.objects.filter(pk=OuterRef('pk')).values('field')),
        ).filter(value__a='b')
        self.assertSequenceEqual(qs, [self.objs[7], self.objs[8]])

    def test_deep_lookup_objs(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__k__l='m'),
            [self.objs[8]]
        )

    def test_shallow_lookup_obj_target(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__k={'l': 'm'}),
            [self.objs[8]]
        )

    def test_deep_lookup_array(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__1__0=2),
            [self.objs[9]]
        )

    def test_deep_lookup_mixed(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__d__1__f='g'),
            [self.objs[8]]
        )

    def test_deep_lookup_transform(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__c__gt=1),
            []
        )
        self.assertSequenceEqual(
            JSONModel.objects.filter(field__c__lt=5),
            [self.objs[7], self.objs[8]]
        )

    def test_usage_in_subquery(self):
        self.assertSequenceEqual(
            JSONModel.objects.filter(id__in=JSONModel.objects.filter(field__c=1)),
            self.objs[7:9]
        )

    def test_iexact(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__iexact='BaR').exists())
        self.assertFalse(JSONModel.objects.filter(field__foo__iexact='"BaR"').exists())

    def test_icontains(self):
        self.assertFalse(JSONModel.objects.filter(field__foo__icontains='"bar"').exists())

    def test_startswith(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__startswith='b').exists())

    def test_istartswith(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__istartswith='B').exists())

    def test_endswith(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__endswith='r').exists())

    def test_iendswith(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__iendswith='R').exists())

    def test_regex(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__regex=r'^bar$').exists())

    def test_iregex(self):
        self.assertTrue(JSONModel.objects.filter(field__foo__iregex=r'^bAr$').exists())

    def test_key_sql_injection(self):
        with CaptureQueriesContext(connection) as queries:
            self.assertFalse(
                JSONModel.objects.filter(**{
                    """field__test' = '"a"') OR 1 = 1 OR ('d""": 'x',
                }).exists()
            )
        self.assertIn(
            """."field" -> 'test'' = ''"a"'') OR 1 = 1 OR (''d') = '"x"' """,
            queries[0]['sql'],
        )

    def test_lookups_with_key_transform(self):
        tests = (
            ('field__d__contains', 'e'),
            ('field__baz__contained_by', {'a': 'b', 'c': 'd', 'e': 'f'}),
            ('field__baz__has_key', 'c'),
            ('field__baz__has_keys', ['a', 'c']),
            ('field__baz__has_any_keys', ['a', 'x']),
            ('field__contains', KeyTransform('bax', 'field')),
            (
                'field__contained_by',
                KeyTransform('x', RawSQL('%s::jsonb', ['{"x": {"a": "b", "c": 1, "d": "e"}}'])),
            ),
            ('field__has_key', KeyTextTransform('foo', 'field')),
        )
        for lookup, value in tests:
            with self.subTest(lookup=lookup):
                self.assertTrue(JSONModel.objects.filter(
                    **{lookup: value},
                ).exists())


@isolate_apps('postgres_tests')
class TestChecks(PostgreSQLSimpleTestCase):

    def test_invalid_default(self):
        class MyModel(PostgreSQLModel):
            field = JSONField(default={})

        model = MyModel()
        self.assertEqual(model.check(), [
            checks.Warning(
                msg=(
                    "JSONField default should be a callable instead of an "
                    "instance so that it's not shared between all field "
                    "instances."
                ),
                hint='Use a callable instead, e.g., use `dict` instead of `{}`.',
                obj=MyModel._meta.get_field('field'),
                id='postgres.E003',
            )
        ])

    def test_valid_default(self):
        class MyModel(PostgreSQLModel):
            field = JSONField(default=dict)

        model = MyModel()
        self.assertEqual(model.check(), [])

    def test_valid_default_none(self):
        class MyModel(PostgreSQLModel):
            field = JSONField(default=None)

        model = MyModel()
        self.assertEqual(model.check(), [])


class TestSerialization(PostgreSQLSimpleTestCase):
    test_data = (
        '[{"fields": {"field": %s, "field_custom": null}, '
        '"model": "postgres_tests.jsonmodel", "pk": null}]'
    )
    test_values = (
        # (Python value, serialized value),
        ({'a': 'b', 'c': None}, '{"a": "b", "c": null}'),
        ('abc', '"abc"'),
        ('{"a": "a"}', '"{\\"a\\": \\"a\\"}"'),
    )

    def test_dumping(self):
        for value, serialized in self.test_values:
            with self.subTest(value=value):
                instance = JSONModel(field=value)
                data = serializers.serialize('json', [instance])
                self.assertJSONEqual(data, self.test_data % serialized)

    def test_loading(self):
        for value, serialized in self.test_values:
            with self.subTest(value=value):
                instance = list(serializers.deserialize('json', self.test_data % serialized))[0].object
                self.assertEqual(instance.field, value)


class TestValidation(PostgreSQLSimpleTestCase):

    def test_not_serializable(self):
        field = JSONField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(datetime.timedelta(days=1), None)
        self.assertEqual(cm.exception.code, 'invalid')
        self.assertEqual(cm.exception.message % cm.exception.params, "Value must be valid JSON.")

    def test_custom_encoder(self):
        with self.assertRaisesMessage(ValueError, "The encoder parameter must be a callable object."):
            field = JSONField(encoder=DjangoJSONEncoder())
        field = JSONField(encoder=DjangoJSONEncoder)
        self.assertEqual(field.clean(datetime.timedelta(days=1), None), datetime.timedelta(days=1))


class TestFormField(PostgreSQLSimpleTestCase):

    def test_valid(self):
        field = forms.JSONField()
        value = field.clean('{"a": "b"}')
        self.assertEqual(value, {'a': 'b'})

    def test_valid_empty(self):
        field = forms.JSONField(required=False)
        value = field.clean('')
        self.assertIsNone(value)

    def test_invalid(self):
        field = forms.JSONField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('{some badly formed: json}')
        self.assertEqual(cm.exception.messages[0], "'{some badly formed: json}' value must be valid JSON.")

    def test_formfield(self):
        model_field = JSONField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, forms.JSONField)

    def test_formfield_disabled(self):
        class JsonForm(Form):
            name = CharField()
            jfield = forms.JSONField(disabled=True)

        form = JsonForm({'name': 'xyz', 'jfield': '["bar"]'}, initial={'jfield': ['foo']})
        self.assertIn('[&quot;foo&quot;]</textarea>', form.as_p())

    def test_prepare_value(self):
        field = forms.JSONField()
        self.assertEqual(field.prepare_value({'a': 'b'}), '{"a": "b"}')
        self.assertEqual(field.prepare_value(None), 'null')
        self.assertEqual(field.prepare_value('foo'), '"foo"')

    def test_redisplay_wrong_input(self):
        """
        When displaying a bound form (typically due to invalid input), the form
        should not overquote JSONField inputs.
        """
        class JsonForm(Form):
            name = CharField(max_length=2)
            jfield = forms.JSONField()

        # JSONField input is fine, name is too long
        form = JsonForm({'name': 'xyz', 'jfield': '["foo"]'})
        self.assertIn('[&quot;foo&quot;]</textarea>', form.as_p())

        # This time, the JSONField input is wrong
        form = JsonForm({'name': 'xy', 'jfield': '{"foo"}'})
        # Appears once in the textarea and once in the error message
        self.assertEqual(form.as_p().count(escape('{"foo"}')), 2)

    def test_widget(self):
        """The default widget of a JSONField is a Textarea."""
        field = forms.JSONField()
        self.assertIsInstance(field.widget, widgets.Textarea)

    def test_custom_widget_kwarg(self):
        """The widget can be overridden with a kwarg."""
        field = forms.JSONField(widget=widgets.Input)
        self.assertIsInstance(field.widget, widgets.Input)

    def test_custom_widget_attribute(self):
        """The widget can be overridden with an attribute."""
        class CustomJSONField(forms.JSONField):
            widget = widgets.Input

        field = CustomJSONField()
        self.assertIsInstance(field.widget, widgets.Input)

    def test_already_converted_value(self):
        field = forms.JSONField(required=False)
        tests = [
            '["a", "b", "c"]', '{"a": 1, "b": 2}', '1', '1.5', '"foo"',
            'true', 'false', 'null',
        ]
        for json_string in tests:
            val = field.clean(json_string)
            self.assertEqual(field.clean(val), val)

    def test_has_changed(self):
        field = forms.JSONField()
        self.assertIs(field.has_changed({'a': True}, '{"a": 1}'), True)
        self.assertIs(field.has_changed({'a': 1, 'b': 2}, '{"b": 2, "a": 1}'), False)
