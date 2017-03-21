import copy
import unittest
from contextlib import contextmanager
from io import StringIO
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.creation import (
    TEST_DATABASE_PREFIX, BaseDatabaseCreation,
)
from django.db.backends.oracle.creation import \
    DatabaseCreation as OracleDatabaseCreation
from django.db.backends.postgresql.creation import \
    DatabaseCreation as PostgreSQLDatabaseCreation
from django.db.utils import DatabaseError
from django.test import SimpleTestCase, TestCase


class TestDbSignatureTests(SimpleTestCase):

    def get_connection_copy(self):
        # Get a copy of the default connection. (Can't use django.db.connection
        # because it'll modify the default connection itself.)
        test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
        test_connection.settings_dict = copy.copy(connections[DEFAULT_DB_ALIAS].settings_dict)
        return test_connection

    def test_default_name(self):
        # A test db name isn't set.
        prod_name = 'hodor'
        test_connection = self.get_connection_copy()
        test_connection.settings_dict['NAME'] = prod_name
        test_connection.settings_dict['TEST'] = {'NAME': None}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], TEST_DATABASE_PREFIX + prod_name)

    def test_custom_test_name(self):
        # A regular test db name is set.
        test_name = 'hodor'
        test_connection = self.get_connection_copy()
        test_connection.settings_dict['TEST'] = {'NAME': test_name}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], test_name)

    def test_custom_test_name_with_test_prefix(self):
        # A test db name prefixed with TEST_DATABASE_PREFIX is set.
        test_name = TEST_DATABASE_PREFIX + 'hodor'
        test_connection = self.get_connection_copy()
        test_connection.settings_dict['TEST'] = {'NAME': test_name}
        signature = BaseDatabaseCreation(test_connection).test_db_signature()
        self.assertEqual(signature[3], test_name)


@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL-specific tests")
class PostgreSQLDatabaseCreationTests(SimpleTestCase):

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
            for name, value in kwargs.items():
                if name in saved_values:
                    settings[name] = saved_values[name]
                else:
                    del settings[name]

    def check_sql_table_creation_suffix(self, settings, expected):
        with self.changed_test_settings(**settings):
            creation = PostgreSQLDatabaseCreation(connection)
            suffix = creation.sql_table_creation_suffix()
            self.assertEqual(suffix, expected)

    def test_sql_table_creation_suffix_with_none_settings(self):
        settings = dict(CHARSET=None, TEMPLATE=None)
        self.check_sql_table_creation_suffix(settings, "")

    def test_sql_table_creation_suffix_with_encoding(self):
        settings = dict(CHARSET='UTF8')
        self.check_sql_table_creation_suffix(settings, "WITH ENCODING 'UTF8'")

    def test_sql_table_creation_suffix_with_template(self):
        settings = dict(TEMPLATE='template0')
        self.check_sql_table_creation_suffix(settings, 'WITH TEMPLATE "template0"')

    def test_sql_table_creation_suffix_with_encoding_and_template(self):
        settings = dict(CHARSET='UTF8', TEMPLATE='template0')
        self.check_sql_table_creation_suffix(settings, '''WITH ENCODING 'UTF8' TEMPLATE "template0"''')


@unittest.skipUnless(connection.vendor == 'oracle', "Oracle specific tests")
@mock.patch.object(OracleDatabaseCreation, '_maindb_connection', return_value=connection)
@mock.patch('sys.stdout', new_callable=StringIO)
@mock.patch('sys.stderr', new_callable=StringIO)
class OracleDatabaseCreationTests(TestCase):

    def _execute_raise_user_already_exists(self, cursor, statements, parameters, verbosity, allow_quiet_fail=False):
        # Raise "user already exists" only in test user creation
        if statements and statements[0].startswith('CREATE USER'):
            raise DatabaseError("ORA-01920: user name 'string' conflicts with another user or role name")

    def _execute_raise_tablespace_already_exists(
        self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
    ):
        raise DatabaseError("ORA-01543: tablespace 'string' already exists")

    def _execute_raise_insufficient_privileges(
        self, cursor, statements, parameters, verbosity, allow_quiet_fail=False
    ):
        raise DatabaseError("ORA-01031: insufficient privileges")

    def _test_database_passwd(self):
        # Mocked to avoid test user password changed
        return connection.settings_dict['SAVED_PASSWORD']

    def patch_execute_statements(self, execute_statements):
        return mock.patch.object(OracleDatabaseCreation, '_execute_statements', execute_statements)

    @mock.patch.object(OracleDatabaseCreation, '_test_user_create', return_value=False)
    def test_create_test_db(self, *mocked_objects):
        creation = OracleDatabaseCreation(connection)
        # Simulate test database creation raising "tablespace already exists"
        with self.patch_execute_statements(self._execute_raise_tablespace_already_exists):
            with mock.patch('builtins.input', return_value='no'):
                with self.assertRaises(SystemExit):
                    # SystemExit is raised if the user answers "no" to the
                    # prompt asking if it's okay to delete the test tablespace.
                    creation._create_test_db(verbosity=0, keepdb=False)
            # "Tablespace already exists" error is ignored when keepdb is on
            creation._create_test_db(verbosity=0, keepdb=True)
        # Simulate test database creation raising unexpected error
        with self.patch_execute_statements(self._execute_raise_insufficient_privileges):
            with self.assertRaises(SystemExit):
                creation._create_test_db(verbosity=0, keepdb=False)
            with self.assertRaises(SystemExit):
                creation._create_test_db(verbosity=0, keepdb=True)

    @mock.patch.object(OracleDatabaseCreation, '_test_database_create', return_value=False)
    def test_create_test_user(self, *mocked_objects):
        creation = OracleDatabaseCreation(connection)
        with mock.patch.object(OracleDatabaseCreation, '_test_database_passwd', self._test_database_passwd):
            # Simulate test user creation raising "user already exists"
            with self.patch_execute_statements(self._execute_raise_user_already_exists):
                with mock.patch('builtins.input', return_value='no'):
                    with self.assertRaises(SystemExit):
                        # SystemExit is raised if the user answers "no" to the
                        # prompt asking if it's okay to delete the test user.
                        creation._create_test_db(verbosity=0, keepdb=False)
                # "User already exists" error is ignored when keepdb is on
                creation._create_test_db(verbosity=0, keepdb=True)
            # Simulate test user creation raising unexpected error
            with self.patch_execute_statements(self._execute_raise_insufficient_privileges):
                with self.assertRaises(SystemExit):
                    creation._create_test_db(verbosity=0, keepdb=False)
                with self.assertRaises(SystemExit):
                    creation._create_test_db(verbosity=0, keepdb=True)
