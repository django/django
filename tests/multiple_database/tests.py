from __future__ import unicode_literals

import datetime
import pickle
import warnings
from operator import attrgetter

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core import management
from django.db import DEFAULT_DB_ALIAS, connections, router, transaction
from django.db.models import signals
from django.db.utils import ConnectionRouter
from django.test import TestCase, override_settings
from django.utils.encoding import force_text
from django.utils.six import StringIO

from .models import Book, Person, Pet, Review, UserProfile
from .routers import AuthRouter, TestRouter, WriteRouter


class QueryTestCase(TestCase):
    multi_db = True

    def test_db_selection(self):
        "Check that querysets will use the default database by default"
        self.assertEqual(Book.objects.db, DEFAULT_DB_ALIAS)
        self.assertEqual(Book.objects.all().db, DEFAULT_DB_ALIAS)

        self.assertEqual(Book.objects.using('other').db, 'other')

        self.assertEqual(Book.objects.db_manager('other').db, 'other')
        self.assertEqual(Book.objects.db_manager('other').all().db, 'other')

    def test_default_creation(self):
        "Objects created on the default database don't leak onto other databases"
        # Create a book on the default database using create()
        Book.objects.create(title="Pro Django",
                            published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title = "Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save()

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on default database')

        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on default database')

        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Dive into Python"
        )

    def test_other_creation(self):
        "Objects created on another database don't leak onto the default database"
        # Create a book on the second database
        Book.objects.using('other').create(title="Pro Django",
                                           published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title = "Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on other database')

        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
        )

        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

    def test_refresh(self):
        dive = Book()
        dive.title = "Dive into Python"
        dive = Book()
        dive.title = "Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')
        dive2 = Book.objects.using('other').get()
        dive2.title = "Dive into Python (on default)"
        dive2.save(using='default')
        dive.refresh_from_db()
        self.assertEqual(dive.title, "Dive into Python")
        dive.refresh_from_db(using='default')
        self.assertEqual(dive.title, "Dive into Python (on default)")
        self.assertEqual(dive._state.db, "default")

    def test_basic_queries(self):
        "Queries are constrained to a single database"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        dive = Book.objects.using('other').get(published=datetime.date(2009, 5, 4))
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published=datetime.date(2009, 5, 4))

        dive = Book.objects.using('other').get(title__icontains="dive")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__icontains="dive")

        dive = Book.objects.using('other').get(title__iexact="dive INTO python")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__iexact="dive INTO python")

        dive = Book.objects.using('other').get(published__year=2009)
        self.assertEqual(dive.title, "Dive into Python")
        self.assertEqual(dive.published, datetime.date(2009, 5, 4))
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published__year=2009)

        years = Book.objects.using('other').dates('published', 'year')
        self.assertEqual([o.year for o in years], [2009])
        years = Book.objects.using('default').dates('published', 'year')
        self.assertEqual([o.year for o in years], [])

        months = Book.objects.using('other').dates('published', 'month')
        self.assertEqual([o.month for o in months], [5])
        months = Book.objects.using('default').dates('published', 'month')
        self.assertEqual([o.month for o in months], [])

    def test_m2m_separation(self):
        "M2M fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        pro.authors = [marty]
        dive.authors = [mark]

        # Inspect the m2m tables directly.
        # There should be 1 entry in each database
        self.assertEqual(Book.authors.through.objects.using('default').count(), 1)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 1)

        # Check that queries work across m2m joins
        self.assertEqual(list(Book.objects.using('default').filter(authors__name='Marty Alchin').values_list('title', flat=True)),
            ['Pro Django'])
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Marty Alchin').values_list('title', flat=True)),
            [])

        self.assertEqual(list(Book.objects.using('default').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
            [])
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
            ['Dive into Python'])

        # Reget the objects to clear caches
        dive = Book.objects.using('other').get(title="Dive into Python")
        mark = Person.objects.using('other').get(name="Mark Pilgrim")

        # Retrieve related object by descriptor. Related objects should be database-bound
        self.assertEqual(list(dive.authors.all().values_list('name', flat=True)),
            ['Mark Pilgrim'])

        self.assertEqual(list(mark.book_set.all().values_list('title', flat=True)),
            ['Dive into Python'])

    def test_m2m_forward_operations(self):
        "M2M forward manipulations are all constrained to a single DB"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        dive.authors = [mark]

        # Add a second author
        john = Person.objects.using('other').create(name="John Smith")
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
            [])

        dive.authors.add(john)
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
            ['Dive into Python'])
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
            ['Dive into Python'])

        # Remove the second author
        dive.authors.remove(john)
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
            ['Dive into Python'])
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
            [])

        # Clear all authors
        dive.authors.clear()
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
            [])
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
            [])

        # Create an author through the m2m interface
        dive.authors.create(name='Jane Brown')
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
            [])
        self.assertEqual(list(Book.objects.using('other').filter(authors__name='Jane Brown').values_list('title', flat=True)),
            ['Dive into Python'])

    def test_m2m_reverse_operations(self):
        "M2M reverse manipulations are all constrained to a single DB"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        dive.authors = [mark]

        # Create a second book on the other database
        grease = Book.objects.using('other').create(title="Greasemonkey Hacks",
                                                    published=datetime.date(2005, 11, 1))

        # Add a books to the m2m
        mark.book_set.add(grease)
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
            ['Mark Pilgrim'])
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
            ['Mark Pilgrim'])

        # Remove a book from the m2m
        mark.book_set.remove(grease)
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
            ['Mark Pilgrim'])
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
            [])

        # Clear the books associated with mark
        mark.book_set.clear()
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
            [])
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
            [])

        # Create a book through the m2m interface
        mark.book_set.create(title="Dive into HTML5", published=datetime.date(2020, 1, 1))
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
            [])
        self.assertEqual(list(Person.objects.using('other').filter(book__title='Dive into HTML5').values_list('name', flat=True)),
            ['Mark Pilgrim'])

    def test_m2m_cross_database_protection(self):
        "Operations that involve sharing M2M objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
            published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        # Set a foreign key set with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='default'):
                marty.edited = [pro, dive]

        # Add to an m2m with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='default'):
                marty.book_set.add(dive)

        # Set a m2m with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='default'):
                marty.book_set = [pro, dive]

        # Add to a reverse m2m with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='other'):
                dive.authors.add(marty)

        # Set a reverse m2m with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='other'):
                dive.authors = [mark, marty]

    def test_m2m_deletion(self):
        "Cascaded deletions of m2m relations issue queries on the right database"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        dive.authors = [mark]

        # Check the initial state
        self.assertEqual(Person.objects.using('default').count(), 0)
        self.assertEqual(Book.objects.using('default').count(), 0)
        self.assertEqual(Book.authors.through.objects.using('default').count(), 0)

        self.assertEqual(Person.objects.using('other').count(), 1)
        self.assertEqual(Book.objects.using('other').count(), 1)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 1)

        # Delete the object on the other database
        dive.delete(using='other')

        self.assertEqual(Person.objects.using('default').count(), 0)
        self.assertEqual(Book.objects.using('default').count(), 0)
        self.assertEqual(Book.authors.through.objects.using('default').count(), 0)

        # The person still exists ...
        self.assertEqual(Person.objects.using('other').count(), 1)
        # ... but the book has been deleted
        self.assertEqual(Book.objects.using('other').count(), 0)
        # ... and the relationship object has also been deleted.
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

        # Now try deletion in the reverse direction. Set up the relation again
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))
        dive.authors = [mark]

        # Check the initial state
        self.assertEqual(Person.objects.using('default').count(), 0)
        self.assertEqual(Book.objects.using('default').count(), 0)
        self.assertEqual(Book.authors.through.objects.using('default').count(), 0)

        self.assertEqual(Person.objects.using('other').count(), 1)
        self.assertEqual(Book.objects.using('other').count(), 1)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 1)

        # Delete the object on the other database
        mark.delete(using='other')

        self.assertEqual(Person.objects.using('default').count(), 0)
        self.assertEqual(Book.objects.using('default').count(), 0)
        self.assertEqual(Book.authors.through.objects.using('default').count(), 0)

        # The person has been deleted ...
        self.assertEqual(Person.objects.using('other').count(), 0)
        # ... but the book still exists
        self.assertEqual(Book.objects.using('other').count(), 1)
        # ... and the relationship object has been deleted.
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

    def test_foreign_key_separation(self):
        "FK fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        george = Person.objects.create(name="George Vilches")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        chris = Person.objects.using('other').create(name="Chris Mills")

        # Save the author's favorite books
        pro.editor = george
        pro.save()

        dive.editor = chris
        dive.save()

        pro = Book.objects.using('default').get(title="Pro Django")
        self.assertEqual(pro.editor.name, "George Vilches")

        dive = Book.objects.using('other').get(title="Dive into Python")
        self.assertEqual(dive.editor.name, "Chris Mills")

        # Check that queries work across foreign key joins
        self.assertEqual(list(Person.objects.using('default').filter(edited__title='Pro Django').values_list('name', flat=True)),
            ['George Vilches'])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Pro Django').values_list('name', flat=True)),
            [])

        self.assertEqual(list(Person.objects.using('default').filter(edited__title='Dive into Python').values_list('name', flat=True)),
            [])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
            ['Chris Mills'])

        # Reget the objects to clear caches
        chris = Person.objects.using('other').get(name="Chris Mills")
        dive = Book.objects.using('other').get(title="Dive into Python")

        # Retrieve related object by descriptor. Related objects should be database-bound
        self.assertEqual(list(chris.edited.values_list('title', flat=True)),
            ['Dive into Python'])

    def test_foreign_key_reverse_operations(self):
        "FK reverse manipulations are all constrained to a single DB"
        dive = Book.objects.using('other').create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))

        chris = Person.objects.using('other').create(name="Chris Mills")

        # Save the author relations
        dive.editor = chris
        dive.save()

        # Add a second book edited by chris
        html5 = Book.objects.using('other').create(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
            [])

        chris.edited.add(html5)
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
            ['Chris Mills'])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
            ['Chris Mills'])

        # Remove the second editor
        chris.edited.remove(html5)
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
            [])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
            ['Chris Mills'])

        # Clear all edited books
        chris.edited.clear()
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
            [])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
            [])

        # Create an author through the m2m interface
        chris.edited.create(title='Dive into Water', published=datetime.date(2010, 3, 15))
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into HTML5').values_list('name', flat=True)),
            [])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into Water').values_list('name', flat=True)),
            ['Chris Mills'])
        self.assertEqual(list(Person.objects.using('other').filter(edited__title='Dive into Python').values_list('name', flat=True)),
            [])

    def test_foreign_key_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
            published=datetime.date(2008, 12, 16))

        marty = Person.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))

        # Set a foreign key with an object from a different database
        with self.assertRaises(ValueError):
            dive.editor = marty

        # Set a foreign key set with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='default'):
                marty.edited = [pro, dive]

        # Add to a foreign key set with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='default'):
                marty.edited.add(dive)

    def test_foreign_key_deletion(self):
        "Cascaded deletions of Foreign Key relations issue queries on the right database"
        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        Pet.objects.using('other').create(name="Fido", owner=mark)

        # Check the initial state
        self.assertEqual(Person.objects.using('default').count(), 0)
        self.assertEqual(Pet.objects.using('default').count(), 0)

        self.assertEqual(Person.objects.using('other').count(), 1)
        self.assertEqual(Pet.objects.using('other').count(), 1)

        # Delete the person object, which will cascade onto the pet
        mark.delete(using='other')

        self.assertEqual(Person.objects.using('default').count(), 0)
        self.assertEqual(Pet.objects.using('default').count(), 0)

        # Both the pet and the person have been deleted from the right database
        self.assertEqual(Person.objects.using('other').count(), 0)
        self.assertEqual(Pet.objects.using('other').count(), 0)

    def test_foreign_key_validation(self):
        "ForeignKey.validate() uses the correct database"
        mickey = Person.objects.using('other').create(name="Mickey")
        pluto = Pet.objects.using('other').create(name="Pluto", owner=mickey)
        self.assertIsNone(pluto.full_clean())

    def test_o2o_separation(self):
        "OneToOne fields are constrained to a single database"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')
        alice_profile = UserProfile.objects.using('default').create(user=alice, flavor='chocolate')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')
        bob_profile = UserProfile.objects.using('other').create(user=bob, flavor='crunchy frog')

        # Retrieve related objects; queries should be database constrained
        alice = User.objects.using('default').get(username="alice")
        self.assertEqual(alice.userprofile.flavor, "chocolate")

        bob = User.objects.using('other').get(username="bob")
        self.assertEqual(bob.userprofile.flavor, "crunchy frog")

        # Check that queries work across joins
        self.assertEqual(list(User.objects.using('default').filter(userprofile__flavor='chocolate').values_list('username', flat=True)),
            ['alice'])
        self.assertEqual(list(User.objects.using('other').filter(userprofile__flavor='chocolate').values_list('username', flat=True)),
            [])

        self.assertEqual(list(User.objects.using('default').filter(userprofile__flavor='crunchy frog').values_list('username', flat=True)),
            [])
        self.assertEqual(list(User.objects.using('other').filter(userprofile__flavor='crunchy frog').values_list('username', flat=True)),
            ['bob'])

        # Reget the objects to clear caches
        alice_profile = UserProfile.objects.using('default').get(flavor='chocolate')
        bob_profile = UserProfile.objects.using('other').get(flavor='crunchy frog')

        # Retrieve related object by descriptor. Related objects should be database-bound
        self.assertEqual(alice_profile.user.username, 'alice')
        self.assertEqual(bob_profile.user.username, 'bob')

    def test_o2o_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        # Set a one-to-one relation with an object from a different database
        alice_profile = UserProfile.objects.using('default').create(user=alice, flavor='chocolate')
        with self.assertRaises(ValueError):
            bob.userprofile = alice_profile

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        bob_profile = UserProfile.objects.using('other').create(user=bob, flavor='crunchy frog')

        new_bob_profile = UserProfile(flavor="spring surprise")

        # assigning a profile requires an explicit pk as the object isn't saved
        charlie = User(pk=51, username='charlie', email='charlie@example.com')
        charlie.set_unusable_password()

        # initially, no db assigned
        self.assertEqual(new_bob_profile._state.db, None)
        self.assertEqual(charlie._state.db, None)

        # old object comes from 'other', so the new object is set to use 'other'...
        new_bob_profile.user = bob
        charlie.userprofile = bob_profile
        self.assertEqual(new_bob_profile._state.db, 'other')
        self.assertEqual(charlie._state.db, 'other')

        # ... but it isn't saved yet
        self.assertEqual(list(User.objects.using('other').values_list('username', flat=True)),
            ['bob'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor', flat=True)),
            ['crunchy frog'])

        # When saved (no using required), new objects goes to 'other'
        charlie.save()
        bob_profile.save()
        new_bob_profile.save()
        self.assertEqual(list(User.objects.using('default').values_list('username', flat=True)),
            ['alice'])
        self.assertEqual(list(User.objects.using('other').values_list('username', flat=True)),
            ['bob', 'charlie'])
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor', flat=True)),
            ['chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor', flat=True)),
            ['crunchy frog', 'spring surprise'])

        # This also works if you assign the O2O relation in the constructor
        denise = User.objects.db_manager('other').create_user('denise', 'denise@example.com')
        denise_profile = UserProfile(flavor="tofu", user=denise)

        self.assertEqual(denise_profile._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor', flat=True)),
            ['chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor', flat=True)),
            ['crunchy frog', 'spring surprise'])

        # When saved, the new profile goes to 'other'
        denise_profile.save()
        self.assertEqual(list(UserProfile.objects.using('default').values_list('flavor', flat=True)),
            ['chocolate'])
        self.assertEqual(list(UserProfile.objects.using('other').values_list('flavor', flat=True)),
            ['crunchy frog', 'spring surprise', 'tofu'])

    def test_generic_key_separation(self):
        "Generic fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        review1 = Review.objects.create(source="Python Monthly", content_object=pro)

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        review2 = Review.objects.using('other').create(source="Python Weekly", content_object=dive)

        review1 = Review.objects.using('default').get(source="Python Monthly")
        self.assertEqual(review1.content_object.title, "Pro Django")

        review2 = Review.objects.using('other').get(source="Python Weekly")
        self.assertEqual(review2.content_object.title, "Dive into Python")

        # Reget the objects to clear caches
        dive = Book.objects.using('other').get(title="Dive into Python")

        # Retrieve related object by descriptor. Related objects should be database-bound
        self.assertEqual(list(dive.reviews.all().values_list('source', flat=True)),
            ['Python Weekly'])

    def test_generic_key_reverse_operations(self):
        "Generic reverse manipulations are all constrained to a single DB"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        temp = Book.objects.using('other').create(title="Temp",
                                                  published=datetime.date(2009, 5, 4))

        review1 = Review.objects.using('other').create(source="Python Weekly", content_object=dive)
        review2 = Review.objects.using('other').create(source="Python Monthly", content_object=temp)

        self.assertEqual(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
            [])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            ['Python Weekly'])

        # Add a second review
        dive.reviews.add(review2)
        self.assertEqual(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
            [])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            ['Python Monthly', 'Python Weekly'])

        # Remove the second author
        dive.reviews.remove(review1)
        self.assertEqual(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
            [])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            ['Python Monthly'])

        # Clear all reviews
        dive.reviews.clear()
        self.assertEqual(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
            [])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            [])

        # Create an author through the generic interface
        dive.reviews.create(source='Python Daily')
        self.assertEqual(list(Review.objects.using('default').filter(object_id=dive.pk).values_list('source', flat=True)),
            [])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            ['Python Daily'])

    def test_generic_key_cross_database_protection(self):
        "Operations that involve sharing generic key objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        review1 = Review.objects.create(source="Python Monthly", content_object=pro)

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        Review.objects.using('other').create(source="Python Weekly", content_object=dive)

        # Set a foreign key with an object from a different database
        with self.assertRaises(ValueError):
            review1.content_object = dive

        # Add to a foreign key set with an object from a different database
        with self.assertRaises(ValueError):
            with transaction.atomic(using='other'):
                dive.reviews.add(review1)

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        review3 = Review(source="Python Daily")
        # initially, no db assigned
        self.assertEqual(review3._state.db, None)

        # Dive comes from 'other', so review3 is set to use 'other'...
        review3.content_object = dive
        self.assertEqual(review3._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEqual(list(Review.objects.using('default').filter(object_id=pro.pk).values_list('source', flat=True)),
            ['Python Monthly'])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            ['Python Weekly'])

        # When saved, John goes to 'other'
        review3.save()
        self.assertEqual(list(Review.objects.using('default').filter(object_id=pro.pk).values_list('source', flat=True)),
            ['Python Monthly'])
        self.assertEqual(list(Review.objects.using('other').filter(object_id=dive.pk).values_list('source', flat=True)),
            ['Python Daily', 'Python Weekly'])

    def test_generic_key_deletion(self):
        "Cascaded deletions of Generic Key relations issue queries on the right database"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))
        Review.objects.using('other').create(source="Python Weekly", content_object=dive)

        # Check the initial state
        self.assertEqual(Book.objects.using('default').count(), 0)
        self.assertEqual(Review.objects.using('default').count(), 0)

        self.assertEqual(Book.objects.using('other').count(), 1)
        self.assertEqual(Review.objects.using('other').count(), 1)

        # Delete the Book object, which will cascade onto the pet
        dive.delete(using='other')

        self.assertEqual(Book.objects.using('default').count(), 0)
        self.assertEqual(Review.objects.using('default').count(), 0)

        # Both the pet and the person have been deleted from the right database
        self.assertEqual(Book.objects.using('other').count(), 0)
        self.assertEqual(Review.objects.using('other').count(), 0)

    def test_ordering(self):
        "get_next_by_XXX commands stick to a single database"
        Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        learn = Book.objects.using('other').create(title="Learning Python",
                                                   published=datetime.date(2008, 7, 16))

        self.assertEqual(learn.get_next_by_published().title, "Dive into Python")
        self.assertEqual(dive.get_previous_by_published().title, "Learning Python")

    def test_raw(self):
        "test the raw() method across databases"
        dive = Book.objects.using('other').create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))
        val = Book.objects.db_manager("other").raw('SELECT id FROM multiple_database_book')
        self.assertQuerysetEqual(val, [dive.pk], attrgetter("pk"))

        val = Book.objects.raw('SELECT id FROM multiple_database_book').using('other')
        self.assertQuerysetEqual(val, [dive.pk], attrgetter("pk"))

    def test_select_related(self):
        "Database assignment is retained if an object is retrieved with select_related()"
        # Create a book and author on the other database
        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        Book.objects.using('other').create(title="Dive into Python",
                                           published=datetime.date(2009, 5, 4),
                                           editor=mark)

        # Retrieve the Person using select_related()
        book = Book.objects.using('other').select_related('editor').get(title="Dive into Python")

        # The editor instance should have a db state
        self.assertEqual(book.editor._state.db, 'other')

    def test_subquery(self):
        """Make sure as_sql works with subqueries and primary/replica."""
        sub = Person.objects.using('other').filter(name='fff')
        qs = Book.objects.filter(editor__in=sub)

        # When you call __str__ on the query object, it doesn't know about using
        # so it falls back to the default. If the subquery explicitly uses a
        # different database, an error should be raised.
        self.assertRaises(ValueError, str, qs.query)

        # Evaluating the query shouldn't work, either
        with self.assertRaises(ValueError):
            for obj in qs:
                pass

    def test_related_manager(self):
        "Related managers return managers, not querysets"
        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # extra_arg is removed by the BookManager's implementation of
        # create(); but the BookManager's implementation won't get called
        # unless edited returns a Manager, not a queryset
        mark.book_set.create(title="Dive into Python",
                             published=datetime.date(2009, 5, 4),
                             extra_arg=True)

        mark.book_set.get_or_create(title="Dive into Python",
                                    published=datetime.date(2009, 5, 4),
                                    extra_arg=True)

        mark.edited.create(title="Dive into Water",
                           published=datetime.date(2009, 5, 4),
                           extra_arg=True)

        mark.edited.get_or_create(title="Dive into Water",
                                  published=datetime.date(2009, 5, 4),
                                  extra_arg=True)


