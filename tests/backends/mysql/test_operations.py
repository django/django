import unittest

from django.core.management.color import no_style
from django.db import connection
from django.test import SimpleTestCase

from ..models import Person, Square, Tag


@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL tests.')
class MySQLOperationsTests(SimpleTestCase):
    def test_sql_flush(self):
        # allow_cascade doesn't change statements on MySQL.
        for allow_cascade in [False, True]:
            with self.subTest(allow_cascade=allow_cascade):
                statements = connection.ops.sql_flush(
                    no_style(),
                    [Person._meta.db_table, Tag._meta.db_table],
                    [],
                    allow_cascade=allow_cascade,
                )
                self.assertEqual(statements[0], 'SET FOREIGN_KEY_CHECKS = 0;')
                # The tables are processed in an unordered set.
                self.assertEqual(
                    sorted(statements[1:-1]),
                    [
                        'DELETE FROM `backends_person`;',
                        'DELETE FROM `backends_tag`;',
                    ],
                )
                self.assertEqual(statements[-1], 'SET FOREIGN_KEY_CHECKS = 1;')

    def test_sql_flush_sequences(self):
        # allow_cascade doesn't change statements on MySQL.
        for allow_cascade in [False, True]:
            with self.subTest(allow_cascade=allow_cascade):
                statements = connection.ops.sql_flush(
                    no_style(),
                    [Person._meta.db_table, Square._meta.db_table, Tag._meta.db_table],
                    [
                        {
                            'table': Person._meta.db_table,
                            'column': Person._meta.pk.db_column,
                        },
                        {
                            'table': Tag._meta.db_table,
                            'column': Tag._meta.pk.db_column,
                        },
                    ],
                    allow_cascade=allow_cascade,
                )
                self.assertEqual(statements[0], 'SET FOREIGN_KEY_CHECKS = 0;')
                # The tables are processed in an unordered set.
                self.assertEqual(
                    sorted(statements[1:-1]),
                    [
                        'DELETE FROM `backends_square`;',
                        'TRUNCATE `backends_person`;',
                        'TRUNCATE `backends_tag`;',
                    ],
                )
                self.assertEqual(statements[-1], 'SET FOREIGN_KEY_CHECKS = 1;')
