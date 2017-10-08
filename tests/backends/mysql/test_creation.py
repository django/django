import unittest
from io import StringIO
from unittest import mock

from django.db import connection
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.backends.mysql.creation import DatabaseCreation
from django.db.utils import DatabaseError
from django.test import SimpleTestCase


@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class DatabaseCreationTests(SimpleTestCase):

    def _execute_raise_database_exists(self, cursor, parameters, keepdb=False):
        raise DatabaseError(1007, "Can't create database '%s'; database exists" % parameters['dbname'])

    def _execute_raise_access_denied(self, cursor, parameters, keepdb=False):
        raise DatabaseError(1044, "Access denied for user")

    def patch_test_db_creation(self, execute_create_test_db):
        return mock.patch.object(BaseDatabaseCreation, '_execute_create_test_db', execute_create_test_db)

    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_create_test_db_database_exists(self, *mocked_objects):
        # Simulate test database creation raising "database exists"
        creation = DatabaseCreation(connection)
        with self.patch_test_db_creation(self._execute_raise_database_exists):
            with mock.patch('builtins.input', return_value='no'):
                with self.assertRaises(SystemExit):
                    # SystemExit is raised if the user answers "no" to the
                    # prompt asking if it's okay to delete the test database.
                    creation._create_test_db(verbosity=0, autoclobber=False, keepdb=False)
            # "Database exists" shouldn't appear when keepdb is on
            creation._create_test_db(verbosity=0, autoclobber=False, keepdb=True)

    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_create_test_db_unexpected_error(self, *mocked_objects):
        # Simulate test database creation raising unexpected error
        creation = DatabaseCreation(connection)
        with self.patch_test_db_creation(self._execute_raise_access_denied):
            with self.assertRaises(SystemExit):
                creation._create_test_db(verbosity=0, autoclobber=False, keepdb=False)
