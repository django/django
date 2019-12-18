import unittest
from unittest import mock

from django.core.checks import Tags, run_checks
from django.core.checks.database import check_database_backends
from django.db import connection
from django.test import TestCase


class DatabaseCheckTests(TestCase):
    databases = {'default', 'other'}

    def test_database_checks_called(self):
        with mock.patch('django.db.backends.base.validation.BaseDatabaseValidation.check') as mocked_check:
            run_checks(tags=[Tags.database], databases=self.databases)
            self.assertTrue(mocked_check.called)

    @unittest.skipUnless(connection.vendor == 'mysql', 'Test only for MySQL')
    def test_mysql_strict_mode(self):
        good_sql_modes = [
            'STRICT_TRANS_TABLES,STRICT_ALL_TABLES',
            'STRICT_TRANS_TABLES',
            'STRICT_ALL_TABLES',
        ]
        for response in good_sql_modes:
            with mock.patch(
                'django.db.backends.utils.CursorWrapper.fetchone', create=True,
                return_value=(response,)
            ), self.subTest(sql_mode=response):
                self.assertEqual(check_database_backends(databases=self.databases), [])

        bad_sql_modes = ['', 'WHATEVER']
        for response in bad_sql_modes:
            with mock.patch(
                'django.db.backends.utils.CursorWrapper.fetchone', create=True,
                return_value=(response,)
            ), self.subTest(sql_mode=response):
                # One warning for each database alias
                result = check_database_backends(databases=self.databases)
                self.assertEqual(len(result), 2)
                self.assertEqual([r.id for r in result], ['mysql.W002', 'mysql.W002'])
