import datetime
import pickle

from django.conf import settings
from django.db import connections
from django.test import TestCase

from models import Book, Author

try:
    # we only have these models if the user is using multi-db, it's safe the
    # run the tests without them though.
    from models import Article, article_using
except ImportError:
    pass

class QueryTestCase(TestCase):
    multi_db = True

    def test_default_creation(self):
        "Objects created on the default database don't leak onto other databases"
        # Create a book on the default database using create()
        Book.objects.create(title="Pro Django",
                            published=datetime.date(2008, 12, 16))

        # Create a book on the default database using a save
        dive = Book()
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save()

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
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
        dive.title="Dive into Python"
        dive.published = datetime.date(2009, 5, 4)
        dive.save(using='other')

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
        )

        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

    def test_basic_queries(self):
        "Queries are constrained to a single database"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        dive =  Book.objects.using('other').get(published=datetime.date(2009, 5, 4))
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, published=datetime.date(2009, 5, 4))

        dive = Book.objects.using('other').get(title__icontains="dive")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__icontains="dive")

        dive = Book.objects.using('other').get(title__iexact="dive INTO python")
        self.assertEqual(dive.title, "Dive into Python")
        self.assertRaises(Book.DoesNotExist, Book.objects.using('default').get, title__iexact="dive INTO python")

        dive =  Book.objects.using('other').get(published__year=2009)
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

        marty = Author.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        pro.authors = [marty]
        dive.authors = [mark]

        # Inspect the m2m tables directly.
        # There should be 1 entry in each database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 1)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 1)

        # Check that queries work across m2m joins
        self.assertEquals(list(Book.objects.using('default').filter(authors__name='Marty Alchin').values_list('title', flat=True)),
                          [u'Pro Django'])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Marty Alchin').values_list('title', flat=True)),
                          [])

        self.assertEquals(list(Book.objects.using('default').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_m2m_forward_operations(self):
        "M2M forward manipulations are all constrained to a single DB"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        dive.authors = [mark]

        # Add a second author
        john = Author.objects.using('other').create(name="John Smith")
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [])


        dive.authors.add(john)
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [u'Dive into Python'])

        # Remove the second author
        dive.authors.remove(john)
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [])

        # Clear all authors
        dive.authors.clear()
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='John Smith').values_list('title', flat=True)),
                          [])

        # Create an author through the m2m interface
        dive.authors.create(name='Jane Brown')
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(authors__name='Jane Brown').values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_m2m_reverse_operations(self):
        "M2M reverse manipulations are all constrained to a single DB"
        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        dive.authors = [mark]

        # Create a second book on the other database
        grease = Book.objects.using('other').create(title="Greasemonkey Hacks",
                                                    published=datetime.date(2005, 11, 1))

        # Add a books to the m2m
        mark.book_set.add(grease)
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])

        # Remove a book from the m2m
        mark.book_set.remove(grease)
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
                          [])

        # Clear the books associated with mark
        mark.book_set.clear()
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Greasemonkey Hacks').values_list('name', flat=True)),
                          [])

        # Create a book through the m2m interface
        mark.book_set.create(title="Dive into HTML5", published=datetime.date(2020, 1, 1))
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Dive into Python').values_list('name', flat=True)),
                          [])
        self.assertEquals(list(Author.objects.using('other').filter(book__title='Dive into HTML5').values_list('name', flat=True)),
                          [u'Mark Pilgrim'])


    def test_foreign_key_separation(self):
        "FK fields are constrained to a single database"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Author.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")

        # Save the author's favourite books
        marty.favourite_book = pro
        marty.save()

        mark.favourite_book = dive
        mark.save()

        marty = Author.objects.using('default').get(name="Marty Alchin")
        self.assertEquals(marty.favourite_book.title, "Pro Django")

        mark = Author.objects.using('other').get(name='Mark Pilgrim')
        self.assertEquals(mark.favourite_book.title, "Dive into Python")

        # Check that queries work across foreign key joins
        self.assertEquals(list(Book.objects.using('default').filter(favourite_of__name='Marty Alchin').values_list('title', flat=True)),
                          [u'Pro Django'])
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Marty Alchin').values_list('title', flat=True)),
                          [])

        self.assertEquals(list(Book.objects.using('default').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_foreign_key_reverse_operations(self):
        "FK reverse manipulations are all constrained to a single DB"
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                       published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")

        # Save the author relations
        mark.favourite_book = dive
        mark.save()

        # Add a second author
        john = Author.objects.using('other').create(name="John Smith")
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='John Smith').values_list('title', flat=True)),
                          [])


        dive.favourite_of.add(john)
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='John Smith').values_list('title', flat=True)),
                          [u'Dive into Python'])

        # Remove the second author
        dive.favourite_of.remove(john)
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True)),
                          [u'Dive into Python'])
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='John Smith').values_list('title', flat=True)),
                          [])

        # Clear all favourite_of
        dive.favourite_of.clear()
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='John Smith').values_list('title', flat=True)),
                          [])

        # Create an author through the m2m interface
        dive.favourite_of.create(name='Jane Brown')
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True)),
                          [])
        self.assertEquals(list(Book.objects.using('other').filter(favourite_of__name='Jane Brown').values_list('title', flat=True)),
                          [u'Dive into Python'])

    def test_m2m_cross_database_protection(self):
        "Operations that involve sharing M2M objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Author.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")
        # Set a foreign key set with an object from a different database
        try:
            marty.book_set = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to an m2m with an object from a different database
        try:
            marty.book_set.add(dive)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a m2m with an object from a different database
        try:
            marty.book_set = [pro, dive]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a reverse m2m with an object from a different database
        try:
            dive.authors.add(marty)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a reverse m2m with an object from a different database
        try:
            dive.authors = [mark, marty]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

    def test_foreign_key_cross_database_protection(self):
        "Operations that involve sharing FK objects across databases raise an error"
        # Create a book and author on the default database
        pro = Book.objects.create(title="Pro Django",
                                  published=datetime.date(2008, 12, 16))

        marty = Author.objects.create(name="Marty Alchin")

        # Create a book and author on the other database
        dive = Book.objects.using('other').create(title="Dive into Python",
                                                  published=datetime.date(2009, 5, 4))

        mark = Author.objects.using('other').create(name="Mark Pilgrim")

        # Set a foreign key with an object from a different database
        try:
            marty.favourite_book = dive
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Set a foreign key set with an object from a different database
        try:
            dive.favourite_of = [mark, marty]
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # Add to a foreign key set with an object from a different database
        try:
            dive.favourite_of.add(marty)
            self.fail("Shouldn't be able to assign across databases")
        except ValueError:
            pass

        # BUT! if you assign a FK object when the base object hasn't
        # been saved yet, you implicitly assign the database for the
        # base object.
        john = Author(name="John Smith")
        # initially, no db assigned
        self.assertEquals(john._state.db, None)

        # Dive comes from 'other', so john is set to use 'other'...
        john.favourite_book = dive
        self.assertEquals(john._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEquals(list(Author.objects.using('other').values_list('name',flat=True)),
                          [u'Mark Pilgrim'])

        # When saved, John goes to 'other'
        john.save()
        self.assertEquals(list(Author.objects.using('default').values_list('name',flat=True)),
                          [u'Marty Alchin'])
        self.assertEquals(list(Author.objects.using('other').values_list('name',flat=True)),
                          [u'John Smith', u'Mark Pilgrim'])

        # This also works if you assign the FK in the constructor
        jane = Author(name='Jane Brown', favourite_book=dive)
        self.assertEquals(jane._state.db, 'other')
        # ... but it isn't saved yet
        self.assertEquals(list(Author.objects.using('other').values_list('name',flat=True)),
                          [u'John Smith', u'Mark Pilgrim'])

        # When saved, Jane goes to 'other'
        jane.save()
        self.assertEquals(list(Author.objects.using('default').values_list('name',flat=True)),
                          [u'Marty Alchin'])
        self.assertEquals(list(Author.objects.using('other').values_list('name',flat=True)),
                          [u'Jane Brown', u'John Smith', u'Mark Pilgrim'])


class FixtureTestCase(TestCase):
    multi_db = True
    fixtures = ['multidb-common', 'multidb']

    def test_fixture_loading(self):
        "Multi-db fixtures are loaded correctly"
        # Check that "Pro Django" exists on the default database, but not on other database
        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )

        # Check that "Dive into Python" exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
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


class PickleQuerySetTestCase(TestCase):
    multi_db = True

    def test_pickling(self):
        for db in connections:
            Book.objects.using(db).create(title='Dive into Python', published=datetime.date(2009, 5, 4))
            qs = Book.objects.all()
            self.assertEqual(qs.db, pickle.loads(pickle.dumps(qs)).db)
