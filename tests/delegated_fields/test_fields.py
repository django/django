import unittest

from django.db import NotSupportedError, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from .models import (
    DelegatedWithDBDefault, OnlyDelegatedFields, PartiallyDelegated,
    WithDelegatedFields,
)

DB_NONE = '' if connection.features.interprets_empty_strings_as_nulls else None


class DatabaseNoneAssertMixin(object):

    def assertIsDBNone(self, value):
        self.assertEqual(value, DB_NONE)

    def assertIsNotDBNone(self, value):
        self.assertNotEqual(value, DB_NONE)


class DelegatedFieldsTestCase(TestCase, DatabaseNoneAssertMixin):

    def test_delegated(self):
        obj = WithDelegatedFields.objects.create(a="John")
        obj.refresh_from_db()
        self.assertIsDBNone(obj.a)
        obj.a = "Lorem Ipsum"
        obj.save()
        obj.refresh_from_db()
        self.assertIsDBNone(obj.a)

    def test_model_with_only_delegated_fields(self):
        obj = OnlyDelegatedFields.objects.create(a="John")
        obj.refresh_from_db()
        self.assertIsDBNone(obj.a)
        self.assertRaises(NotSupportedError, obj.save)

    def test_ignore_delegated_fields(self):
        obj = OnlyDelegatedFields.objects.create(a="John")
        obj.refresh_from_db()
        self.assertIsDBNone(obj.a)
        obj.a = "Lorem Ipsum"
        obj.save(ignore_delegated=['a'])
        self.assertEqual(obj.a, "Lorem Ipsum")

        obj.refresh_from_db()
        self.assertEqual(obj.a, "Lorem Ipsum")


class TestQuerySetMethods(TestCase, DatabaseNoneAssertMixin):

    def test_create(self):
        p = PartiallyDelegated.objects.create()
        p.refresh_from_db()
        self.assertIsNone(p.insert)
        self.assertIsNone(p.update)
        self.assertIsNone(p.both)

        p = PartiallyDelegated.objects.create(insert=1, update=1, both=1)
        p.refresh_from_db()
        self.assertIsNone(p.insert)
        self.assertEqual(p.update, 1)
        self.assertIsNone(p.both)

    def test_ignore_with_create(self):
        p = PartiallyDelegated.objects.ignore_delegated('insert').create(insert=1, update=1, both=1)
        p.refresh_from_db()
        self.assertEqual(p.insert, 1)
        self.assertEqual(p.update, 1)
        self.assertIsNone(p.both)

        p = PartiallyDelegated.objects.ignore_delegated('insert', 'both').create(insert=1, update=1, both=1)
        self.assertEqual(p.insert, 1)
        self.assertEqual(p.update, 1)
        self.assertEqual(p.both, 1)

    def test_update(self):
        for i in range(10):
            PartiallyDelegated.objects.ignore_delegated(
                'insert', 'both').create(insert=1, update=1, both=1)
        affected = PartiallyDelegated.objects.update(insert=2)
        self.assertEqual(affected, 10)
        self.assertEqual(PartiallyDelegated.objects.filter(insert=2).count(), 10)

        affected = PartiallyDelegated.objects.update(update=2, both=2)
        self.assertEqual(affected, 0)
        self.assertEqual(PartiallyDelegated.objects.filter(update=2).count(), 0)
        self.assertEqual(PartiallyDelegated.objects.filter(both=2).count(), 0)

        affected = PartiallyDelegated.objects.ignore_delegated('update').update(update=2)
        self.assertEqual(affected, 10)
        self.assertEqual(PartiallyDelegated.objects.filter(update=2).count(), 10)
        self.assertEqual(PartiallyDelegated.objects.filter(both=2).count(), 0)

        affected = PartiallyDelegated.objects.ignore_delegated('both').update(both=2)
        self.assertEqual(affected, 10)
        self.assertEqual(PartiallyDelegated.objects.filter(both=2).count(), 10)


@unittest.skipUnless(connection.features.can_return_multiple_values,
                     "Tests for backends that support returning values")
class ReturningFieldsTestCase(TransactionTestCase, DatabaseNoneAssertMixin):

    available_apps = ['delegated_fields']

    def test_delegated_with_db_defaults(self):
        '''
        Trigger sets now to current date
        '''
        now = timezone.now()
        obj = DelegatedWithDBDefault.objects.create()
        self.assertIsNotDBNone(obj.now)
        self.assertTrue(obj.now >= now)

    def test_returning_values_with_trigger(self):
        '''
        Database trigger set the `num` field to 0 if num is NULL.
        If num is not null, it doubles and sets the provided value
        '''
        obj = DelegatedWithDBDefault.objects.create()
        self.assertEqual(obj.num, 0)

        obj.num = 100
        obj.save()

        self.assertEqual(obj.num, 200)

    def test_return_on_insert(self):
        '''
        num_a is always set to 1 by database
        '''
        obj = DelegatedWithDBDefault.objects.create()
        self.assertEqual(obj.num_a, 1)

        obj.num_a = 2
        obj.save()
        self.assertEqual(obj.num_a, 2)

    def test_return_on_update(self):
        '''
        num_b is always set to 1 by database
        '''
        obj = DelegatedWithDBDefault.objects.create()
        self.assertEqual(obj.num_b, None)

        obj.num_b = 2
        obj.save()
        self.assertEqual(obj.num_b, 1)
