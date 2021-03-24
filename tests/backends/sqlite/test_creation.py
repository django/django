import copy
import unittest
import os
from random import randint


from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.test import SimpleTestCase


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class TestDbSignatureTests(SimpleTestCase):
    def test_custom_test_name(self):
        test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
        test_connection.settings_dict = copy.deepcopy(connections[DEFAULT_DB_ALIAS].settings_dict)
        test_connection.settings_dict['NAME'] = None
        test_connection.settings_dict['TEST']['NAME'] = 'custom.sqlite.db'
        signature = test_connection.creation_class(test_connection).test_db_signature()
        self.assertEqual(signature, (None, 'custom.sqlite.db'))

    def test_parallel_test_name(self):
        test_connection = copy.copy(connections[DEFAULT_DB_ALIAS])
        test_connection.settings_dict = copy.deepcopy(connections[DEFAULT_DB_ALIAS].settings_dict)
        test_connection.settings_dict['NAME'] = 'test.sqlite3'
        test_connection.settings_dict['TEST']['NAME'] = 'test.sqlite3'
        random_suffix = randint(1, 100)
        root, ext = os.path.splitext(test_connection.settings_dict['NAME'])
        settings_dict = test_connection.creation_class(test_connection).get_test_db_clone_settings(random_suffix)
        self.assertEqual(settings_dict['NAME'], '{}_{}{}'.format(root, random_suffix, ext))
