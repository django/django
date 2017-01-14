import decimal
import json
import unittest
import uuid

from django import forms
from django.core import exceptions, serializers, validators
from django.core.exceptions import FieldError
from django.core.management import call_command
from django.db import IntegrityError, connection, models
from django.test import TransactionTestCase, override_settings
from django.test.utils import isolate_apps
from django.utils import timezone

from . import PostgreSQLTestCase
from .models import (
    ArrayFieldSubclass, CharArrayModel, DateTimeArrayModel, IntegerArrayModel,
    NestedIntegerArrayModel, NullableIntegerArrayModel, OtherTypesArrayModel,
    PostgreSQLModel, Tag,
)

try:
    from django.contrib.postgres.fields import ArrayField
    from django.contrib.postgres.forms import (
        SimpleArrayField, SplitArrayField, SplitArrayWidget,
    )
except ImportError:
    pass


class TestSaveLoad(PostgreSQLTestCase):

    def test_integer(self):
        instance = IntegerArrayModel(field=[1, 2, 3])
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_char(self):
        instance = CharArrayModel(field=['hello', 'goodbye'])
        instance.save()
        loaded = CharArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_dates(self):
        instance = DateTimeArrayModel(
            datetimes=[timezone.now()],
            dates=[timezone.now().date()],
            times=[timezone.now().time()],
        )
        instance.save()
        loaded = DateTimeArrayModel.objects.get()
        self.assertEqual(instance.datetimes, loaded.datetimes)
        self.assertEqual(instance.dates, loaded.dates)
        self.assertEqual(instance.times, loaded.times)

    def test_tuples(self):
        instance = IntegerArrayModel(field=(1,))
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertSequenceEqual(instance.field, loaded.field)

    def test_integers_passed_as_strings(self):
        # This checks that get_prep_value is deferred properly
        instance = IntegerArrayModel(field=['1'])
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertEqual(loaded.field, [1])

    def test_default_null(self):
        instance = NullableIntegerArrayModel()
        instance.save()
        loaded = NullableIntegerArrayModel.objects.get(pk=instance.pk)
        self.assertIsNone(loaded.field)
        self.assertEqual(instance.field, loaded.field)

    def test_null_handling(self):
        instance = NullableIntegerArrayModel(field=None)
        instance.save()
        loaded = NullableIntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

        instance = IntegerArrayModel(field=None)
        with self.assertRaises(IntegrityError):
            instance.save()

    def test_nested(self):
        instance = NestedIntegerArrayModel(field=[[1, 2], [3, 4]])
        instance.save()
        loaded = NestedIntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_other_array_types(self):
        instance = OtherTypesArrayModel(
            ips=['192.168.0.1', '::1'],
            uuids=[uuid.uuid4()],
            decimals=[decimal.Decimal(1.25), 1.75],
            tags=[Tag(1), Tag(2), Tag(3)],
        )
        instance.save()
        loaded = OtherTypesArrayModel.objects.get()
        self.assertEqual(instance.ips, loaded.ips)
        self.assertEqual(instance.uuids, loaded.uuids)
        self.assertEqual(instance.decimals, loaded.decimals)
        self.assertEqual(instance.tags, loaded.tags)

    def test_null_from_db_value_handling(self):
        instance = OtherTypesArrayModel.objects.create(
            ips=['192.168.0.1', '::1'],
            uuids=[uuid.uuid4()],
            decimals=[decimal.Decimal(1.25), 1.75],
            tags=None,
        )
        instance.refresh_from_db()
        self.assertIsNone(instance.tags)

    def test_model_set_on_base_field(self):
        instance = IntegerArrayModel()
        field = instance._meta.get_field('field')
        self.assertEqual(field.model, IntegerArrayModel)
        self.assertEqual(field.base_field.model, IntegerArrayModel)


