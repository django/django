import unittest

from django.contrib.postgres.fields import ArrayField
from django.core import exceptions, serializers
from django.db import models, IntegrityError, connection
from django.db.migrations.writer import MigrationWriter
from django.test import TestCase
from django.utils import timezone

from .models import IntegerArrayModel, NullableIntegerArrayModel, CharArrayModel, DateTimeArrayModel


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL required')
class TestSaveLoad(TestCase):

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
        instance = DateTimeArrayModel(field=[timezone.now()])
        instance.save()
        loaded = DateTimeArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

    def test_integers_passed_as_strings(self):
        # This checks that get_prep_value is deferred properly
        instance = IntegerArrayModel(field=['1'])
        instance.save()
        loaded = IntegerArrayModel.objects.get()
        self.assertEqual(loaded.field, [1])

    def test_null_handling(self):
        instance = NullableIntegerArrayModel(field=None)
        instance.save()
        loaded = NullableIntegerArrayModel.objects.get()
        self.assertEqual(instance.field, loaded.field)

        instance = IntegerArrayModel(field=None)
        with self.assertRaises(IntegrityError):
            instance.save()


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL required')
class TestQuerying(TestCase):

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

    def test_contains(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__contains=[2]),
            self.objs[1:3]
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

    def test_slice(self):
        self.assertSequenceEqual(
            NullableIntegerArrayModel.objects.filter(field__1_2=[3]),
            self.objs[2:3]
        )


class TestChecks(TestCase):

    def test_field_checks(self):
        field = ArrayField(models.CharField())
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E001')

    def test_invalid_base_fields(self):
        field = ArrayField(models.ManyToManyField('postgres_tests.IntegerArrayModel'))
        field.set_attributes_from_name('field')
        errors = field.check()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, 'postgres.E002')


class TestMigrations(TestCase):

    def test_deconstruct(self):
        field = ArrayField(models.IntegerField())
        name, path, args, kwargs = field.deconstruct()
        new = ArrayField(*args, **kwargs)
        self.assertEqual(type(new.base_field), type(field.base_field))

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

    def test_makemigrations(self):
        field = ArrayField(models.CharField(max_length=20))
        statement, imports = MigrationWriter.serialize(field)
        self.assertEqual(statement, 'django.contrib.postgres.fields.ArrayField(models.CharField(max_length=20), size=None)')


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL required')
class TestSerialization(TestCase):
    test_data = '[{"fields": {"field": "[\\"1\\", \\"2\\"]"}, "model": "postgres_tests.integerarraymodel", "pk": null}]'

    def test_dumping(self):
        instance = IntegerArrayModel(field=[1, 2])
        data = serializers.serialize('json', [instance])
        self.assertEqual(data, self.test_data)

    def test_loading(self):
        instance = list(serializers.deserialize('json', self.test_data))[0].object
        self.assertEqual(instance.field, [1, 2])


class TestValidation(TestCase):

    def test_unbounded(self):
        field = ArrayField(models.IntegerField())
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([1, None], None)
        self.assertEqual(cm.exception.code, 'item_invalid')
        self.assertEqual(cm.exception.message % cm.exception.params, 'Item 1 in the array did not validate: This field cannot be null.')

    def test_blank_true(self):
        field = ArrayField(models.IntegerField(blank=True, null=True))
        # This should not raise a validation error
        field.clean([1, None], None)

    def test_with_size(self):
        field = ArrayField(models.IntegerField(), size=3)
        field.clean([1, 2, 3], None)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([1, 2, 3, 4], None)
        self.assertEqual(cm.exception.messages[0], 'Array contains 4 items, it should contain no more than 3.')

    def test_nested_array_mismatch(self):
        field = ArrayField(ArrayField(models.IntegerField()))
        field.clean([[1, 2], [3, 4]], None)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean([[1, 2], [3, 4, 5]], None)
        self.assertEqual(cm.exception.code, 'nested_array_mismatch')
        self.assertEqual(cm.exception.messages[0], 'Nested arrays must have the same length.')
