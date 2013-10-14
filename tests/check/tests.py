from django.core.checks.compatibility import base
from django.core.checks.compatibility import django_1_6_0
from django.core.management.commands import check
from django.core.management import call_command
from django.db.models.fields import NOT_PROVIDED
from django.test import TestCase

from .models import Book

class StubCheckModule(object):
    # Has no ``run_checks`` attribute & will trigger a warning.
    __name__ = 'StubCheckModule'


class FakeWarnings(object):
    def __init__(self):
        self._warnings = []

    def warn(self, message):
        self._warnings.append(message)


class CompatChecksTestCase(TestCase):
    def setUp(self):
        super(CompatChecksTestCase, self).setUp()

        # We're going to override the list of checks to perform for test
        # consistency in the future.
        self.old_compat_checks = base.COMPAT_CHECKS
        base.COMPAT_CHECKS = [
            django_1_6_0,
        ]

    def tearDown(self):
        # Restore what's supposed to be in ``COMPAT_CHECKS``.
        base.COMPAT_CHECKS = self.old_compat_checks
        super(CompatChecksTestCase, self).tearDown()

    def test_check_test_runner_new_default(self):
        with self.settings(TEST_RUNNER='django.test.runner.DiscoverRunner'):
            result = django_1_6_0.check_test_runner()
            self.assertTrue("Django 1.6 introduced a new default test runner" in result)

    def test_check_test_runner_overridden(self):
        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            self.assertEqual(django_1_6_0.check_test_runner(), None)

    def test_run_checks_new_default(self):
        with self.settings(TEST_RUNNER='django.test.runner.DiscoverRunner'):
            result = django_1_6_0.run_checks()
            self.assertEqual(len(result), 1)
            self.assertTrue("Django 1.6 introduced a new default test runner" in result[0])

    def test_run_checks_overridden(self):
        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            self.assertEqual(len(django_1_6_0.run_checks()), 0)

    def test_boolean_field_default_value(self):
        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            # We patch the field's default value to trigger the warning
            boolean_field = Book._meta.get_field('is_published')
            old_default = boolean_field.default
            try:
                boolean_field.default = NOT_PROVIDED
                result = django_1_6_0.run_checks()
                self.assertEqual(len(result), 1)
                self.assertTrue("You have not set a default value for one or more BooleanFields" in result[0])
                self.assertTrue('check.Book: "is_published"' in result[0])
                # We did not patch the BlogPost.is_published field so
                # there should not be a warning about it
                self.assertFalse('check.BlogPost' in result[0])
            finally:
                # Restore the ``default``
                boolean_field.default = old_default

    def test_check_compatibility(self):
        with self.settings(TEST_RUNNER='django.test.runner.DiscoverRunner'):
            result = base.check_compatibility()
            self.assertEqual(len(result), 1)
            self.assertTrue("Django 1.6 introduced a new default test runner" in result[0])

        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            self.assertEqual(len(base.check_compatibility()), 0)

    def test_check_compatibility_warning(self):
        # First, we're patching over the ``COMPAT_CHECKS`` with a stub which
        # will trigger the warning.
        base.COMPAT_CHECKS = [
            StubCheckModule(),
        ]

        # Next, we unfortunately have to patch out ``warnings``.
        old_warnings = base.warnings
        base.warnings = FakeWarnings()

        self.assertEqual(len(base.warnings._warnings), 0)

        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            self.assertEqual(len(base.check_compatibility()), 0)

        self.assertEqual(len(base.warnings._warnings), 1)
        self.assertTrue("The 'StubCheckModule' module lacks a 'run_checks'" in base.warnings._warnings[0])

        # Restore the ``warnings``.
        base.warnings = old_warnings

    def test_management_command(self):
        # Again, we unfortunately have to patch out ``warnings``. Different
        old_warnings = check.warnings
        check.warnings = FakeWarnings()

        self.assertEqual(len(check.warnings._warnings), 0)

        # Should not produce any warnings.
        with self.settings(TEST_RUNNER='myapp.test.CustomRunnner'):
            call_command('check')

        self.assertEqual(len(check.warnings._warnings), 0)

        with self.settings(TEST_RUNNER='django.test.runner.DiscoverRunner'):
            call_command('check')

        self.assertEqual(len(check.warnings._warnings), 1)
        self.assertTrue("Django 1.6 introduced a new default test runner" in check.warnings._warnings[0])

        # Restore the ``warnings``.
        base.warnings = old_warnings
