import unittest

from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase, override_settings


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL specific tests")
class TestMigrations(TransactionTestCase):
    available_apps = ["postgres_tests"]

    @override_settings(
        MIGRATION_MODULES={
            "postgres_tests": "postgres_tests.unmanaged_migrations",
        }
    )
    def test_adding_field_with_default(self):
        call_command("migrate", "postgres_tests", verbosity=0)
