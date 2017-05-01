import time
import traceback
from datetime import date, datetime, timedelta
from threading import Thread

from django.core.exceptions import FieldError
from django.db import DatabaseError, IntegrityError, connection
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, skipUnlessDBFeature,
)

from .models import (
    Author, Book, DefaultPerson, ManualPrimaryKeyTest, Person, Profile,
    Publisher, Tag, Thing,
)


class GetOrCreateTests(TestCase):

    def setUp(self):
        self.lennon = Person.objects.create(
            first_name='John', last_name='Lennon', birthday=date(1940, 10, 9)
        )

    def test_get_or_create_method_with_get(self):
        created = Person.objects.get_or_create(
            first_name="John", last_name="Lennon", defaults={
                "birthday": date(1940, 10, 9)
            }
        )[1]
        self.assertFalse(created)
        self.assertEqual(Person.objects.count(), 1)

    def test_get_or_create_method_with_create(self):
        created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )[1]
        self.assertTrue(created)
        self.assertEqual(Person.objects.count(), 2)

    def test_get_or_create_redundant_instance(self):
        """
        If we execute the exact same statement twice, the second time,
        it won't create a Person.
        """
        Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )
        created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults={
                'birthday': date(1943, 2, 25)
            }
        )[1]

        self.assertFalse(created)
        self.assertEqual(Person.objects.count(), 2)

    def test_get_or_create_invalid_params(self):
        """
        If you don't specify a value or default value for all required
        fields, you will get an error.
        """
        with self.assertRaises(IntegrityError):
            Person.objects.get_or_create(first_name="Tom", last_name="Smith")

    def test_get_or_create_with_pk_property(self):
        """
        Using the pk property of a model is allowed.
        """
        Thing.objects.get_or_create(pk=1)

    def test_get_or_create_on_related_manager(self):
        p = Publisher.objects.create(name="Acme Publishing")
        # Create a book through the publisher.
        book, created = p.books.get_or_create(name="The Book of Ed & Fred")
        self.assertTrue(created)
        # The publisher should have one book.
        self.assertEqual(p.books.count(), 1)

        # Try get_or_create again, this time nothing should be created.
        book, created = p.books.get_or_create(name="The Book of Ed & Fred")
        self.assertFalse(created)
        # And the publisher should still have one book.
        self.assertEqual(p.books.count(), 1)

        # Add an author to the book.
        ed, created = book.authors.get_or_create(name="Ed")
        self.assertTrue(created)
        # The book should have one author.
        self.assertEqual(book.authors.count(), 1)

        # Try get_or_create again, this time nothing should be created.
        ed, created = book.authors.get_or_create(name="Ed")
        self.assertFalse(created)
        # And the book should still have one author.
        self.assertEqual(book.authors.count(), 1)

        # Add a second author to the book.
        fred, created = book.authors.get_or_create(name="Fred")
        self.assertTrue(created)

        # The book should have two authors now.
        self.assertEqual(book.authors.count(), 2)

        # Create an Author not tied to any books.
        Author.objects.create(name="Ted")

        # There should be three Authors in total. The book object should have two.
        self.assertEqual(Author.objects.count(), 3)
        self.assertEqual(book.authors.count(), 2)

        # Try creating a book through an author.
        _, created = ed.books.get_or_create(name="Ed's Recipes", publisher=p)
        self.assertTrue(created)

        # Now Ed has two Books, Fred just one.
        self.assertEqual(ed.books.count(), 2)
        self.assertEqual(fred.books.count(), 1)

        # Use the publisher's primary key value instead of a model instance.
        _, created = ed.books.get_or_create(name='The Great Book of Ed', publisher_id=p.id)
        self.assertTrue(created)

        # Try get_or_create again, this time nothing should be created.
        _, created = ed.books.get_or_create(name='The Great Book of Ed', publisher_id=p.id)
        self.assertFalse(created)

        # The publisher should have three books.
        self.assertEqual(p.books.count(), 3)

    def test_defaults_exact(self):
        """
        If you have a field named defaults and want to use it as an exact
        lookup, you need to use 'defaults__exact'.
        """
        obj, created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults__exact='testing', defaults={
                'birthday': date(1943, 2, 25),
                'defaults': 'testing',
            }
        )
        self.assertTrue(created)
        self.assertEqual(obj.defaults, 'testing')
        obj2, created = Person.objects.get_or_create(
            first_name='George', last_name='Harrison', defaults__exact='testing', defaults={
                'birthday': date(1943, 2, 25),
                'defaults': 'testing',
            }
        )
        self.assertFalse(created)
        self.assertEqual(obj, obj2)

    def test_callable_defaults(self):
        """
        Callables in `defaults` are evaluated if the instance is created.
        """
        obj, created = Person.objects.get_or_create(
            first_name="George",
            defaults={"last_name": "Harrison", "birthday": lambda: date(1943, 2, 25)},
        )
        self.assertTrue(created)
        self.assertEqual(date(1943, 2, 25), obj.birthday)

    def test_callable_defaults_not_called(self):
        def raise_exception():
            raise AssertionError
        obj, created = Person.objects.get_or_create(
            first_name="John", last_name="Lennon",
            defaults={"birthday": lambda: raise_exception()},
        )


