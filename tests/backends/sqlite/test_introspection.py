import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class IntrospectionTests(TestCase):
    def test_get_primary_key_column(self):
        """Get the primary key column regardless of whether or not it has quotation."""
        testable_primary_key_columns = ('id', '[id]', '`id`', '"id"')
        with connection.cursor() as cursor:
            for column in testable_primary_key_columns:
                sql = "CREATE TABLE `test_primary` (%s int PRIMARY KEY NOT NULL);" % column
                try:
                    cursor.execute(sql)
                    field = connection.introspection.get_primary_key_column(cursor, 'test_primary')
                    self.assertEqual(field, 'id')
                finally:
                    cursor.execute('DROP TABLE `test_primary`;')
