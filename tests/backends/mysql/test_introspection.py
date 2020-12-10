from unittest import skipUnless

from django.db import connection
from django.test import TestCase


@skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class ParsingTests(TestCase):
    def test_parse_constraint_columns(self):
        _parse_constraint_columns = connection.introspection._parse_constraint_columns
        tests = (
            ('`height` >= 0', ['height'], ['height']),
            ('`cost` BETWEEN 1 AND 10', ['cost'], ['cost']),
            ('`ref1` > `ref2`', ['id', 'ref1', 'ref2'], ['ref1', 'ref2']),
            (
                '`start` IS NULL OR `end` IS NULL OR `start` < `end`',
                ['id', 'start', 'end'],
                ['start', 'end'],
            ),
            ('JSON_VALID(`json_field`)', ['json_field'], ['json_field']),
            ('CHAR_LENGTH(`name`) > 2', ['name'], ['name']),
            ("lower(`ref1`) != 'test'", ['id', 'owe', 'ref1'], ['ref1']),
            ("lower(`ref1`) != 'test'", ['id', 'lower', 'ref1'], ['ref1']),
            ("`name` LIKE 'test%'", ['name'], ['name']),
        )
        for check_clause, table_columns, expected_columns in tests:
            with self.subTest(check_clause):
                check_columns = _parse_constraint_columns(check_clause, table_columns)
                self.assertEqual(list(check_columns), expected_columns)