class GetOrCreateTestsWithManualPKs(TestCase):

    def setUp(self):
        self.first_pk = ManualPrimaryKeyTest.objects.create(id=1, data="Original")

    def test_create_with_duplicate_primary_key(self):
        """
        If you specify an existing primary key, but different other fields,
        then you will get an error and data will not be updated.
        """
        with self.assertRaises(IntegrityError):
            ManualPrimaryKeyTest.objects.get_or_create(id=1, data="Different")
        self.assertEqual(ManualPrimaryKeyTest.objects.get(id=1).data, "Original")

    def test_get_or_create_raises_IntegrityError_plus_traceback(self):
        """
        get_or_create should raise IntegrityErrors with the full traceback.
        This is tested by checking that a known method call is in the traceback.
        We cannot use assertRaises here because we need to inspect
        the actual traceback. Refs #16340.
        """
        try:
            ManualPrimaryKeyTest.objects.get_or_create(id=1, data="Different")
        except IntegrityError:
            formatted_traceback = traceback.format_exc()
            self.assertIn('obj.save', formatted_traceback)

    def test_savepoint_rollback(self):
        """
        The database connection is still usable after a DatabaseError in
        get_or_create() (#20463).
        """
        Tag.objects.create(text='foo')
        with self.assertRaises(DatabaseError):
            # pk 123456789 doesn't exist, so the tag object will be created.
            # Saving triggers a unique constraint violation on 'text'.
            Tag.objects.get_or_create(pk=123456789, defaults={'text': 'foo'})
        # Tag objects can be created after the error.
        Tag.objects.create(text='bar')

    def test_get_or_create_empty(self):
        """
        If all the attributes on a model have defaults, get_or_create() doesn't
        require any arguments.
        """
        DefaultPerson.objects.get_or_create()


class GetOrCreateTransactionTests(TransactionTestCase):

    available_apps = ['get_or_create']

    def test_get_or_create_integrityerror(self):
        """
        Regression test for #15117. Requires a TransactionTestCase on
        databases that delay integrity checks until the end of transactions,
        otherwise the exception is never raised.
        """
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
        with self.assertRaises(IntegrityError):
            a_thing.tags.get_or_create(text='foo')


