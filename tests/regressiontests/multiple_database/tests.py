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
        Book.objects.create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))

        # Create a book on the default database using a save
        pro = Book()
        pro.title="Pro Django"
        pro.published = datetime.date(2008, 12, 16)
        pro.save()

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Dive into Python"
        )

        try:
            Book.objects.get(title="Pro Django")
            Book.objects.using('default').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Pro Django"
        )


    def test_other_creation(self):
        "Objects created on another database don't leak onto the default database"
        # Create a book on the second database
        Book.objects.using('other').create(title="Dive into Python",
            published=datetime.date(2009, 5, 4))

        # Create a book on the default database using a save
        pro = Book()
        pro.title="Pro Django"
        pro.published = datetime.date(2008, 12, 16)
        pro.save(using='other')

        # Check that book exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Dive into Python"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Dive into Python"
        )

        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
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

    def test_m2m(self):
        "M2M fields are constrained to a single database"
        # Create a book and author on the default database
        dive = Book.objects.create(title="Dive into Python",
                                       published=datetime.date(2009, 5, 4))

        mark = Author.objects.create(name="Mark Pilgrim")

        # Create a book and author on the other database
        pro = Book.objects.using('other').create(title="Pro Django",
                                                       published=datetime.date(2008, 12, 16))

        marty = Author.objects.using('other').create(name="Marty Alchin")

        # Save the author relations
        dive.authors = [mark]
        pro.authors = [marty]

        # Inspect the m2m tables directly.
        # There should be 1 entry in each database
        self.assertEquals(Book.authors.through.objects.using('default').count(), 1)
        self.assertEquals(Book.authors.through.objects.using('other').count(), 1)

        # Check that queries work across m2m joins
        self.assertEquals(Book.objects.using('default').filter(authors__name='Mark Pilgrim').values_list('title', flat=True),
                          ['Dive into Python'])
        self.assertEquals(Book.objects.using('other').filter(authors__name='Mark Pilgrim').values_list('title', flat=True),
                          [])

        self.assertEquals(Book.objects.using('default').filter(authors__name='Marty Alchin').values_list('title', flat=True),
                          [])
        self.assertEquals(Book.objects.using('other').filter(authors__name='Marty Alchin').values_list('title', flat=True),
                          ['Pro Django'])

    def test_foreign_key(self):
        "FK fields are constrained to a single database"
        # Create a book and author on the default database
        dive = Book.objects.create(title="Dive into Python",
                                       published=datetime.date(2009, 5, 4))

        mark = Author.objects.create(name="Mark Pilgrim")

        # Create a book and author on the other database
        pro = Book.objects.using('other').create(title="Pro Django",
                                                       published=datetime.date(2008, 12, 16))

        marty = Author.objects.using('other').create(name="Marty Alchin")

        # Save the author's favourite books
        mark.favourite_book = dive
        mark.save()

        marty.favourite_book = pro
        marty.save() # FIXME Should this be save(using=alias)?

        mark = Author.objects.using('default').get(name="Mark Pilgrim")
        self.assertEquals(mark.favourite_book.title, "Dive into Python")

        marty = Author.objects.using('other').get(name='Marty Alchin')
        self.assertEquals(marty.favourite_book.title, "Dive into Python")

        try:
            mark.favourite_book = marty
            self.fail("Shouldn't be able to assign across databases")
        except Exception: # FIXME - this should be more explicit
            pass

        # Check that queries work across foreign key joins
        self.assertEquals(Book.objects.using('default').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True),
                          ['Dive into Python'])
        self.assertEquals(Book.objects.using('other').filter(favourite_of__name='Mark Pilgrim').values_list('title', flat=True),
                          [])

        self.assertEquals(Book.objects.using('default').filter(favourite_of__name='Marty Alchin').values_list('title', flat=True),
                          [])
        self.assertEquals(Book.objects.using('other').filter(favourite_of__name='Marty Alchin').values_list('title', flat=True),
                          ['Pro Django'])

class FixtureTestCase(TestCase):
    multi_db = True
    fixtures = ['multidb-common', 'multidb']

    def test_fixture_loading(self):
        "Multi-db fixtures are loaded correctly"
        # Check that "Dive into Python" exists on the default database, but not on other database
        try:
            Book.objects.get(title="Dive into Python")
            Book.objects.using('default').get(title="Dive into Python")
        except Book.DoesNotExist:
            self.fail('"Dive Into Python" should exist on default database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('other').get,
            title="Dive into Python"
        )

        # Check that "Pro Django" exists on the default database, but not on other database
        try:
            Book.objects.using('other').get(title="Pro Django")
        except Book.DoesNotExist:
            self.fail('"Pro Django" should exist on other database')

        self.assertRaises(Book.DoesNotExist,
            Book.objects.get,
            title="Pro Django"
        )
        self.assertRaises(Book.DoesNotExist,
            Book.objects.using('default').get,
            title="Pro Django"
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
            Book.objects.using(db).create(title='Pro Django', published=datetime.date(2008, 12, 16))
            qs = Book.objects.all()
            self.assertEqual(qs._using, pickle.loads(pickle.dumps(qs))._using)
