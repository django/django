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
            # First, we create a test table
            cursor.execute(
                """
                CREATE TABLE TEST_TABLE (
                    TEST_FIELD VARCHAR2(100) COLLATE BINARY_CI
                )
            """
            )
            try:
                # Then we get the description of the table
                description = connection.introspection.get_table_description(
                    cursor, "TEST_TABLE"
                )

                # Finally, we make assertions about the table description
                self.assertEqual(len(description), 1)
                self.assertEqual(description[0][0], "TEST_FIELD")
                self.assertEqual(description[0][1], "VARCHAR2")
            finally:
                # Clean up after ourselves by removing the test table
                cursor.execute("DROP TABLE TEST_TABLE")
