import unittest

from django.db import connection
from django.test import TransactionTestCase

from ..models import Person


@unittest.skipUnless(connection.vendor == 'oracle', 'Oracle tests')
class DatabaseSequenceTests(TransactionTestCase):
    available_apps = []

    def test_get_sequences(self):
        with connection.cursor() as cursor:
            seqs = connection.introspection.get_sequences(cursor, Person._meta.db_table, Person._meta.local_fields)
            self.assertEqual(len(seqs), 1)
            self.assertIsNotNone(seqs[0]['name'])
            self.assertEqual(seqs[0]['table'], Person._meta.db_table)
            self.assertEqual(seqs[0]['column'], 'id')

    def test_get_sequences_manually_created_index(self):
        with connection.cursor() as cursor:
            with connection.schema_editor() as editor:
                editor._drop_identity(Person._meta.db_table, 'id')
                seqs = connection.introspection.get_sequences(cursor, Person._meta.db_table, Person._meta.local_fields)
                self.assertEqual(seqs, [{'table': Person._meta.db_table, 'column': 'id'}])
                # Recreate model, because adding identity is impossible.
                editor.delete_model(Person)
                editor.create_model(Person)
