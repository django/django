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

class ConnectionTestCase(TestCase):
    def test_queries(self):
        for db in connections:
            Book.objects.using(db).create(title="Dive into Python")

        for db in connections:
            books = Book.objects.all().using(db)
            self.assertEqual(books.count(), 1)
            self.assertEqual(len(books), 1)
            self.assertEqual(books[0].title, "Dive into Python")
