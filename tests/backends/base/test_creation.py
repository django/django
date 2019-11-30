import copy
from unittest import mock

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.creation import (
    TEST_DATABASE_PREFIX, BaseDatabaseCreation,
)
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


@mock.patch.object(connection, 'ensure_connection')
@mock.patch('django.core.management.commands.migrate.Command.handle', return_value=None)
class TestDbCreationTests(SimpleTestCase):
    def test_migrate_test_setting_false(self, mocked_migrate, mocked_ensure_connection):
        creation = connection.creation_class(connection)
        saved_settings = copy.deepcopy(connection.settings_dict)
        try:
            connection.settings_dict['TEST']['MIGRATE'] = False
            with mock.patch.object(creation, '_create_test_db'):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            mocked_migrate.assert_not_called()
        finally:
            connection.settings_dict = saved_settings

    def test_migrate_test_setting_true(self, mocked_migrate, mocked_ensure_connection):
        creation = connection.creation_class(connection)
        saved_settings = copy.deepcopy(connection.settings_dict)
        try:
            connection.settings_dict['TEST']['MIGRATE'] = True
            with mock.patch.object(creation, '_create_test_db'):
                creation.create_test_db(verbosity=0, autoclobber=True, serialize=False)
            mocked_migrate.assert_called_once()
        finally:
            connection.settings_dict = saved_settings
