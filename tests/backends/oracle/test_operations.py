import unittest

from django.db import connection


@unittest.skipUnless(connection.vendor == 'oracle', 'Oracle tests')
class OperationsTests(unittest.TestCase):

    def test_sequence_name_truncation(self):
        seq_name = connection.ops._get_no_autofield_sequence_name('schema_authorwithevenlongee869')
        self.assertEqual(seq_name, 'SCHEMA_AUTHORWITHEVENLOB0B8_SQ')
