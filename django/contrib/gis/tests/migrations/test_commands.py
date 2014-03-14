# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management import call_command
from django.test import override_settings, override_system_checks

from .test_base import MigrationTestBase


class MigrateTests(MigrationTestBase):
    """
    Tests running the migrate command in Geodjango.
    """

    # `auth` app is imported, but not installed in these tests (thanks to
    # MigrationTestBase), so we need to exclude checks registered by this app.

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"gis": "django.contrib.gis.tests.migrations.migrations"})
    def test_migrate_gis(self):
        """
        Tests basic usage of the migrate command when a model uses Geodjango
        fields. Regression test for ticket #22001:
        https://code.djangoproject.com/ticket/22001
        """
        # Make sure no tables are created
        self.assertTableNotExists("migrations_neighborhood")
        self.assertTableNotExists("migrations_household")
        # Run the migrations to 0001 only
        call_command("migrate", "gis", "0001", verbosity=0)
        # Make sure the right tables exist
        self.assertTableExists("gis_neighborhood")
        self.assertTableExists("gis_household")
        # Unmigrate everything
        call_command("migrate", "gis", "zero", verbosity=0)
        # Make sure it's all gone
        self.assertTableNotExists("gis_neighborhood")
        self.assertTableNotExists("gis_household")