class TestQuerying(PostgreSQLTestCase):

    def setUp(self):
        self.objs = [
            NullableIntegerArrayModel.objects.create(field=[1]),
            NullableIntegerArrayModel.objects.create(field=[2]),
            NullableIntegerArrayModel.objects.create(field=[2, 3]),
            NullableIntegerArrayModel.objects.create(field=[20, 30, 40]),
            NullableIntegerArrayModel.objects.create(field=None),
        ]

    def test_exact(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__exact=[1]),
            self.objs[:1]
        )

    def test_exact_charfield(self):
        instance = CharArrayModel.objects.create(field=['text'])
        self.assertSequenceEqual(
            CharArrayModel.objects.filter(field=['text']),
            [instance]
        )

    def test_exact_nested(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field=[[1, 2], [3, 4]]),
            [instance]
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__isnull=True),
            self.objs[-1:]
        )

    def test_gt(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__gt=[0]),
            self.objs[:4]
        )

    def test_lt(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__lt=[2]),
            self.objs[:1]
        )

    def test_in(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__in=[[1], [2]]),
            self.objs[:2]
        )

    @unittest.expectedFailure
    def test_in_including_F_object(self):
        # This test asserts that Array objects passed to filters can be
        # constructed to contain F objects. This currently doesn't work as the
        # psycopg2 mogrify method that generates the ARRAY() syntax is
        # expecting literals, not column references (#27095).
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__in=[[models.F('id')]]),
            self.objs[:2]
        )

    def test_in_as_F_object(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__in=[models.F('field')]),
            self.objs[:4]
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contained_by=[1, 2]),
            self.objs[:2]
        )

    @unittest.expectedFailure
    def test_contained_by_including_F_object(self):
        # This test asserts that Array objects passed to filters can be
        # constructed to contain F objects. This currently doesn't work as the
        # psycopg2 mogrify method that generates the ARRAY() syntax is
        # expecting literals, not column references (#27095).
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contained_by=[models.F('id'), 2]),
            self.objs[:2]
        )

    def test_contains(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contains=[2]),
            self.objs[1:3]
        )

    def test_contains_charfield(self):
        # Regression for #22907
        self.assertSequenceEqual(
            CharArrayModel.objects.filter(field__contains=['text']),
            []
        )

    def test_contained_by_charfield(self):
        self.assertSequenceEqual(
            CharArrayModel.objects.filter(field__contained_by=['text']),
            []
        )

    def test_overlap_charfield(self):
        self.assertSequenceEqual(
            CharArrayModel.objects.filter(field__overlap=['text']),
            []
        )

    def test_index(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0=2),
            self.objs[1:3]
        )

    def test_index_chained(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0__lt=3),
            self.objs[0:3]
        )

    def test_index_nested(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field__0__0=1),
            [instance]
        )

    @unittest.expectedFailure
    def test_index_used_on_nested_data(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field__0=[1, 2]),
            [instance]
        )

    def test_overlap(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__overlap=[1, 2]),
            self.objs[0:3]
        )

    def test_len(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__len__lte=2),
            self.objs[0:3]
        )

    def test_len_empty_array(self):
        obj = NullableIntegerArrayModel.objects.create(field=[])
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__len=0),
            [obj]
        )

    def test_slice(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0_1=[2]),
            self.objs[1:3]
        )

        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__0_2=[2, 3]),
            self.objs[2:3]
        )

    @unittest.expectedFailure
    def test_slice_nested(self):
        instance = NestedIntegerArrayModel.objects.create(field=[[1, 2], [3, 4]])
        self.assertSequenceEqual(
            NestedIntegerArrayModel.objects.filter(field__0__0_1=[1]),
            [instance]
        )

    def test_usage_in_subquery(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(
                id__in=NullableIntegerArrayModel.objects.filter(field__len=3)
            ),
            [self.objs[3]]
        )

    def test_unsupported_lookup(self):
        msg = "Unsupported lookup '0_bar' for ArrayField or join on the field not permitted."
        with self.assertRaisesMessage(FieldError, msg):
            list(NullableIntegerArrayModel.objects.filter(field__0_bar=[2]))

        msg = "Unsupported lookup '0bar' for ArrayField or join on the field not permitted."
        with self.assertRaisesMessage(FieldError, msg):
            list(NullableIntegerArrayModel.objects.filter(field__0bar=[2]))


