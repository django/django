import unittest

from django.db import connection


@unittest.skipUnless(connection.vendor == 'oracle', 'Oracle tests')
class OperationsTests(unittest.TestCase):

    def test_sequence_name_truncation(self):
        seq_name = connection.ops._get_no_autofield_sequence_name('schema_authorwithevenlongee869')
        self.assertEqual(seq_name, 'SCHEMA_AUTHORWITHEVENLOB0B8_SQ')

    def test_bulk_batch_size(self):
        # Oracle restricts the number of parameters in a query.
        objects = range(2**16)
        self.assertEqual(connection.ops.bulk_batch_size([], objects), len(objects))
        # Each field is a parameter for each object.
        self.assertEqual(
            connection.ops.bulk_batch_size(['id'], objects),
            connection.features.max_query_params,
        )
        self.assertEqual(
            connection.ops.bulk_batch_size(['id', 'other'], objects),
            connection.features.max_query_params // 2,
        )
