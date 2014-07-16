from __future__ import unicode_literals

from unittest import skipUnless

from django.contrib.gis.tests.utils import HAS_SPATIAL_DB
from django.core.management import call_command
from django.db import connection
from django.test import override_settings, override_system_checks, TransactionTestCase


class MigrateTests(TransactionTestCase):
    """
    Tests running the migrate command in Geodjango.
    """
    available_apps = ["django.contrib.gis"]

    def get_table_description(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_table_description(cursor, table)

    def assertTableExists(self, table):
        with connection.cursor() as cursor:
            self.assertIn(table, connection.introspection.get_table_list(cursor))

    def assertTableNotExists(self, table):
        with connection.cursor() as cursor:
            self.assertNotIn(table, connection.introspection.get_table_list(cursor))

    @skipUnless(HAS_SPATIAL_DB, "Spatial db is required.")
    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"gis": "django.contrib.gis.tests.gis_migrations.migrations"})
    def test_migrate_gis(self):
        """
        Tests basic usage of the migrate command when a model uses Geodjango
        fields. Regression test for ticket #22001:
        https://code.djangoproject.com/ticket/22001

        It's also used to showcase an error in migrations where spatialite is
        enabled and geo tables are renamed resulting in unique constraint
        failure on geometry_columns. Regression for ticket #23030:
        https://code.djangoproject.com/ticket/23030
        """
        # Make sure no tables are created
        self.assertTableNotExists("migrations_neighborhood")
        self.assertTableNotExists("migrations_household")
        self.assertTableNotExists("migrations_family")
        # Run the migrations to 0001 only
        call_command("migrate", "gis", "0001", verbosity=0)
        # Make sure the right tables exist
        self.assertTableExists("gis_neighborhood")
        self.assertTableExists("gis_household")
        self.assertTableExists("gis_family")
        # Unmigrate everything
        call_command("migrate", "gis", "zero", verbosity=0)
        # Make sure it's all gone
        self.assertTableNotExists("gis_neighborhood")
        self.assertTableNotExists("gis_household")
        self.assertTableNotExists("gis_family")
        # Even geometry columns metadata
        try:
            GeoColumn = connection.ops.geometry_columns()
        except NotImplementedError:
            # Not all GIS backends have geometry columns model
            pass
        else:
            self.assertEqual(
                GeoColumn.objects.filter(
                    **{'%s__in' % GeoColumn.table_name_col(): ["gis_neighborhood", "gis_household"]}
                    ).count(),
                0)
