import unittest
from unittest import mock

from django.db import connection
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class DatabaseCreationTests(TestCase):

    def test_check_keepdb(self):
        creation = DatabaseCreation(connection)
        tests = (  # return_value, keepdb, result
            (True, True, True),
            (True, False, False),
            (False, True, False),
            (False, False, False),
        )
        for item in tests:
            with mock.patch.object(DatabaseCreation, '_database_exists', return_value=item[0]):
                self.assertEqual(creation._check_keepdb(item[1]), item[2])


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class DatabaseExistsTests(TestCase):

    def test_database_exists(self):
        creation = DatabaseCreation(connection)
        self.assertFalse(creation._database_exists(None, 'test_db'))
