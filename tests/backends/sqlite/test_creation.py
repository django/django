import unittest

from django.db import connection
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class DatabaseExistsTests(TestCase):

    def test_database_exists(self):
        creation = DatabaseCreation(connection)
        self.assertFalse(creation._database_exists(None, 'test_db'))
