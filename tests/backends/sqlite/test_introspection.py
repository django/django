import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite tests')
class IntrospectionTests(TestCase):
    def test_get_primary_key_column(self):
        """
        Get the primary key column regardless of whether or not it has
        quotation.
        """
        testable_column_strings = (
            ('id', 'id'), ('[id]', 'id'), ('`id`', 'id'), ('"id"', 'id'),
            ('[id col]', 'id col'), ('`id col`', 'id col'), ('"id col"', 'id col')
        )
        with connection.cursor() as cursor:
            for column, expected_string in testable_column_strings:
                sql = 'CREATE TABLE test_primary (%s int PRIMARY KEY NOT NULL)' % column
                with self.subTest(column=column):
                    try:
                        cursor.execute(sql)
                        field = connection.introspection.get_primary_key_column(cursor, 'test_primary')
                        self.assertEqual(field, expected_string)
                    finally:
                        cursor.execute('DROP TABLE test_primary')
