# encoding: utf8
from django.core import checks
from django.core.checks.migrations import check_migrations
from django.test import TestCase, override_settings

from .test_base import MigrationTestBase


class CheckMigrationTests(MigrationTestBase):
    """
    Test checks for unapplied migrations.
    """

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_unapplied(self):
        """
        check_migrations should return a warning when there are unapplied migrations.
        """
        expected = [
            checks.Warning(
                "You have unapplied migrations; "
                "your app may not work properly until they are applied.",
                hint="Run 'python manage.py migrate' to apply them.",
            )
        ]
        errors = check_migrations()
        self.assertEqual(errors, expected)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"}, DATABASES={})
    def test_no_databases(self):
        """
        Migration checks should not consider unapplied migrations if there is
        no database configured.
        """
        errors = check_migrations()
        self.assertEqual(errors, [])

    def test_no_unapplied(self):
        """
        No warning should be issued if all migrations have been applied.
        """
        errors = check_migrations()
        self.assertEqual(errors, [])
