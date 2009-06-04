import datetime

from django.conf import settings
from django.db import connections
from django.test import TestCase

from models import Book

class DatabaseSettingTestCase(TestCase):
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

class QueryTestCase(TestCase):
    def test_basic_queries(self):
        for db in connections:
            Book.objects.using(db).create(title="Dive into Python",
                published=datetime.date(2009, 5, 4))

        for db in connections:
            books = Book.objects.all().using(db)
            self.assertEqual(books.count(), 1)
            self.assertEqual(len(books), 1)
            self.assertEqual(books[0].title, "Dive into Python")
            self.assertEqual(books[0].published, datetime.date(2009, 5, 4))

        for db in connections:
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
