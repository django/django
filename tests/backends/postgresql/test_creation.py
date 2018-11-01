import unittest
from contextlib import contextmanager
from io import StringIO
from unittest import mock

from django.db import connection
from django.db.backends.base.creation import BaseDatabaseCreation
from django.db.utils import DatabaseError
from django.test import SimpleTestCase

try:
    import psycopg2  # NOQA
except ImportError:
    pass
else:
    from psycopg2 import errorcodes
    from django.db.backends.postgresql.creation import DatabaseCreation


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL tests')
class DatabaseCreationTests(SimpleTestCase):

    @contextmanager
    def changed_test_settings(self, **kwargs):
        settings = connection.settings_dict['TEST']
        saved_values = {}
        for name in kwargs:
            if name in settings:
                saved_values[name] = settings[name]

        for name, value in kwargs.items():
            settings[name] = value
        try:
            yield
        finally:
            for name in kwargs:
                if name in saved_values:
                    settings[name] = saved_values[name]
                else:
                    del settings[name]

    def check_sql_table_creation_suffix(self, settings, expected):
        with self.changed_test_settings(**settings):
            creation = DatabaseCreation(connection)
            suffix = creation.sql_table_creation_suffix()
            self.assertEqual(suffix, expected)

    def test_sql_table_creation_suffix_with_none_settings(self):
        settings = {'CHARSET': None, 'TEMPLATE': None}
        self.check_sql_table_creation_suffix(settings, "")

    def test_sql_table_creation_suffix_with_encoding(self):
        settings = {'CHARSET': 'UTF8'}
        self.check_sql_table_creation_suffix(settings, "WITH ENCODING 'UTF8'")

    def test_sql_table_creation_suffix_with_template(self):
        settings = {'TEMPLATE': 'template0'}
        self.check_sql_table_creation_suffix(settings, 'WITH TEMPLATE "template0"')

    def test_sql_table_creation_suffix_with_encoding_and_template(self):
        settings = {'CHARSET': 'UTF8', 'TEMPLATE': 'template0'}
        self.check_sql_table_creation_suffix(settings, '''WITH ENCODING 'UTF8' TEMPLATE "template0"''')

    def _execute_raise_database_already_exists(self, cursor, parameters, keepdb=False):
        error = DatabaseError('database %s already exists' % parameters['dbname'])
        error.pgcode = errorcodes.DUPLICATE_DATABASE
        raise DatabaseError() from error

    def _execute_raise_permission_denied(self, cursor, parameters, keepdb=False):
        error = DatabaseError('permission denied to create database')
        error.pgcode = errorcodes.INSUFFICIENT_PRIVILEGE
        raise DatabaseError() from error

    def patch_test_db_creation(self, execute_create_test_db):
        return mock.patch.object(BaseDatabaseCreation, '_execute_create_test_db', execute_create_test_db)

    @mock.patch('sys.stdout', new_callable=StringIO)
    @mock.patch('sys.stderr', new_callable=StringIO)
    def test_create_test_db(self, *mocked_objects):
        creation = DatabaseCreation(connection)
        # Simulate test database creation raising "database already exists"
        with self.patch_test_db_creation(self._execute_raise_database_already_exists):
            with mock.patch('builtins.input', return_value='no'):
                with self.assertRaises(SystemExit):
                    # SystemExit is raised if the user answers "no" to the
                    # prompt asking if it's okay to delete the test database.
                    creation._create_test_db(verbosity=0, autoclobber=False, keepdb=False)
            # "Database already exists" error is ignored when keepdb is on
            creation._create_test_db(verbosity=0, autoclobber=False, keepdb=True)
        # Simulate test database creation raising unexpected error
        with self.patch_test_db_creation(self._execute_raise_permission_denied):
            with mock.patch.object(DatabaseCreation, '_database_exists', return_value=False):
                with self.assertRaises(SystemExit):
                    creation._create_test_db(verbosity=0, autoclobber=False, keepdb=False)
                with self.assertRaises(SystemExit):
                    creation._create_test_db(verbosity=0, autoclobber=False, keepdb=True)
        # Simulate test database creation raising "insufficient privileges".
        # An error shouldn't appear when keepdb is on and the database already
        # exists.
        with self.patch_test_db_creation(self._execute_raise_permission_denied):
            with mock.patch.object(DatabaseCreation, '_database_exists', return_value=True):
                creation._create_test_db(verbosity=0, autoclobber=False, keepdb=True)
