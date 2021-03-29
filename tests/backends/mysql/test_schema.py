import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class SchemaEditorTests(TestCase):
    def test_quote_value(self):
        import MySQLdb
        editor = connection.schema_editor()
        tested_values = [
            ('string', "'string'"),
            ('¿Tú hablas inglés?', "'¿Tú hablas inglés?'"),
            (b'bytes', b"'bytes'"),
            (42, '42'),
            (1.754, '1.754e0' if MySQLdb.version_info >= (1, 3, 14) else '1.754'),
            (False, b'0' if MySQLdb.version_info >= (1, 4, 0) else '0'),
        ]
        for value, expected in tested_values:
            with self.subTest(value=value):
                self.assertEqual(editor.quote_value(value), expected)
