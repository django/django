import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class SchemaEditorTests(TestCase):
    def test_quote_value(self):
        editor = connection.schema_editor()
        tested_values = [
            ('string', "'string'"),
            (42, '42'),
            (1.754, '1.754'),
            (False, '0'),
        ]
        for value, expected in tested_values:
            with self.subTest(value=value):
                self.assertEqual(editor.quote_value(value), expected)
