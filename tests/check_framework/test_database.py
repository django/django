import unittest

from django.core.checks import Tags, run_checks
from django.core.checks.registry import CheckRegistry
from django.db import connection
from django.test import TestCase, mock


class DatabaseCheckTests(TestCase):
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