class TestDateTimeExactQuerying(PostgreSQLTestCase):

    def setUp(self):
        now = timezone.now()
        self.datetimes = [now]
        self.dates = [now.date()]
        self.times = [now.time()]
        self.objs = [
            DateTimeArrayModel.objects.create(
                datetimes=self.datetimes,
                dates=self.dates,
                times=self.times,
            )
        ]

    def test_exact_datetimes(self):
        self.assertSequenceEqual(
            DateTimeArrayModel.objects.filter(datetimes=self.datetimes),
            self.objs
        )

    def test_exact_dates(self):
        self.assertSequenceEqual(
            DateTimeArrayModel.objects.filter(dates=self.dates),
            self.objs
        )

    def test_exact_times(self):
        self.assertSequenceEqual(
            DateTimeArrayModel.objects.filter(times=self.times),
            self.objs
        )


class TestOtherTypesExactQuerying(PostgreSQLTestCase):

    def setUp(self):
        self.ips = ['192.168.0.1', '::1']
        self.uuids = [uuid.uuid4()]
        self.decimals = [decimal.Decimal(1.25), 1.75]
        self.tags = [Tag(1), Tag(2), Tag(3)]
        self.objs = [
            OtherTypesArrayModel.objects.create(
                ips=self.ips,
                uuids=self.uuids,
                decimals=self.decimals,
                tags=self.tags,
            )
        ]

    def test_exact_ip_addresses(self):
        self.assertSequenceEqual(
            OtherTypesArrayModel.objects.filter(ips=self.ips),
            self.objs
        )

    def test_exact_uuids(self):
        self.assertSequenceEqual(
            OtherTypesArrayModel.objects.filter(uuids=self.uuids),
            self.objs
        )

    def test_exact_decimals(self):
        self.assertSequenceEqual(
            OtherTypesArrayModel.objects.filter(decimals=self.decimals),
            self.objs
        )

    def test_exact_tags(self):
        self.assertSequenceEqual(
            OtherTypesArrayModel.objects.filter(tags=self.tags),
            self.objs
        )


