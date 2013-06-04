from __future__ import absolute_import

from datetime import date
import traceback
import warnings

from django.db import IntegrityError, DatabaseError
from django.utils.encoding import DjangoUnicodeDecodeError
from django.test import TestCase, TransactionTestCase

from .models import DefaultPerson, Person, ManualPrimaryKeyTest, Profile, Tag, Thing


class GetOrCreateTests(TestCase):

    def test_get_or_create(self):
        p = Person.objects.create(
            first_name='John', last_name='Lennon', birthday=date(1940, 10, 9)
        )

        p, created = Person.objects.get_or_create(
            first_name="John", last_name="Lennon", defaults={
                "birthday": date(1940, 10, 9)
            }
        )
        self.assertFalse(created)
        self.assertEqual(Person.objects.count(), 1)

        p, created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        self.assertTrue(created)
        self.assertEqual(Person.objects.count(), 2)

        # If we execute the exact same statement, it won't create a Person.
        p, created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        self.assertFalse(created)
        self.assertEqual(Person.objects.count(), 2)

        # If you don't specify a value or default value for all required
        # fields, you will get an error.
        self.assertRaises(IntegrityError,
            Person.objects.get_or_create, first_name="Tom", last_name="Smith"
        )

        # If you specify an existing primary key, but different other fields,
        # then you will get an error and data will not be updated.
        m = ManualPrimaryKeyTest.objects.create(id=1, data="Original")
        self.assertRaises(IntegrityError,
            ManualPrimaryKeyTest.objects.get_or_create, id=1, data="Different"
        )
        self.assertEqual(ManualPrimaryKeyTest.objects.get(id=1).data, "Original")

        # get_or_create should raise IntegrityErrors with the full traceback.
        # This is tested by checking that a known method call is in the traceback.
        # We cannot use assertRaises/assertRaises here because we need to inspect
        # the actual traceback. Refs #16340.
        try:
            ManualPrimaryKeyTest.objects.get_or_create(id=1, data="Different")
        except IntegrityError as e:
            formatted_traceback = traceback.format_exc()
            self.assertIn('obj.save', formatted_traceback)

    def test_savepoint_rollback(self):
        # Regression test for #20463: the database connection should still be
        # usable after a DataError or ProgrammingError in .get_or_create().
        try:
            # Hide warnings when broken data is saved with a warning (MySQL).
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                Person.objects.get_or_create(
                    birthday=date(1970, 1, 1),
                    defaults={'first_name': b"\xff", 'last_name': b"\xff"})
        except (DatabaseError, DjangoUnicodeDecodeError):
            Person.objects.create(
                first_name="Bob", last_name="Ross", birthday=date(1950, 1, 1))
        else:
            self.skipTest("This backend accepts broken utf-8.")

    def test_get_or_create_empty(self):
        # Regression test for #16137: get_or_create does not require kwargs.
        try:
            DefaultPerson.objects.get_or_create()
        except AssertionError:
            self.fail("If all the attributes on a model have defaults, we "
                      "shouldn't need to pass any arguments.")


class GetOrCreateTransactionTests(TransactionTestCase):

    available_apps = ['get_or_create']

    def test_get_or_create_integrityerror(self):
        # Regression test for #15117. Requires a TransactionTestCase on
        # databases that delay integrity checks until the end of transactions,
        # otherwise the exception is never raised.
        try:
            Profile.objects.get_or_create(person=Person(id=1))
        except IntegrityError:
            pass
        else:
            self.skipTest("This backend does not support integrity checks.")


class GetOrCreateThroughManyToMany(TestCase):

    def test_get_get_or_create(self):
        tag = Tag.objects.create(text='foo')
        a_thing = Thing.objects.create(name='a')
        a_thing.tags.add(tag)
        obj, created = a_thing.tags.get_or_create(text='foo')

        self.assertFalse(created)
        self.assertEqual(obj.pk, tag.pk)

    def test_create_get_or_create(self):
        a_thing = Thing.objects.create(name='a')
        obj, created = a_thing.tags.get_or_create(text='foo')

        self.assertTrue(created)
        self.assertEqual(obj.text, 'foo')
        self.assertIn(obj, a_thing.tags.all())

    def test_something(self):
        Tag.objects.create(text='foo')
        a_thing = Thing.objects.create(name='a')
        self.assertRaises(IntegrityError, a_thing.tags.get_or_create, text='foo')
