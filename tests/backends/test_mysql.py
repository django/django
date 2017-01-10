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
        read_committed = 'READ COMMITTED'
        repeatable_read = 'REPEATABLE READ'

        isolation_values = {
            level: level.replace(' ', '-')
            for level in (read_committed, repeatable_read)
        }

        # This test assumes that MySQL is configured with the default isolation level.

        with connection.cursor() as cursor:
            cursor.execute("SELECT @@session.tx_isolation")
            tx_isolation = cursor.fetchone()[0]
        self.assertEqual(tx_isolation, isolation_values[repeatable_read])

        new_connection = connection.copy()
        new_connection.settings_dict['OPTIONS']['isolation_level'] = read_committed
        try:
            with new_connection.cursor() as cursor:
                cursor.execute("SELECT @@session.tx_isolation")
                tx_isolation = cursor.fetchone()[0]
            self.assertEqual(tx_isolation, isolation_values[read_committed])
        finally:
            new_connection.close()