@isolate_apps('postgres_tests')
class TestChecks(PostgreSQLTestCase):

    def test_field_checks(self):
        class MyModel(PostgreSQLModel):
            field = ArrayField(models.CharField())

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        # The inner CharField is missing a max_length.
        self.assertEqual(errors[0].id, 'postgres.E001')
        self.assertIn('max_length', errors[0].msg)

    def test_invalid_base_fields(self):
        class MyModel(PostgreSQLModel):
            field = ArrayField(models.ManyToManyField('postgres_tests.IntegerArrayModel'))

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E002')

    def test_nested_field_checks(self):
        """
        Nested ArrayFields are permitted.
        """
        class MyModel(PostgreSQLModel):
            field = ArrayField(ArrayField(models.CharField()))

        model = MyModel()
        errors = model.check()
        self.assertEqual(len(errors), 1)
        # The inner CharField is missing a max_length.
        self.assertEqual(errors[0].id, 'postgres.E001')
        self.assertIn('max_length', errors[0].msg)


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class TestMigrations(TransactionTestCase):

    available_apps = ['postgres_tests']

    def test_deconstruct(self):
        field = ArrayField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        new = ArrayField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))
        self.assertIsNot(new.base_field, field.base_field)

    def test_deconstruct_with_size(self):
        field = ArrayField(models.IntegerField(), size=3)
        name, path, args, kwargs = field.deconstruct()
        new = ArrayField(*args, **kwargs)
        self.assertEqual(new.size, field.size)

    def test_deconstruct_args(self):
        field = ArrayField(models.CharField(max_length=20))
        name, path, args, kwargs = field.deconstruct()
        new = ArrayField(*args, **kwargs)
        self.assertEqual(new.base_field.max_length, field.base_field.max_length)

    def test_subclass_deconstruct(self):
        field = ArrayField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.fields.ArrayField')

        field = ArrayFieldSubclass()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, 'postgres_tests.models.ArrayFieldSubclass')

    @override_settings(MIGRATION_MODULES={
        "postgres_tests": "postgres_tests.array_default_migrations",
    })
    def test_adding_field_with_default(self):
        # See #22962
        table_name = 'postgres_tests_integerarraydefaultmodel'
        with connection.cursor() as cursor:
            self.assertNotIn(table_name, connection.introspection.table_names(cursor))
        call_command('migrate', 'postgres_tests', verbosity=0)
        with connection.cursor() as cursor:
            self.assertIn(table_name, connection.introspection.table_names(cursor))
        call_command('migrate', 'postgres_tests', 'zero', verbosity=0)
        with connection.cursor() as cursor:
            self.assertNotIn(table_name, connection.introspection.table_names(cursor))

    @override_settings(MIGRATION_MODULES={
        "postgres_tests": "postgres_tests.array_index_migrations",
    })
    def test_adding_arrayfield_with_index(self):
        """
        ArrayField shouldn't have varchar_patterns_ops or text_patterns_ops indexes.
        """
        table_name = 'postgres_tests_chartextarrayindexmodel'
        call_command('migrate', 'postgres_tests', verbosity=0)
        with connection.cursor() as cursor:
            like_constraint_columns_list = [
                v['columns']
                for k, v in list(connection.introspection.get_constraints(cursor, table_name).items())
                if k.endswith('_like')
            ]
        # Only the CharField should have a LIKE index.
        self.assertEqual(like_constraint_columns_list, [['char2']])
        # All fields should have regular indexes.
        with connection.cursor() as cursor:
            indexes = [
                c['columns'][0]
                for c in connection.introspection.get_constraints(cursor, table_name).values()
                if c['index'] and len(c['columns']) == 1
            ]
        self.assertIn('char', indexes)
        self.assertIn('char2', indexes)
        self.assertIn('text', indexes)
        call_command('migrate', 'postgres_tests', 'zero', verbosity=0)
        with connection.cursor() as cursor:
            self.assertNotIn(table_name, connection.introspection.table_names(cursor))


