"""Tests for django.db.backends.utils"""
from decimal import Decimal, Rounded

from django.db import connection
from django.db.backends.utils import (
    format_number, split_identifier, truncate_name,
)
from django.db.utils import NotSupportedError
from django.test import (
    SimpleTestCase, TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)


class TestUtils(SimpleTestCase):

    def test_truncate_name(self):
        self.assertEqual(truncate_name('some_table', 10), 'some_table')
        self.assertEqual(truncate_name('some_long_table', 10), 'some_la38a')
        self.assertEqual(truncate_name('some_long_table', 10, 3), 'some_loa38')
        self.assertEqual(truncate_name('some_long_table'), 'some_long_table')
        # "user"."table" syntax
        self.assertEqual(truncate_name('username"."some_table', 10), 'username"."some_table')
        self.assertEqual(truncate_name('username"."some_long_table', 10), 'username"."some_la38a')
        self.assertEqual(truncate_name('username"."some_long_table', 10, 3), 'username"."some_loa38')

    def test_split_identifier(self):
        self.assertEqual(split_identifier('some_table'), ('', 'some_table'))
        self.assertEqual(split_identifier('"some_table"'), ('', 'some_table'))
        self.assertEqual(split_identifier('namespace"."some_table'), ('namespace', 'some_table'))
        self.assertEqual(split_identifier('"namespace"."some_table"'), ('namespace', 'some_table'))

    def test_format_number(self):
        def equal(value, max_d, places, result):
            self.assertEqual(format_number(Decimal(value), max_d, places), result)

        equal('0', 12, 3, '0.000')
        equal('0', 12, 8, '0.00000000')
        equal('1', 12, 9, '1.000000000')
        equal('0.00000000', 12, 8, '0.00000000')
        equal('0.000000004', 12, 8, '0.00000000')
        equal('0.000000008', 12, 8, '0.00000001')
        equal('0.000000000000000000999', 10, 8, '0.00000000')
        equal('0.1234567890', 12, 10, '0.1234567890')
        equal('0.1234567890', 12, 9, '0.123456789')
        equal('0.1234567890', 12, 8, '0.12345679')
        equal('0.1234567890', 12, 5, '0.12346')
        equal('0.1234567890', 12, 3, '0.123')
        equal('0.1234567890', 12, 1, '0.1')
        equal('0.1234567890', 12, 0, '0')
        equal('0.1234567890', None, 0, '0')
        equal('1234567890.1234567890', None, 0, '1234567890')
        equal('1234567890.1234567890', None, 2, '1234567890.12')
        equal('0.1234', 5, None, '0.1234')
        equal('123.12', 5, None, '123.12')

        with self.assertRaises(Rounded):
            equal('0.1234567890', 5, None, '0.12346')
        with self.assertRaises(Rounded):
            equal('1234567890.1234', 5, None, '1234600000')


class CursorWrapperTests(TransactionTestCase):
    available_apps = []

    def _test_procedure(self, procedure_sql, params, param_types, kparams=None):
        with connection.cursor() as cursor:
            cursor.execute(procedure_sql)
        # Use a new cursor because in MySQL a procedure can't be used in the
        # same cursor in which it was created.
        with connection.cursor() as cursor:
            cursor.callproc('test_procedure', params, kparams)
        with connection.schema_editor() as editor:
            editor.remove_procedure('test_procedure', param_types)

    @skipUnlessDBFeature('create_test_procedure_without_params_sql')
    def test_callproc_without_params(self):
        self._test_procedure(connection.features.create_test_procedure_without_params_sql, [], [])

    @skipUnlessDBFeature('create_test_procedure_with_int_param_sql')
    def test_callproc_with_int_params(self):
        self._test_procedure(connection.features.create_test_procedure_with_int_param_sql, [1], ['INTEGER'])

    @skipUnlessDBFeature('create_test_procedure_with_int_param_sql', 'supports_callproc_kwargs')
    def test_callproc_kparams(self):
        self._test_procedure(connection.features.create_test_procedure_with_int_param_sql, [], ['INTEGER'], {'P_I': 1})

    @skipIfDBFeature('supports_callproc_kwargs')
    def test_unsupported_callproc_kparams_raises_error(self):
        msg = 'Keyword parameters for callproc are not supported on this database backend.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            with connection.cursor() as cursor:
                cursor.callproc('test_procedure', [], {'P_I': 1})
