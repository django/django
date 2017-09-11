import unittest

from django.db import connection
from django.test import TestCase

from ..models import Person


@unittest.skipUnless(connection.vendor == 'postgresql', "Test only for PostgreSQL")
class DatabaseSequenceTests(TestCase):
    def test_get_sequences(self):
        cursor = connection.cursor()
        seqs = connection.introspection.get_sequences(cursor, Person._meta.db_table)
        self.assertEqual(
            seqs,
            [{'table': Person._meta.db_table, 'column': 'id', 'name': 'backends_person_id_seq'}]
        )
        cursor.execute('ALTER SEQUENCE backends_person_id_seq RENAME TO pers_seq')
        seqs = connection.introspection.get_sequences(cursor, Person._meta.db_table)
        self.assertEqual(
            seqs,
            [{'table': Person._meta.db_table, 'column': 'id', 'name': 'pers_seq'}]
        )