class ConnectionRouterTestCase(TestCase):
    @override_settings(DATABASE_ROUTERS=[
        'multiple_database.tests.TestRouter',
        'multiple_database.tests.WriteRouter'])
    def test_router_init_default(self):
        connection_router = ConnectionRouter()
        self.assertListEqual([r.__class__.__name__ for r in connection_router.routers],
                             ['TestRouter', 'WriteRouter'])

    def test_router_init_arg(self):
        connection_router = ConnectionRouter([
            'multiple_database.tests.TestRouter',
            'multiple_database.tests.WriteRouter'
        ])
        self.assertListEqual([r.__class__.__name__ for r in connection_router.routers],
                             ['TestRouter', 'WriteRouter'])

        # Init with instances instead of strings
        connection_router = ConnectionRouter([TestRouter(), WriteRouter()])
        self.assertListEqual([r.__class__.__name__ for r in connection_router.routers],
                             ['TestRouter', 'WriteRouter'])


# Make the 'other' database appear to be a replica of the 'default'
@override_settings(DATABASE_ROUTERS=[TestRouter()])
class RouterTestCase(TestCase):
    multi_db = True

    def test_db_selection(self):
        "Check that querysets obey the router for db suggestions"
        self.assertEqual(Book.objects.db, 'other')
        self.assertEqual(Book.objects.all().db, 'other')

        self.assertEqual(Book.objects.using('default').db, 'default')

        self.assertEqual(Book.objects.db_manager('default').db, 'default')
        self.assertEqual(Book.objects.db_manager('default').all().db, 'default')

    def test_migrate_selection(self):
        "Synchronization behavior is predictable"

        self.assertTrue(router.allow_migrate_model('default', User))
        self.assertTrue(router.allow_migrate_model('default', Book))

        self.assertTrue(router.allow_migrate_model('other', User))
        self.assertTrue(router.allow_migrate_model('other', Book))

        with override_settings(DATABASE_ROUTERS=[TestRouter(), AuthRouter()]):
            # Add the auth router to the chain. TestRouter is a universal
            # synchronizer, so it should have no effect.
            self.assertTrue(router.allow_migrate_model('default', User))
            self.assertTrue(router.allow_migrate_model('default', Book))

            self.assertTrue(router.allow_migrate_model('other', User))
            self.assertTrue(router.allow_migrate_model('other', Book))

        with override_settings(DATABASE_ROUTERS=[AuthRouter(), TestRouter()]):
            # Now check what happens if the router order is reversed.
            self.assertFalse(router.allow_migrate_model('default', User))
            self.assertTrue(router.allow_migrate_model('default', Book))

            self.assertTrue(router.allow_migrate_model('other', User))
            self.assertTrue(router.allow_migrate_model('other', Book))

    def test_migrate_legacy_router(self):
        class LegacyRouter(object):
            def allow_migrate(self, db, model):
                """
                Deprecated allow_migrate signature should trigger
                RemovedInDjango110Warning.
                """
                assert db == 'default'
                assert model is User
                return True

        with override_settings(DATABASE_ROUTERS=[LegacyRouter()]):
            with warnings.catch_warnings(record=True) as recorded:
                warnings.filterwarnings('always')

                msg = (
                    "The signature of allow_migrate has changed from "
                    "allow_migrate(self, db, model) to "
                    "allow_migrate(self, db, app_label, model_name=None, **hints). "
                    "Support for the old signature will be removed in Django 1.10."
                )

                self.assertTrue(router.allow_migrate_model('default', User))
                self.assertEqual(force_text(recorded.pop().message), msg)

                self.assertEqual(recorded, [])

                self.assertTrue(router.allow_migrate('default', 'app_label'))
                self.assertEqual(force_text(recorded.pop().message), msg)

    def test_allow_syncdb_deprecation(self):
        class LegacyRouter(object):
            def allow_syncdb(self, db, model):
                assert db == 'default'
                assert model is User
                return True

        with override_settings(DATABASE_ROUTERS=[LegacyRouter()]):
            with warnings.catch_warnings(record=True) as recorded:
                warnings.filterwarnings('always')
                msg = (
                    "Router.allow_syncdb has been deprecated and will stop "
                    "working in Django 1.9. Rename the method to allow_migrate."
                )
                self.assertTrue(router.allow_migrate_model('default', User))
                self.assertEqual(force_text(recorded.pop().message), msg)
                self.assertEqual(recorded, [])

                self.assertTrue(router.allow_migrate('default', 'app_label'))
                self.assertEqual(force_text(recorded.pop().message), msg)

    def test_partial_router(self):
        "A router can choose to implement a subset of methods"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        # First check the baseline behavior.

        self.assertEqual(router.db_for_read(User), 'other')
        self.assertEqual(router.db_for_read(Book), 'other')

        self.assertEqual(router.db_for_write(User), 'default')
        self.assertEqual(router.db_for_write(Book), 'default')

        self.assertTrue(router.allow_relation(dive, dive))

        self.assertTrue(router.allow_migrate_model('default', User))
        self.assertTrue(router.allow_migrate_model('default', Book))

        with override_settings(DATABASE_ROUTERS=[WriteRouter(), AuthRouter(), TestRouter()]):
            self.assertEqual(router.db_for_read(User), 'default')
            self.assertEqual(router.db_for_read(Book), 'other')

            self.assertEqual(router.db_for_write(User), 'writer')
            self.assertEqual(router.db_for_write(Book), 'writer')

            self.assertTrue(router.allow_relation(dive, dive))

            self.assertFalse(router.allow_migrate_model('default', User))
            self.assertTrue(router.allow_migrate_model('default', Book))

    def test_database_routing(self):
        marty = Person.objects.using('default').create(name="Marty Alchin")
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16),
                                                   editor=marty)
        pro.authors = [marty]

        # Create a book and author on the other database
        Book.objects.using('other').create(title="Dive into Python",
                                           published=datetime.date(2009, 5, 4))

        # An update query will be routed to the default database
        Book.objects.filter(title='Pro Django').update(pages=200)

        with self.assertRaises(Book.DoesNotExist):
            # By default, the get query will be directed to 'other'
            Book.objects.get(title='Pro Django')

        # But the same query issued explicitly at a database will work.
        pro = Book.objects.using('default').get(title='Pro Django')

        # Check that the update worked.
        self.assertEqual(pro.pages, 200)

        # An update query with an explicit using clause will be routed
        # to the requested database.
        Book.objects.using('other').filter(title='Dive into Python').update(pages=300)
        self.assertEqual(Book.objects.get(title='Dive into Python').pages, 300)

        # Related object queries stick to the same database
        # as the original object, regardless of the router
        self.assertEqual(list(pro.authors.values_list('name', flat=True)), ['Marty Alchin'])
        self.assertEqual(pro.editor.name, 'Marty Alchin')

        # get_or_create is a special case. The get needs to be targeted at
        # the write database in order to avoid potential transaction
        # consistency problems
        book, created = Book.objects.get_or_create(title="Pro Django")
        self.assertFalse(created)

        book, created = Book.objects.get_or_create(title="Dive Into Python",
                                                   defaults={'published': datetime.date(2009, 5, 4)})
        self.assertTrue(created)

        # Check the head count of objects
        self.assertEqual(Book.objects.using('default').count(), 2)
        self.assertEqual(Book.objects.using('other').count(), 1)
        # If a database isn't specified, the read database is used
        self.assertEqual(Book.objects.count(), 1)

        # A delete query will also be routed to the default database
        Book.objects.filter(pages__gt=150).delete()

        # The default database has lost the book.
        self.assertEqual(Book.objects.using('default').count(), 1)
        self.assertEqual(Book.objects.using('other').count(), 1)

    def test_foreign_key_cross_database_protection(self):
        "Foreign keys can cross databases if they two databases have a common source"
        # Create a book and author on the default database
        pro = Book.objects.using('default').create(title="Pro Django",
                                                   published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('default').create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            dive.editor = marty
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEqual(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real primary/replica database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Set a foreign key set with an object from a different database
        try:
            marty.edited = [pro, dive]
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Assignment implies a save, so database assignments of original objects have changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')
        self.assertEqual(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real primary/replica database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Add to a foreign key set with an object from a different database
        try:
            marty.edited.add(dive)
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Add implies a save, so database assignments of original objects have changed...
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')
        self.assertEqual(mark._state.db, 'other')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real primary/replica database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')

        # If you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        chris = Person(name="Chris Mills")
        html5 = Book(title="Dive into HTML5", published=datetime.date(2010, 3, 15))
        # initially, no db assigned
        self.assertEqual(chris._state.db, None)
        self.assertEqual(html5._state.db, None)

        # old object comes from 'other', so the new object is set to use the
        # source of 'other'...
        self.assertEqual(dive._state.db, 'other')
        chris.save()
        dive.editor = chris
        html5.editor = mark

        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')
        self.assertEqual(chris._state.db, 'default')
        self.assertEqual(html5._state.db, 'default')

        # This also works if you assign the FK in the constructor
        water = Book(title="Dive into Water", published=datetime.date(2001, 1, 1), editor=mark)
        self.assertEqual(water._state.db, 'default')

        # For the remainder of this test, create a copy of 'mark' in the
        # 'default' database to prevent integrity errors on backends that
        # don't defer constraints checks until the end of the transaction
        mark.save(using='default')

        # This moved 'mark' in the 'default' database, move it back in 'other'
        mark.save(using='other')
        self.assertEqual(mark._state.db, 'other')

        # If you create an object through a FK relation, it will be
        # written to the write database, even if the original object
        # was on the read database
        cheesecake = mark.edited.create(title='Dive into Cheesecake', published=datetime.date(2010, 3, 15))
        self.assertEqual(cheesecake._state.db, 'default')

        # Same goes for get_or_create, regardless of whether getting or creating
        cheesecake, created = mark.edited.get_or_create(title='Dive into Cheesecake', published=datetime.date(2010, 3, 15))
        self.assertEqual(cheesecake._state.db, 'default')

        puddles, created = mark.edited.get_or_create(title='Dive into Puddles', published=datetime.date(2010, 3, 15))
        self.assertEqual(puddles._state.db, 'default')

    def test_m2m_cross_database_protection(self):
        "M2M relations can cross databases if the database share a source"
        # Create books and authors on the inverse to the usual database
        pro = Book.objects.using('other').create(pk=1, title="Pro Django",
                                                 published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('other').create(pk=1, name="Marty Alchin")

        dive = Book.objects.using('default').create(pk=2, title="Dive into Python",
                                                    published=datetime.date(2009, 5, 4))

        mark = Person.objects.using('default').create(pk=2, name="Mark Pilgrim")

        # Now save back onto the usual database.
        # This simulates primary/replica - the objects exist on both database,
        # but the _state.db is as it is for all other tests.
        pro.save(using='default')
        marty.save(using='default')
        dive.save(using='other')
        mark.save(using='other')

        # Check that we have 2 of both types of object on both databases
        self.assertEqual(Book.objects.using('default').count(), 2)
        self.assertEqual(Book.objects.using('other').count(), 2)
        self.assertEqual(Person.objects.using('default').count(), 2)
        self.assertEqual(Person.objects.using('other').count(), 2)

        # Set a m2m set with an object from a different database
        try:
            marty.book_set = [pro, dive]
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments don't change
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEqual(Book.authors.through.objects.using('default').count(), 2)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

        # Reset relations
        Book.authors.through.objects.using('default').delete()

        # Add to an m2m with an object from a different database
        try:
            marty.book_set.add(dive)
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments don't change
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEqual(Book.authors.through.objects.using('default').count(), 1)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

        # Reset relations
        Book.authors.through.objects.using('default').delete()

        # Set a reverse m2m with an object from a different database
        try:
            dive.authors = [mark, marty]
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments don't change
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEqual(Book.authors.through.objects.using('default').count(), 2)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

        # Reset relations
        Book.authors.through.objects.using('default').delete()

        self.assertEqual(Book.authors.through.objects.using('default').count(), 0)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

        # Add to a reverse m2m with an object from a different database
        try:
            dive.authors.add(marty)
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments don't change
        self.assertEqual(marty._state.db, 'default')
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(mark._state.db, 'other')

        # All m2m relations should be saved on the default database
        self.assertEqual(Book.authors.through.objects.using('default').count(), 1)
        self.assertEqual(Book.authors.through.objects.using('other').count(), 0)

        # If you create an object through a M2M relation, it will be
        # written to the write database, even if the original object
        # was on the read database
        alice = dive.authors.create(name='Alice')
        self.assertEqual(alice._state.db, 'default')

        # Same goes for get_or_create, regardless of whether getting or creating
        alice, created = dive.authors.get_or_create(name='Alice')
        self.assertEqual(alice._state.db, 'default')

        bob, created = dive.authors.get_or_create(name='Bob')
        self.assertEqual(bob._state.db, 'default')

    def test_o2o_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a user and profile on the default database
        alice = User.objects.db_manager('default').create_user('alice', 'alice@example.com')

        # Create a user and profile on the other database
        bob = User.objects.db_manager('other').create_user('bob', 'bob@example.com')

        # Set a one-to-one relation with an object from a different database
        alice_profile = UserProfile.objects.create(user=alice, flavor='chocolate')
        try:
            bob.userprofile = alice_profile
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(alice._state.db, 'default')
        self.assertEqual(alice_profile._state.db, 'default')
        self.assertEqual(bob._state.db, 'other')

        # ... but they will when the affected object is saved.
        bob.save()
        self.assertEqual(bob._state.db, 'default')

    def test_generic_key_cross_database_protection(self):
        "Generic Key operations can span databases if they share a source"
        # Create a book and author on the default database
        pro = Book.objects.using(
            'default').create(title="Pro Django", published=datetime.date(2008, 12, 16))

        review1 = Review.objects.using(
            'default').create(source="Python Monthly", content_object=pro)

        # Create a book and author on the other database
        dive = Book.objects.using(
            'other').create(title="Dive into Python", published=datetime.date(2009, 5, 4))

        review2 = Review.objects.using(
            'other').create(source="Python Weekly", content_object=dive)

        # Set a generic foreign key with an object from a different database
        try:
            review1.content_object = dive
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(review1._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(review2._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEqual(review1._state.db, 'default')
        self.assertEqual(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # This isn't a real primary/replica database, so restore the original from other
        dive = Book.objects.using('other').get(title='Dive into Python')
        self.assertEqual(dive._state.db, 'other')

        # Add to a generic foreign key set with an object from a different database
        try:
            dive.reviews.add(review1)
        except ValueError:
            self.fail("Assignment across primary/replica databases with a common source should be ok")

        # Database assignments of original objects haven't changed...
        self.assertEqual(pro._state.db, 'default')
        self.assertEqual(review1._state.db, 'default')
        self.assertEqual(dive._state.db, 'other')
        self.assertEqual(review2._state.db, 'other')

        # ... but they will when the affected object is saved.
        dive.save()
        self.assertEqual(dive._state.db, 'default')

        # ...and the source database now has a copy of any object saved
        try:
            Book.objects.using('default').get(title='Dive into Python').delete()
        except Book.DoesNotExist:
            self.fail('Source database should have a copy of saved object')

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        review3 = Review(source="Python Daily")
        # initially, no db assigned
        self.assertEqual(review3._state.db, None)

        # Dive comes from 'other', so review3 is set to use the source of 'other'...
        review3.content_object = dive
        self.assertEqual(review3._state.db, 'default')

        # If you create an object through a M2M relation, it will be
        # written to the write database, even if the original object
        # was on the read database
        dive = Book.objects.using('other').get(title='Dive into Python')
        nyt = dive.reviews.create(source="New York Times", content_object=dive)
        self.assertEqual(nyt._state.db, 'default')

    def test_m2m_managers(self):
        "M2M relations are represented by managers, and can be controlled like managers"
        pro = Book.objects.using('other').create(pk=1, title="Pro Django",
                                                 published=datetime.date(2008, 12, 16))

        marty = Person.objects.using('other').create(pk=1, name="Marty Alchin")

        self.assertEqual(pro.authors.db, 'other')
        self.assertEqual(pro.authors.db_manager('default').db, 'default')
        self.assertEqual(pro.authors.db_manager('default').all().db, 'default')

        self.assertEqual(marty.book_set.db, 'other')
        self.assertEqual(marty.book_set.db_manager('default').db, 'default')
        self.assertEqual(marty.book_set.db_manager('default').all().db, 'default')

    def test_foreign_key_managers(self):
        "FK reverse relations are represented by managers, and can be controlled like managers"
        marty = Person.objects.using('other').create(pk=1, name="Marty Alchin")
        Book.objects.using('other').create(pk=1, title="Pro Django",
                                           published=datetime.date(2008, 12, 16),
                                           editor=marty)

        self.assertEqual(marty.edited.db, 'other')
        self.assertEqual(marty.edited.db_manager('default').db, 'default')
        self.assertEqual(marty.edited.db_manager('default').all().db, 'default')

    def test_generic_key_managers(self):
        "Generic key relations are represented by managers, and can be controlled like managers"
        pro = Book.objects.using('other').create(title="Pro Django",
                                                 published=datetime.date(2008, 12, 16))

        Review.objects.using('other').create(source="Python Monthly",
                                             content_object=pro)

        self.assertEqual(pro.reviews.db, 'other')
        self.assertEqual(pro.reviews.db_manager('default').db, 'default')
        self.assertEqual(pro.reviews.db_manager('default').all().db, 'default')

    def test_subquery(self):
        """Make sure as_sql works with subqueries and primary/replica."""
        # Create a book and author on the other database

        mark = Person.objects.using('other').create(name="Mark Pilgrim")
        Book.objects.using('other').create(title="Dive into Python",
                                           published=datetime.date(2009, 5, 4),
                                           editor=mark)

        sub = Person.objects.filter(name='Mark Pilgrim')
        qs = Book.objects.filter(editor__in=sub)

        # When you call __str__ on the query object, it doesn't know about using
        # so it falls back to the default. Don't let routing instructions
        # force the subquery to an incompatible database.
        str(qs.query)

        # If you evaluate the query, it should work, running on 'other'
        self.assertEqual(list(qs.values_list('title', flat=True)), ['Dive into Python'])

    def test_deferred_models(self):
        mark_def = Person.objects.using('default').create(name="Mark Pilgrim")
        mark_other = Person.objects.using('other').create(name="Mark Pilgrim")
        orig_b = Book.objects.using('other').create(title="Dive into Python",
                                                    published=datetime.date(2009, 5, 4),
                                                    editor=mark_other)
        b = Book.objects.using('other').only('title').get(pk=orig_b.pk)
        self.assertEqual(b.published, datetime.date(2009, 5, 4))
        b = Book.objects.using('other').only('title').get(pk=orig_b.pk)
        b.editor = mark_def
        b.save(using='default')
        self.assertEqual(Book.objects.using('default').get(pk=b.pk).published,
                         datetime.date(2009, 5, 4))


@override_settings(DATABASE_ROUTERS=[AuthRouter()])
class AuthTestCase(TestCase):
    multi_db = True

    def test_auth_manager(self):
        "The methods on the auth manager obey database hints"
        # Create one user using default allocation policy
        User.objects.create_user('alice', 'alice@example.com')

        # Create another user, explicitly specifying the database
        User.objects.db_manager('default').create_user('bob', 'bob@example.com')

        # The second user only exists on the other database
        alice = User.objects.using('other').get(username='alice')

        self.assertEqual(alice.username, 'alice')
        self.assertEqual(alice._state.db, 'other')

        self.assertRaises(User.DoesNotExist, User.objects.using('default').get, username='alice')

        # The second user only exists on the default database
        bob = User.objects.using('default').get(username='bob')

        self.assertEqual(bob.username, 'bob')
        self.assertEqual(bob._state.db, 'default')

        self.assertRaises(User.DoesNotExist, User.objects.using('other').get, username='bob')

        # That is... there is one user on each database
        self.assertEqual(User.objects.using('default').count(), 1)
        self.assertEqual(User.objects.using('other').count(), 1)

    def test_dumpdata(self):
        "Check that dumpdata honors allow_migrate restrictions on the router"
        User.objects.create_user('alice', 'alice@example.com')
        User.objects.db_manager('default').create_user('bob', 'bob@example.com')

        # Check that dumping the default database doesn't try to include auth
        # because allow_migrate prohibits auth on default
        new_io = StringIO()
        management.call_command('dumpdata', 'auth', format='json', database='default', stdout=new_io)
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, '[]')

        # Check that dumping the other database does include auth
        new_io = StringIO()
        management.call_command('dumpdata', 'auth', format='json', database='other', stdout=new_io)
        command_output = new_io.getvalue().strip()
        self.assertIn('"email": "alice@example.com"', command_output)


class AntiPetRouter(object):
    # A router that only expresses an opinion on migrate,
    # passing pets to the 'other' database

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'other':
            return model_name == 'pet'
        else:
            return model_name != 'pet'


class FixtureTestCase(TestCase):
    multi_db = True
    fixtures = ['multidb-common', 'multidb']

    @override_settings(DATABASE_ROUTERS=[AntiPetRouter()])
    def test_fixture_loading(self):
        "Multi-db fixtures are loaded correctly"
        # Check that "Pro Django" exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on default database')

        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        # Check that "Dive into Python" exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(
            Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

        # Check that "Definitive Guide" exists on the both databases
        try:
            Book.objects.get(title="The Definitive Guide to Django")
            Book.objects.using('default').get(title="The Definitive Guide to Django")
            Book.objects.using('other').get(title="The Definitive Guide to Django")
        except Book.DoesNotExist:
            self.fail('"The Definitive Guide to Django" should exist on both databases')

    @override_settings(DATABASE_ROUTERS=[AntiPetRouter()])
    def test_pseudo_empty_fixtures(self):
        "A fixture can contain entries, but lead to nothing in the database; this shouldn't raise an error (ref #14068)"
        new_io = StringIO()
        management.call_command('loaddata', 'pets', stdout=new_io, stderr=new_io)
        command_output = new_io.getvalue().strip()
        # No objects will actually be loaded
        self.assertEqual(command_output, "Installed 0 object(s) (of 2) from 1 fixture(s)")


class PickleQuerySetTestCase(TestCase):
    multi_db = True

    def test_pickling(self):
        for db in connections:
            Book.objects.using(db).create(title='Dive into Python', published=datetime.date(2009, 5, 4))
            qs = Book.objects.all()
            self.assertEqual(qs.db, pickle.loads(pickle.dumps(qs)).db)


class DatabaseReceiver(object):
    """
    Used in the tests for the database argument in signals (#13552)
    """
    def __call__(self, signal, sender, **kwargs):
        self._database = kwargs['using']


class WriteToOtherRouter(object):
    """
    A router that sends all writes to the other database.
    """
    def db_for_write(self, model, **hints):
        return "other"


class SignalTests(TestCase):
    multi_db = True

    def override_router(self):
        return override_settings(DATABASE_ROUTERS=[WriteToOtherRouter()])

    def test_database_arg_save_and_delete(self):
        """
        Tests that the pre/post_save signal contains the correct database.
        (#13552)
        """
        # Make some signal receivers
        pre_save_receiver = DatabaseReceiver()
        post_save_receiver = DatabaseReceiver()
        pre_delete_receiver = DatabaseReceiver()
        post_delete_receiver = DatabaseReceiver()
        # Make model and connect receivers
        signals.pre_save.connect(sender=Person, receiver=pre_save_receiver)
        signals.post_save.connect(sender=Person, receiver=post_save_receiver)
        signals.pre_delete.connect(sender=Person, receiver=pre_delete_receiver)
        signals.post_delete.connect(sender=Person, receiver=post_delete_receiver)
        p = Person.objects.create(name='Darth Vader')
        # Save and test receivers got calls
        p.save()
        self.assertEqual(pre_save_receiver._database, DEFAULT_DB_ALIAS)
        self.assertEqual(post_save_receiver._database, DEFAULT_DB_ALIAS)
        # Delete, and test
        p.delete()
        self.assertEqual(pre_delete_receiver._database, DEFAULT_DB_ALIAS)
        self.assertEqual(post_delete_receiver._database, DEFAULT_DB_ALIAS)
        # Save again to a different database
        p.save(using="other")
        self.assertEqual(pre_save_receiver._database, "other")
        self.assertEqual(post_save_receiver._database, "other")
        # Delete, and test
        p.delete(using="other")
        self.assertEqual(pre_delete_receiver._database, "other")
        self.assertEqual(post_delete_receiver._database, "other")

        signals.pre_save.disconnect(sender=Person, receiver=pre_save_receiver)
        signals.post_save.disconnect(sender=Person, receiver=post_save_receiver)
        signals.pre_delete.disconnect(sender=Person, receiver=pre_delete_receiver)
        signals.post_delete.disconnect(sender=Person, receiver=post_delete_receiver)

    def test_database_arg_m2m(self):
        """
        Test that the m2m_changed signal has a correct database arg (#13552)
        """
        # Make a receiver
        receiver = DatabaseReceiver()
        # Connect it
        signals.m2m_changed.connect(receiver=receiver)

        # Create the models that will be used for the tests
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        p = Person.objects.create(name="Marty Alchin")

        # Create a copy of the models on the 'other' database to prevent
        # integrity errors on backends that don't defer constraints checks
        Book.objects.using('other').create(pk=b.pk, title=b.title,
                                           published=b.published)
        Person.objects.using('other').create(pk=p.pk, name=p.name)

        # Test addition
        b.authors.add(p)
        self.assertEqual(receiver._database, DEFAULT_DB_ALIAS)
        with self.override_router():
            b.authors.add(p)
        self.assertEqual(receiver._database, "other")

        # Test removal
        b.authors.remove(p)
        self.assertEqual(receiver._database, DEFAULT_DB_ALIAS)
        with self.override_router():
            b.authors.remove(p)
        self.assertEqual(receiver._database, "other")

        # Test addition in reverse
        p.book_set.add(b)
        self.assertEqual(receiver._database, DEFAULT_DB_ALIAS)
        with self.override_router():
            p.book_set.add(b)
        self.assertEqual(receiver._database, "other")

        # Test clearing
        b.authors.clear()
        self.assertEqual(receiver._database, DEFAULT_DB_ALIAS)
        with self.override_router():
            b.authors.clear()
        self.assertEqual(receiver._database, "other")


class AttributeErrorRouter(object):
    "A router to test the exception handling of ConnectionRouter"
    def db_for_read(self, model, **hints):
        raise AttributeError

    def db_for_write(self, model, **hints):
        raise AttributeError


class RouterAttributeErrorTestCase(TestCase):
    multi_db = True

    def override_router(self):
        return override_settings(DATABASE_ROUTERS=[AttributeErrorRouter()])

    def test_attribute_error_read(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        with self.override_router():
            self.assertRaises(AttributeError, Book.objects.get, pk=b.pk)

    def test_attribute_error_save(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        dive = Book()
        dive.title = "Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        with self.override_router():
            self.assertRaises(AttributeError, dive.save)

    def test_attribute_error_delete(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        p = Person.objects.create(name="Marty Alchin")
        b.authors = [p]
        b.editor = p
        with self.override_router():
            self.assertRaises(AttributeError, b.delete)

    def test_attribute_error_m2m(self):
        "Check that the AttributeError from AttributeErrorRouter bubbles up"
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))
        p = Person.objects.create(name="Marty Alchin")
        with self.override_router():
            self.assertRaises(AttributeError, setattr, b, 'authors', [p])


class ModelMetaRouter(object):
    "A router to ensure model arguments are real model classes"
    def db_for_write(self, model, **hints):
        if not hasattr(model, '_meta'):
            raise ValueError


@override_settings(DATABASE_ROUTERS=[ModelMetaRouter()])
class RouterModelArgumentTestCase(TestCase):
    multi_db = True

    def test_m2m_collection(self):
        b = Book.objects.create(title="Pro Django",
                                published=datetime.date(2008, 12, 16))

        p = Person.objects.create(name="Marty Alchin")
        # test add
        b.authors.add(p)
        # test remove
        b.authors.remove(p)
        # test clear
        b.authors.clear()
        # test setattr
        b.authors = [p]
        # test M2M collection
        b.delete()

    def test_foreignkey_collection(self):
        person = Person.objects.create(name='Bob')
        Pet.objects.create(owner=person, name='Wart')
        # test related FK collection
        person.delete()


class SyncOnlyDefaultDatabaseRouter(object):
    def allow_migrate(self, db, app_label, **hints):
        return db == DEFAULT_DB_ALIAS


class MigrateTestCase(TestCase):

    available_apps = [
        'multiple_database',
        'django.contrib.auth',
        'django.contrib.contenttypes'
    ]
    multi_db = True

    def test_migrate_to_other_database(self):
        """Regression test for #16039: migrate with --database option."""
        cts = ContentType.objects.using('other').filter(app_label='multiple_database')

        count = cts.count()
        self.assertGreater(count, 0)

        cts.delete()
        management.call_command('migrate', verbosity=0, interactive=False,
            load_initial_data=False, database='other')
        self.assertEqual(cts.count(), count)

    def test_migrate_to_other_database_with_router(self):
        """Regression test for #16039: migrate with --database option."""
        cts = ContentType.objects.using('other').filter(app_label='multiple_database')

        cts.delete()
        with override_settings(DATABASE_ROUTERS=[SyncOnlyDefaultDatabaseRouter()]):
            management.call_command('migrate', verbosity=0, interactive=False,
                load_initial_data=False, database='other')

        self.assertEqual(cts.count(), 0)


class RouterUsed(Exception):
    WRITE = 'write'

    def __init__(self, mode, model, hints):
        self.mode = mode
        self.model = model
        self.hints = hints


class RouteForWriteTestCase(TestCase):
    multi_db = True

    class WriteCheckRouter(object):
        def db_for_write(self, model, **hints):
            raise RouterUsed(mode=RouterUsed.WRITE, model=model, hints=hints)

    def override_router(self):
        return override_settings(DATABASE_ROUTERS=[RouteForWriteTestCase.WriteCheckRouter()])

    def test_fk_delete(self):
        owner = Person.objects.create(name='Someone')
        pet = Pet.objects.create(name='fido', owner=owner)
        try:
            with self.override_router():
                pet.owner.delete()
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Person)
            self.assertEqual(e.hints, {'instance': owner})

    def test_reverse_fk_delete(self):
        owner = Person.objects.create(name='Someone')
        to_del_qs = owner.pet_set.all()
        try:
            with self.override_router():
                to_del_qs.delete()
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Pet)
            self.assertEqual(e.hints, {'instance': owner})

    def test_reverse_fk_get_or_create(self):
        owner = Person.objects.create(name='Someone')
        try:
            with self.override_router():
                owner.pet_set.get_or_create(name='fido')
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Pet)
            self.assertEqual(e.hints, {'instance': owner})

    def test_reverse_fk_update(self):
        owner = Person.objects.create(name='Someone')
        Pet.objects.create(name='fido', owner=owner)
        try:
            with self.override_router():
                owner.pet_set.update(name='max')
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Pet)
            self.assertEqual(e.hints, {'instance': owner})

    def test_m2m_add(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        try:
            with self.override_router():
                book.authors.add(auth)
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book.authors.through)
            self.assertEqual(e.hints, {'instance': book})

    def test_m2m_clear(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                book.authors.clear()
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book.authors.through)
            self.assertEqual(e.hints, {'instance': book})

    def test_m2m_delete(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                book.authors.all().delete()
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Person)
            self.assertEqual(e.hints, {'instance': book})

    def test_m2m_get_or_create(self):
        Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        try:
            with self.override_router():
                book.authors.get_or_create(name='Someone else')
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book)
            self.assertEqual(e.hints, {'instance': book})

    def test_m2m_remove(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                book.authors.remove(auth)
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book.authors.through)
            self.assertEqual(e.hints, {'instance': book})

    def test_m2m_update(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                book.authors.all().update(name='Different')
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Person)
            self.assertEqual(e.hints, {'instance': book})

    def test_reverse_m2m_add(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        try:
            with self.override_router():
                auth.book_set.add(book)
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book.authors.through)
            self.assertEqual(e.hints, {'instance': auth})

    def test_reverse_m2m_clear(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                auth.book_set.clear()
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book.authors.through)
            self.assertEqual(e.hints, {'instance': auth})

    def test_reverse_m2m_delete(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                auth.book_set.all().delete()
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book)
            self.assertEqual(e.hints, {'instance': auth})

    def test_reverse_m2m_get_or_create(self):
        auth = Person.objects.create(name='Someone')
        Book.objects.create(title="Pro Django",
                            published=datetime.date(2008, 12, 16))
        try:
            with self.override_router():
                auth.book_set.get_or_create(title="New Book", published=datetime.datetime.now())
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Person)
            self.assertEqual(e.hints, {'instance': auth})

    def test_reverse_m2m_remove(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                auth.book_set.remove(book)
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book.authors.through)
            self.assertEqual(e.hints, {'instance': auth})

    def test_reverse_m2m_update(self):
        auth = Person.objects.create(name='Someone')
        book = Book.objects.create(title="Pro Django",
                                   published=datetime.date(2008, 12, 16))
        book.authors.add(auth)
        try:
            with self.override_router():
                auth.book_set.all().update(title='Different')
            self.fail('db_for_write() not invoked on router')
        except RouterUsed as e:
            self.assertEqual(e.mode, RouterUsed.WRITE)
            self.assertEqual(e.model, Book)
            self.assertEqual(e.hints, {'instance': auth})
