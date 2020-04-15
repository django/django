import unittest

from django.core.management.color import no_style
from django.db import connection
from django.test import SimpleTestCase

from ..models import Person, Tag


@unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL tests.')
class PostgreSQLOperationsTests(SimpleTestCase):
    def test_sql_flush(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
                [],
            ),
            ['TRUNCATE "backends_person", "backends_tag";'],
        )

    def test_sql_flush_allow_cascade(self):
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
                [],
                allow_cascade=True,
            ),
            ['TRUNCATE "backends_person", "backends_tag" CASCADE;'],
        )

    def test_sql_flush_sequences(self):
        sequence_reset_sql = (
            "SELECT setval(pg_get_serial_sequence('%s','id'), 1, false);"
        )
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
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
            ),
            [
                'TRUNCATE "backends_person", "backends_tag";',
                sequence_reset_sql % '"backends_person"',
                sequence_reset_sql % '"backends_tag"',
            ],
        )

    def test_sql_flush_sequences_allow_cascade(self):
        sequence_reset_sql = (
            "SELECT setval(pg_get_serial_sequence('%s','id'), 1, false);"
        )
        self.assertEqual(
            connection.ops.sql_flush(
                no_style(),
                [Person._meta.db_table, Tag._meta.db_table],
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
                allow_cascade=True,
            ),
            [
                'TRUNCATE "backends_person", "backends_tag" CASCADE;',
                sequence_reset_sql % '"backends_person"',
                sequence_reset_sql % '"backends_tag"',
            ],
        )
