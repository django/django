import copy
import unittest
from contextlib import contextmanager

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.creation import (
    TEST_DATABASE_PREFIX, BaseDatabaseCreation,
)
from django.db.backends.postgresql.creation import DatabaseCreation
from django.test import SimpleTestCase


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
            creation = DatabaseCreation(connection)
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
