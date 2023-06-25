import unittest

from django.db import connection
from django.test import TransactionTestCase

from ..models import Square


@unittest.skipUnless(connection.vendor == "oracle", "Oracle tests")
class DatabaseSequenceTests(TransactionTestCase):
    available_apps = []

    def test_get_sequences(self):
        with connection.cursor() as cursor:
            seqs = connection.introspection.get_sequences(
                cursor, Square._meta.db_table, Square._meta.local_fields
            )
            self.assertEqual(len(seqs), 1)
            self.assertIsNotNone(seqs[0]["name"])
            self.assertEqual(seqs[0]["table"], Square._meta.db_table)
            self.assertEqual(seqs[0]["column"], "id")

    def test_get_sequences_manually_created_index(self):
        with connection.cursor() as cursor:
            with connection.schema_editor() as editor:
                editor._drop_identity(Square._meta.db_table, "id")
                seqs = connection.introspection.get_sequences(
                    cursor, Square._meta.db_table, Square._meta.local_fields
                )
                self.assertEqual(
                    seqs, [{"table": Square._meta.db_table, "column": "id"}]
                )
                # Recreate model, because adding identity is impossible.
                editor.delete_model(Square)
                editor.create_model(Square)

    def test_get_table_description(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM %s" % Square._meta.db_table)
            description = connection.introspection.get_table_description(
                cursor, Square._meta.db_table
            )
            self.assertEqual(len(description), 2)
            self.assertEqual(description[0][0], "ID")
            self.assertEqual(description[1][0], "NAME")