class TestSerialization(PostgreSQLTestCase):
    test_data = (
        '[{"fields": {"field": "[\\"1\\", \\"2\\", null]"}, "model": "postgres_tests.integerarraymodel", "pk": null}]'
    )

    def test_dumping(self):
        instance = IntegerArrayModel(field=[1, 2, None])
        data = serializers.serialize('json', [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = list(serializers.deserialize('json', self.test_data))[0].object
        self.assertEqual(instance.field, [1, 2, None])


class TestValidation(PostgreSQLTestCase):

    def test_unbounded(self):
        field = ArrayField(models.IntegerField())
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([1, None], None)
        self.assertEqual(cm.exception.code, 'item_invalid')
        self.assertEqual(
            cm.exception.message % cm.exception.params,
            'Item 1 in the array did not validate: This field cannot be null.'
        )

    def test_blank_true(self):
        field = ArrayField(models.IntegerField(blank=True, null=True))
        # This should not raise a validation error
        field.clean([1, None], None)

    def test_with_size(self):
        field = ArrayField(models.IntegerField(), size=3)
        field.clean([1, 2, 3], None)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([1, 2, 3, 4], None)
        self.assertEqual(cm.exception.messages[0], 'List contains 4 items, it should contain no more than 3.')

    def test_nested_array_mismatch(self):
        field = ArrayField(ArrayField(models.IntegerField()))
        field.clean([[1, 2], [3, 4]], None)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([[1, 2], [3, 4, 5]], None)
        self.assertEqual(cm.exception.code, 'nested_array_mismatch')
        self.assertEqual(cm.exception.messages[0], 'Nested arrays must have the same length.')

    def test_with_base_field_error_params(self):
        field = ArrayField(models.CharField(max_length=2))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['abc'], None)
        self.assertEqual(len(cm.exception.error_list), 1)
        exception = cm.exception.error_list[0]
        self.assertEqual(
            exception.message,
            'Item 0 in the array did not validate: Ensure this value has at most 2 characters (it has 3).'
        )
        self.assertEqual(exception.code, 'item_invalid')
        self.assertEqual(exception.params, {'nth': 0, 'value': 'abc', 'limit_value': 2, 'show_value': 3})

    def test_with_validators(self):
        field = ArrayField(models.IntegerField(validators=[validators.MinValueValidator(1)]))
        field.clean([1, 2], None)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([0], None)
        self.assertEqual(len(cm.exception.error_list), 1)
        exception = cm.exception.error_list[0]
        self.assertEqual(
            exception.message,
            'Item 0 in the array did not validate: Ensure this value is greater than or equal to 1.'
        )
        self.assertEqual(exception.code, 'item_invalid')
        self.assertEqual(exception.params, {'nth': 0, 'value': 0, 'limit_value': 1, 'show_value': 0})


class TestSimpleFormField(PostgreSQLTestCase):

    def test_valid(self):
        field = SimpleArrayField(forms.CharField())
        value = field.clean('a,b,c')
        self.assertEqual(value, ['a', 'b', 'c'])

    def test_to_python_fail(self):
        field = SimpleArrayField(forms.IntegerField())
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,9')
        self.assertEqual(cm.exception.messages[0], 'Item 0 in the array did not validate: Enter a whole number.')

    def test_validate_fail(self):
        field = SimpleArrayField(forms.CharField(required=True))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,')
        self.assertEqual(cm.exception.messages[0], 'Item 2 in the array did not validate: This field is required.')

    def test_validate_fail_base_field_error_params(self):
        field = SimpleArrayField(forms.CharField(max_length=2))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('abc,c,defg')
        errors = cm.exception.error_list
        self.assertEqual(len(errors), 2)
        first_error = errors[0]
        self.assertEqual(
            first_error.message,
            'Item 0 in the array did not validate: Ensure this value has at most 2 characters (it has 3).'
        )
        self.assertEqual(first_error.code, 'item_invalid')
        self.assertEqual(first_error.params, {'nth': 0, 'value': 'abc', 'limit_value': 2, 'show_value': 3})
        second_error = errors[1]
        self.assertEqual(
            second_error.message,
            'Item 2 in the array did not validate: Ensure this value has at most 2 characters (it has 4).'
        )
        self.assertEqual(second_error.code, 'item_invalid')
        self.assertEqual(second_error.params, {'nth': 2, 'value': 'defg', 'limit_value': 2, 'show_value': 4})

    def test_validators_fail(self):
        field = SimpleArrayField(forms.RegexField('[a-e]{2}'))
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,bc,de')
        self.assertEqual(cm.exception.messages[0], 'Item 0 in the array did not validate: Enter a valid value.')

    def test_delimiter(self):
        field = SimpleArrayField(forms.CharField(), delimiter='|')
        value = field.clean('a|b|c')
        self.assertEqual(value, ['a', 'b', 'c'])

    def test_delimiter_with_nesting(self):
        field = SimpleArrayField(SimpleArrayField(forms.CharField()), delimiter='|')
        value = field.clean('a,b|c,d')
        self.assertEqual(value, [['a', 'b'], ['c', 'd']])

    def test_prepare_value(self):
        field = SimpleArrayField(forms.CharField())
        value = field.prepare_value(['a', 'b', 'c'])
        self.assertEqual(value, 'a,b,c')

    def test_max_length(self):
        field = SimpleArrayField(forms.CharField(), max_length=2)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,c')
        self.assertEqual(cm.exception.messages[0], 'List contains 3 items, it should contain no more than 2.')

    def test_min_length(self):
        field = SimpleArrayField(forms.CharField(), min_length=4)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('a,b,c')
        self.assertEqual(cm.exception.messages[0], 'List contains 3 items, it should contain no fewer than 4.')

    def test_required(self):
        field = SimpleArrayField(forms.CharField(), required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('')
        self.assertEqual(cm.exception.messages[0], 'This field is required.')

    def test_model_field_formfield(self):
        model_field = ArrayField(models.CharField(max_length=27))
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleArrayField)
        self.assertIsInstance(form_field.base_field, forms.CharField)
        self.assertEqual(form_field.base_field.max_length, 27)

    def test_model_field_formfield_size(self):
        model_field = ArrayField(models.CharField(max_length=27), size=4)
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, SimpleArrayField)
        self.assertEqual(form_field.max_length, 4)

    def test_already_converted_value(self):
        field = SimpleArrayField(forms.CharField())
        vals = ['a', 'b', 'c']
        self.assertEqual(field.clean(vals), vals)


