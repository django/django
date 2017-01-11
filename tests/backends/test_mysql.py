from __future__ import unicode_literals

import unittest

from django.db import connection
from django.test import TestCase, override_settings


@override_settings(DEBUG=True)
@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL specific test.')
class MySQLTests(TestCase):

    def test_auto_is_null_auto_config(self):
        query = 'set sql_auto_is_null = 0'
        connection.init_connection_state()
        last_query = connection.queries[-1]['sql'].lower()
        if connection.features.is_sql_auto_is_null_enabled:
            self.assertIn(query, last_query)
        else:
            self.assertNotIn(query, last_query)

    def test_connect_isolation_level(self):
        """
        Inspired by a similarly-named PostrgreSQL test in tests.py
        """
        read_committed = 'read committed'
        repeatable_read = 'repeatable read'

        isolation_values = {
            level: level.replace(' ', '-').upper()
            for level in (read_committed, repeatable_read)
        }

        configured_level = connection.isolation_level or repeatable_read
        other_level = read_committed if configured_level != read_committed else repeatable_read

        with connection.cursor() as cursor:
            cursor.execute("SELECT @@session.tx_isolation")
            tx_isolation = cursor.fetchone()[0]
        self.assertEqual(tx_isolation, isolation_values[configured_level])

        new_connection = connection.copy()
        new_connection.settings_dict['OPTIONS']['isolation_level'] = other_level
        try:
            with new_connection.cursor() as cursor:
                cursor.execute("SELECT @@session.tx_isolation")
                tx_isolation = cursor.fetchone()[0]
            self.assertEqual(tx_isolation, isolation_values[other_level])
        finally:
            new_connection.close()