class UpdateOrCreateTests(TestCase):

    def test_update(self):
        Person.objects.create(
            first_name='John', last_name='Lennon', birthday=date(1940, 10, 9)
        )
        p, created = Person.objects.update_or_create(
            first_name='John', last_name='Lennon', defaults={
                'birthday': date(1940, 10, 10)
            }
        )
        self.assertFalse(created)
        self.assertEqual(p.first_name, 'John')
        self.assertEqual(p.last_name, 'Lennon')
        self.assertEqual(p.birthday, date(1940, 10, 10))

    def test_create(self):
        p, created = Person.objects.update_or_create(
            first_name='John', last_name='Lennon', defaults={
                'birthday': date(1940, 10, 10)
            }
        )
        self.assertTrue(created)
        self.assertEqual(p.first_name, 'John')
        self.assertEqual(p.last_name, 'Lennon')
        self.assertEqual(p.birthday, date(1940, 10, 10))

    def test_create_twice(self):
        params = {
            'first_name': 'John',
            'last_name': 'Lennon',
            'birthday': date(1940, 10, 10),
        }
        Person.objects.update_or_create(**params)
        # If we execute the exact same statement, it won't create a Person.
        p, created = Person.objects.update_or_create(**params)
        self.assertFalse(created)

    def test_integrity(self):
        """
        If you don't specify a value or default value for all required
        fields, you will get an error.
        """
        with self.assertRaises(IntegrityError):
            Person.objects.update_or_create(first_name="Tom", last_name="Smith")

    def test_manual_primary_key_test(self):
        """
        If you specify an existing primary key, but different other fields,
        then you will get an error and data will not be updated.
        """
        ManualPrimaryKeyTest.objects.create(id=1, data="Original")
        with self.assertRaises(IntegrityError):
            ManualPrimaryKeyTest.objects.update_or_create(id=1, data="Different")
        self.assertEqual(ManualPrimaryKeyTest.objects.get(id=1).data, "Original")

    def test_with_pk_property(self):
        """
        Using the pk property of a model is allowed.
        """
        Thing.objects.update_or_create(pk=1)

    def test_error_contains_full_traceback(self):
        """
        update_or_create should raise IntegrityErrors with the full traceback.
        This is tested by checking that a known method call is in the traceback.
        We cannot use assertRaises/assertRaises here because we need to inspect
        the actual traceback. Refs #16340.
        """
        try:
            ManualPrimaryKeyTest.objects.update_or_create(id=1, data="Different")
        except IntegrityError:
            formatted_traceback = traceback.format_exc()
            self.assertIn('obj.save', formatted_traceback)

    def test_create_with_related_manager(self):
        """
        Should be able to use update_or_create from the related manager to
        create a book. Refs #23611.
        """
        p = Publisher.objects.create(name="Acme Publishing")
        book, created = p.books.update_or_create(name="The Book of Ed & Fred")
        self.assertTrue(created)
        self.assertEqual(p.books.count(), 1)

    def test_update_with_related_manager(self):
        """
        Should be able to use update_or_create from the related manager to
        update a book. Refs #23611.
        """
        p = Publisher.objects.create(name="Acme Publishing")
        book = Book.objects.create(name="The Book of Ed & Fred", publisher=p)
        self.assertEqual(p.books.count(), 1)
        name = "The Book of Django"
        book, created = p.books.update_or_create(defaults={'name': name}, id=book.id)
        self.assertFalse(created)
        self.assertEqual(book.name, name)
        self.assertEqual(p.books.count(), 1)

    def test_create_with_many(self):
        """
        Should be able to use update_or_create from the m2m related manager to
        create a book. Refs #23611.
        """
        p = Publisher.objects.create(name="Acme Publishing")
        author = Author.objects.create(name="Ted")
        book, created = author.books.update_or_create(name="The Book of Ed & Fred", publisher=p)
        self.assertTrue(created)
        self.assertEqual(author.books.count(), 1)

    def test_update_with_many(self):
        """
        Should be able to use update_or_create from the m2m related manager to
        update a book. Refs #23611.
        """
        p = Publisher.objects.create(name="Acme Publishing")
        author = Author.objects.create(name="Ted")
        book = Book.objects.create(name="The Book of Ed & Fred", publisher=p)
        book.authors.add(author)
        self.assertEqual(author.books.count(), 1)
        name = "The Book of Django"
        book, created = author.books.update_or_create(defaults={'name': name}, id=book.id)
        self.assertFalse(created)
        self.assertEqual(book.name, name)
        self.assertEqual(author.books.count(), 1)

    def test_defaults_exact(self):
        """
        If you have a field named defaults and want to use it as an exact
        lookup, you need to use 'defaults__exact'.
        """
        obj, created = Person.objects.update_or_create(
            first_name='George', last_name='Harrison', defaults__exact='testing', defaults={
                'birthday': date(1943, 2, 25),
                'defaults': 'testing',
            }
        )
        self.assertTrue(created)
        self.assertEqual(obj.defaults, 'testing')
        obj, created = Person.objects.update_or_create(
            first_name='George', last_name='Harrison', defaults__exact='testing', defaults={
                'birthday': date(1943, 2, 25),
                'defaults': 'another testing',
            }
        )
        self.assertFalse(created)
        self.assertEqual(obj.defaults, 'another testing')

    def test_create_callable_default(self):
        obj, created = Person.objects.update_or_create(
            first_name='George', last_name='Harrison',
            defaults={'birthday': lambda: date(1943, 2, 25)},
        )
        self.assertIs(created, True)
        self.assertEqual(obj.birthday, date(1943, 2, 25))

    def test_update_callable_default(self):
        Person.objects.update_or_create(
            first_name='George', last_name='Harrison', birthday=date(1942, 2, 25),
        )
        obj, created = Person.objects.update_or_create(
            first_name='George',
            defaults={'last_name': lambda: 'NotHarrison'},
        )
        self.assertIs(created, False)
        self.assertEqual(obj.last_name, 'NotHarrison')


