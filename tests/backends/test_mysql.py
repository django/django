import unittest

from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings


@override_settings(DEBUG=True)
@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL specific test.')
class MySQLTests(TestCase):

    @staticmethod
    def get_isolation_level(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT @@session.tx_isolation")
            return cursor.fetchone()[0]

    def test_auto_is_null_auto_config(self):
        query = 'set sql_auto_is_null = 0'
        connection.init_connection_state()
        last_query = connection.queries[-1]['sql'].lower()
        if connection.features.is_sql_auto_is_null_enabled:
            self.assertIn(query, last_query)
        else:
            self.assertNotIn(query, last_query)

    def test_connect_isolation_level(self):
        read_committed = 'read committed'
        repeatable_read = 'repeatable read'
        isolation_values = {
            level: level.replace(' ', '-').upper()
            for level in (read_committed, repeatable_read)
        }
        configured_level = connection.isolation_level or isolation_values[repeatable_read]
        configured_level = configured_level.upper()
        other_level = read_committed if configured_level != isolation_values[read_committed] else repeatable_read

        self.assertEqual(self.get_isolation_level(connection), configured_level)

        new_connection = connection.copy()
        new_connection.settings_dict['OPTIONS']['isolation_level'] = other_level
        try:
            self.assertEqual(self.get_isolation_level(new_connection), isolation_values[other_level])
        finally:
            new_connection.close()

        # Upper case values are also accepted in 'isolation_level'.
        new_connection = connection.copy()
        new_connection.settings_dict['OPTIONS']['isolation_level'] = other_level.upper()
        try:
            self.assertEqual(self.get_isolation_level(new_connection), isolation_values[other_level])
        finally:
            new_connection.close()

    def test_isolation_level_validation(self):
        new_connection = connection.copy()
        new_connection.settings_dict['OPTIONS']['isolation_level'] = 'xxx'
        msg = (
            "Invalid transaction isolation level 'xxx' specified.\n"
            "Use one of 'read committed', 'read uncommitted', "
            "'repeatable read', 'serializable', or None."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            new_connection.cursor()