class TestSplitFormField(PostgreSQLTestCase):

    def test_valid(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), size=3)

        data = {'array_0': 'a', 'array_1': 'b', 'array_2': 'c'}
        form = SplitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data, {'array': ['a', 'b', 'c']})

    def test_required(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), required=True, size=3)

        data = {'array_0': '', 'array_1': '', 'array_2': ''}
        form = SplitForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'array': ['This field is required.']})

    def test_remove_trailing_nulls(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(required=False), size=5, remove_trailing_nulls=True)

        data = {'array_0': 'a', 'array_1': '', 'array_2': 'b', 'array_3': '', 'array_4': ''}
        form = SplitForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data, {'array': ['a', '', 'b']})

    def test_remove_trailing_nulls_not_required(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(
                forms.CharField(required=False),
                size=2,
                remove_trailing_nulls=True,
                required=False,
            )

        data = {'array_0': '', 'array_1': ''}
        form = SplitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data, {'array': []})

    def test_required_field(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), size=3)

        data = {'array_0': 'a', 'array_1': 'b', 'array_2': ''}
        form = SplitForm(data)
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors, {'array': ['Item 2 in the array did not validate: This field is required.']})

    def test_invalid_integer(self):
        msg = 'Item 1 in the array did not validate: Ensure this value is less than or equal to 100.'
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            SplitArrayField(forms.IntegerField(max_value=100), size=2).clean([0, 101])

    def test_rendering(self):
        class SplitForm(forms.Form):
            array = SplitArrayField(forms.CharField(), size=3)

        self.assertHTMLEqual(str(SplitForm()), '''
            <tr>
                <th><label for="id_array_0">Array:</label></th>
                <td>
                    <input id="id_array_0" name="array_0" type="text" required />
                    <input id="id_array_1" name="array_1" type="text" required />
                    <input id="id_array_2" name="array_2" type="text" required />
                </td>
            </tr>
        ''')

    def test_invalid_char_length(self):
        field = SplitArrayField(forms.CharField(max_length=2), size=3)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['abc', 'c', 'defg'])
        self.assertEqual(cm.exception.messages, [
            'Item 0 in the array did not validate: Ensure this value has at most 2 characters (it has 3).',
            'Item 2 in the array did not validate: Ensure this value has at most 2 characters (it has 4).',
        ])

    def test_splitarraywidget_value_omitted_from_data(self):
        class Form(forms.ModelForm):
            field = SplitArrayField(forms.IntegerField(), required=False, size=2)

            class Meta:
                model = IntegerArrayModel
                fields = ('field',)

        form = Form({'field_0': '1', 'field_1': '2'})
        self.assertEqual(form.errors, {})
        obj = form.save(commit=False)
        self.assertEqual(obj.field, [1, 2])


class TestSplitFormWidget(PostgreSQLTestCase):

    def test_value_omitted_from_data(self):
        widget = SplitArrayWidget(forms.TextInput(), size=2)
        self.assertIs(widget.value_omitted_from_data({}, {}, 'field'), True)
        self.assertIs(widget.value_omitted_from_data({'field_0': 'value'}, {}, 'field'), False)
        self.assertIs(widget.value_omitted_from_data({'field_1': 'value'}, {}, 'field'), False)
        self.assertIs(widget.value_omitted_from_data({'field_0': 'value', 'field_1': 'value'}, {}, 'field'), False)
