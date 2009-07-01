import datetime

from django.conf import settings
from django.db import connections
from django.test import TestCase

from models import Book

try:
    # we only have these models if the user is using multi-db, it's safe the
    # run the tests without them though.
    from models import Article, article_using
except ImportError:
    pass

class ConnectionHandlerTestCase(TestCase):
    def setUp(self):
        settings.DATABASES['__test_db'] = {
            'DATABASE_ENGINE': 'sqlite3',
            'DATABASE_NAME': ':memory:',
        }

    def tearDown(self):
        del settings.DATABASES['__test_db']

    def test_db_connection(self):
        connections['default'].cursor()
        connections['__test_db'].cursor()

    def test_alias_for_connection(self):
        for db in connections:
            self.assertEqual(db, connections.alias_for_connection(connections[db]))


class QueryTestCase(TestCase):
    def test_basic_queries(self):
        for db in connections:
            self.assertRaises(Book.DoesNotExist,
                lambda: Book.objects.using(db).get(title="Dive into Python"))
            Book.objects.using(db).create(title="Dive into Python",
                published=datetime.date(2009, 5, 4))

        for db in connections:
            books = Book.objects.all().using(db)
            self.assertEqual(books.count(), 1)
            self.assertEqual(len(books), 1)
            self.assertEqual(books[0].title, "Dive into Python")
            self.assertEqual(books[0].published, datetime.date(2009, 5, 4))

        for db in connections:
            self.assertRaises(Book.DoesNotExist,
                lambda: Book.objects.using(db).get(title="Pro Django"))
            book = Book(title="Pro Django", published=datetime.date(2008, 12, 16))
            book.save(using=db)

        for db in connections:
            books = Book.objects.all().using(db)
            self.assertEqual(books.count(), 2)
            self.assertEqual(len(books), 2)
            self.assertEqual(books[0].title, "Dive into Python")
            self.assertEqual(books[1].title, "Pro Django")

            pro = Book.objects.using(db).get(published=datetime.date(2008, 12, 16))
            self.assertEqual(pro.title, "Pro Django")

            dive = Book.objects.using(db).get(title__icontains="dive")
            self.assertEqual(dive.title, "Dive into Python")

            dive = Book.objects.using(db).get(title__iexact="dive INTO python")
            self.assertEqual(dive.title, "Dive into Python")

            pro = Book.objects.using(db).get(published__year=2008)
            self.assertEqual(pro.title, "Pro Django")
            self.assertEqual(pro.published, datetime.date(2008, 12, 16))

            years = Book.objects.using(db).dates('published', 'year')
            self.assertEqual([o.year for o in years], [2008, 2009])

            months = Book.objects.dates('published', 'month').using(db)
            self.assertEqual(sorted(o.month for o in months), [5, 12])

if len(settings.DATABASES) > 1:
    class MetaUsingTestCase(TestCase):
        def test_meta_using_queries(self):
            a = Article.objects.create(title="Django Rules!")
            self.assertEqual(Article.objects.get(title="Django Rules!"), a)
            for db in connections:
                if db == article_using:
                    self.assertEqual(Article.objects.using(db).get(title="Django Rules!"), a)
                else:
                    self.assertRaises(Article.DoesNotExist,
                        lambda: Article.objects.using(db).get(title="Django Rules!"))
            a.delete()
            self.assertRaises(Article.DoesNotExist,
                lambda: Article.objects.get(title="Django Rules!"))
