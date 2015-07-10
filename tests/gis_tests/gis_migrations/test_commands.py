from __future__ import unicode_literals

from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase, skipUnlessDBFeature


@skipUnlessDBFeature("gis_enabled")
class MigrateTests(TransactionTestCase):
    """
    Tests running the migrate command in Geodjango.
    """
    available_apps = ["gis_tests.gis_migrations"]

    def get_table_description(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_table_description(cursor, table)

    def assertTableExists(self, table):
        with connection.cursor() as cursor:
            self.assertIn(table, connection.introspection.table_names(cursor))

    def assertTableNotExists(self, table):
        with connection.cursor() as cursor:
            self.assertNotIn(table, connection.introspection.table_names(cursor))

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
        # Make sure the right tables exist
        self.assertTableExists("gis_migrations_neighborhood")
        self.assertTableExists("gis_migrations_household")
        self.assertTableExists("gis_migrations_family")
        if connection.features.supports_raster:
            self.assertTableExists("gis_migrations_heatmap")
        # Unmigrate everything
        call_command("migrate", "gis_migrations", "zero", verbosity=0)
        # Make sure it's all gone
        self.assertTableNotExists("gis_migrations_neighborhood")
        self.assertTableNotExists("gis_migrations_household")
        self.assertTableNotExists("gis_migrations_family")
        if connection.features.supports_raster:
            self.assertTableNotExists("gis_migrations_heatmap")
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
        # Revert the "unmigration"
        call_command("migrate", "gis_migrations", verbosity=0)
