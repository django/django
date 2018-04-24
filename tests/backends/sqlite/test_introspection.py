import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class IntrospectionTests(TestCase):
    def test_get_primary_key_column(self):
        """Get the primary key column regardless of whether or not it has quotation."""
        with connection.cursor() as cursor:
            try:
                cursor.execute('CREATE TABLE `test_primary` (id int PRIMARY KEY NOT NULL);')
                field = connection.introspection.get_primary_key_column(cursor, 'test_primary')
                self.assertEqual(field, 'id')
            finally:
                cursor.execute('DROP TABLE `test_primary`;')