class UpdateOrCreateTransactionTests(TransactionTestCase):
    available_apps = ['get_or_create']

    @skipUnlessDBFeature('has_select_for_update')
    @skipUnlessDBFeature('supports_transactions')
    def test_updates_in_transaction(self):
        """
        Objects are selected and updated in a transaction to avoid race
        conditions. This test forces update_or_create() to hold the lock
        in another thread for a relatively long time so that it can update
        while it holds the lock. The updated field isn't a field in 'defaults',
        so update_or_create() shouldn't have an effect on it.
        """
        lock_status = {'has_grabbed_lock': False}

        def birthday_sleep():
            lock_status['has_grabbed_lock'] = True
            time.sleep(0.5)
            return date(1940, 10, 10)

        def update_birthday_slowly():
            Person.objects.update_or_create(
                first_name='John', defaults={'birthday': birthday_sleep}
            )
            # Avoid leaking connection for Oracle
            connection.close()

        def lock_wait():
            # timeout after ~0.5 seconds
            for i in range(20):
                time.sleep(0.025)
                if lock_status['has_grabbed_lock']:
                    return True
            return False

        Person.objects.create(first_name='John', last_name='Lennon', birthday=date(1940, 10, 9))

        # update_or_create in a separate thread
        t = Thread(target=update_birthday_slowly)
        before_start = datetime.now()
        t.start()

        if not lock_wait():
            self.skipTest('Database took too long to lock the row')

        # Update during lock
        Person.objects.filter(first_name='John').update(last_name='NotLennon')
        after_update = datetime.now()

        # Wait for thread to finish
        t.join()

        # The update remains and it blocked.
        updated_person = Person.objects.get(first_name='John')
        self.assertGreater(after_update - before_start, timedelta(seconds=0.5))
        self.assertEqual(updated_person.last_name, 'NotLennon')


class InvalidCreateArgumentsTests(SimpleTestCase):
    msg = "Invalid field name(s) for model Thing: 'nonexistent'."

    def test_get_or_create_with_invalid_defaults(self):
        with self.assertRaisesMessage(FieldError, self.msg):
            Thing.objects.get_or_create(name='a', defaults={'nonexistent': 'b'})

    def test_get_or_create_with_invalid_kwargs(self):
        with self.assertRaisesMessage(FieldError, self.msg):
            Thing.objects.get_or_create(name='a', nonexistent='b')

    def test_update_or_create_with_invalid_defaults(self):
        with self.assertRaisesMessage(FieldError, self.msg):
            Thing.objects.update_or_create(name='a', defaults={'nonexistent': 'b'})

    def test_update_or_create_with_invalid_kwargs(self):
        with self.assertRaisesMessage(FieldError, self.msg):
            Thing.objects.update_or_create(name='a', nonexistent='b')

    def test_multiple_invalid_fields(self):
        with self.assertRaisesMessage(FieldError, "Invalid field name(s) for model Thing: 'invalid', 'nonexistent'"):
            Thing.objects.update_or_create(name='a', nonexistent='b', defaults={'invalid': 'c'})
