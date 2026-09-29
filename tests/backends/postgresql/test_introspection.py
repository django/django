import unittest

from django.db import connection
from django.test import TestCase

from ..models import Person


@unittest.skipUnless(connection.vendor == "postgresql", "Test only for PostgreSQL")
class DatabaseSequenceTests(TestCase):
    def test_get_sequences(self):
        with connection.cursor() as cursor:
            seqs = connection.introspection.get_sequences(cursor, Person._meta.db_table)
            self.assertEqual(
                seqs,
                [
                    {
                        "table": Person._meta.db_table,
                        "column": "id",
                        "name": "backends_person_id_seq",
                    }
                ],
            )
            cursor.execute("ALTER SEQUENCE backends_person_id_seq RENAME TO pers_seq")
            seqs = connection.introspection.get_sequences(cursor, Person._meta.db_table)
            self.assertEqual(
                seqs,
                [{"table": Person._meta.db_table, "column": "id", "name": "pers_seq"}],
            )

    def test_get_sequences_old_serial(self):
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE testing (serial_field SERIAL);")
            seqs = connection.introspection.get_sequences(cursor, "testing")
            self.assertEqual(
                seqs,
                [
                    {
                        "table": "testing",
                        "column": "serial_field",
                        "name": "testing_serial_field_seq",
                    }
                ],
            )


@unittest.skipUnless(connection.vendor == "postgresql", "Test only for PostgreSQL")
class TableListTests(TestCase):
    def test_get_table_list_for_names(self):
        with connection.cursor() as cursor:
            table_list = connection.introspection.get_table_list_for_names(
                cursor, {Person._meta.db_table, "backends_nonexistent"}
            )
        self.assertEqual([table.name for table in table_list], [Person._meta.db_table])

    def test_table_names_only_tables_search_path(self):
        """Tables in schemas that aren't in the search path are excluded."""
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA backends_hidden")
            cursor.execute("CREATE TABLE backends_hidden.backends_hidden (id int)")
            self.assertEqual(
                connection.introspection.table_names(
                    cursor, only_tables=["backends_hidden"]
                ),
                [],
            )
            cursor.execute("SET LOCAL search_path TO backends_hidden, public")
            self.assertEqual(
                connection.introspection.table_names(
                    cursor, only_tables=["backends_hidden"]
                ),
                ["backends_hidden"],
            )
