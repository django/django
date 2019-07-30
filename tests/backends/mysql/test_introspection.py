from unittest import skipUnless

from django.db import connection
from django.test import TestCase


@skipUnless(connection.vendor == 'mysql', 'MySQL tests')
class ParsingTests(TestCase):
    def test_parse_constraint_columns(self):
        tests = (
            ('`height` >= 0', ['height']),
            ('`cost` BETWEEN 1 AND 10', ['cost']),
            ('`ref1` > `ref2`', ['ref1', 'ref2']),
            (
                '`start` IS NULL OR `end` IS NULL OR `start` < `end`',
                ['start', 'end'],
            ),
        )
        for check_clause, expected_columns in tests:
            with self.subTest(check_clause):
                check_columns = connection.introspection._parse_constraint_columns(check_clause)
                self.assertEqual(list(check_columns), expected_columns)
