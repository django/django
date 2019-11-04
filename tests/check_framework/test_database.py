import unittest
from unittest import mock

from django.core.checks import Tags, run_checks
from django.core.checks.registry import CheckRegistry
from django.db import connection
from django.test import TestCase


class DatabaseCheckTests(TestCase):
    databases = {'default', 'other'}

    @property
    def func(self):
        from django.core.checks.database import check_database_backends
        return check_database_backends

    def test_database_checks_not_run_by_default(self):
        """
        `database` checks are only run when their tag is specified.
        """
        def f1(**kwargs):
            return [5]

        registry = CheckRegistry()
        registry.register(Tags.database)(f1)
        errors = registry.run_checks()
        self.assertEqual(errors, [])

        errors2 = registry.run_checks(tags=[Tags.database])
        self.assertEqual(errors2, [5])

    def test_database_checks_called(self):
        with mock.patch('django.db.backends.base.validation.BaseDatabaseValidation.check') as mocked_check:
            run_checks(tags=[Tags.database])
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
            ):
                self.assertEqual(self.func(None), [])

        bad_sql_modes = ['', 'WHATEVER']
        for response in bad_sql_modes:
            with mock.patch(
                'django.db.backends.utils.CursorWrapper.fetchone', create=True,
                return_value=(response,)
            ):
                # One warning for each database alias
                result = self.func(None)
                self.assertEqual(len(result), 2)
                self.assertEqual([r.id for r in result], ['mysql.W002', 'mysql.W002'])
