import unittest
from unittest import mock

from django.core.checks.database import check_database_backends
from django.db import connection, connections
from django.test import TestCase


class DatabaseCheckTests(TestCase):
    databases = {'default', 'other'}

    @mock.patch('django.db.backends.base.validation.BaseDatabaseValidation.check')
    def test_database_checks_called(self, mocked_check):
        check_database_backends()
        self.assertFalse(mocked_check.called)
        check_database_backends(databases=self.databases)
        self.assertTrue(mocked_check.called)

    @unittest.skipUnless(connection.vendor == 'mysql', 'Test only for MySQL')
    def test_mysql_strict_mode(self):
        def _clean_sql_mode():
            for alias in self.databases:
                if hasattr(connections[alias], 'sql_mode'):
                    del connections[alias].sql_mode

        _clean_sql_mode()
        good_sql_modes = [
            'STRICT_TRANS_TABLES,STRICT_ALL_TABLES',
            'STRICT_TRANS_TABLES',
            'STRICT_ALL_TABLES',
        ]
        for response in good_sql_modes:
            with mock.patch(
                'django.db.backends.utils.CursorWrapper.fetchone', create=True,
                return_value=(response,)
            ):
                self.assertEqual(check_database_backends(databases=self.databases), [])
            _clean_sql_mode()

        bad_sql_modes = ['', 'WHATEVER']
        for response in bad_sql_modes:
            with mock.patch(
                'django.db.backends.utils.CursorWrapper.fetchone', create=True,
                return_value=(response,)
            ):
                # One warning for each database alias
                result = check_database_backends(databases=self.databases)
                self.assertEqual(len(result), 2)
                self.assertEqual([r.id for r in result], ['mysql.W002', 'mysql.W002'])
            _clean_sql_mode()
