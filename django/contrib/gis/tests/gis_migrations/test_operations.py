from __future__ import unicode_literals

from unittest import skipUnless

from django.contrib.gis.tests.utils import HAS_SPATIAL_DB
from django.db import connection, migrations, models
from django.db.migrations.migration import Migration
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase

if HAS_SPATIAL_DB:
    from django.contrib.gis.db.models import fields
    try:
        from django.contrib.gis.models import GeometryColumns
        HAS_GEOMETRY_COLUMNS = True
    except ImportError:
        HAS_GEOMETRY_COLUMNS = False


@skipUnless(HAS_SPATIAL_DB, "Spatial db is required.")
class OperationTests(TransactionTestCase):
    available_apps = ["django.contrib.gis.tests.gis_migrations"]

    def tearDown(self):
        # Delete table after testing
        self.apply_operations('gis', self.current_state, [migrations.DeleteModel("Neighborhood")])
        super(OperationTests, self).tearDown()

    def get_table_description(self, table):
        with connection.cursor() as cursor:
            return connection.introspection.get_table_description(cursor, table)

    def assertColumnExists(self, table, column):
        self.assertIn(column, [c.name for c in self.get_table_description(table)])

    def assertColumnNotExists(self, table, column):
        self.assertNotIn(column, [c.name for c in self.get_table_description(table)])

    def apply_operations(self, app_label, project_state, operations):
        migration = Migration('name', app_label)
        migration.operations = operations
        with connection.schema_editor() as editor:
            return migration.apply(project_state, editor)

    def set_up_test_model(self):
        operations = [migrations.CreateModel(
            "Neighborhood",
            [
                ("id", models.AutoField(primary_key=True)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('geom', fields.MultiPolygonField(srid=4326, null=True)),
            ],
        )]
        return self.apply_operations('gis', ProjectState(), operations)

    def test_add_gis_field(self):
        """
        Tests the AddField operation with a GIS-enabled column.
        """
        project_state = self.set_up_test_model()
        operation = migrations.AddField(
            "Neighborhood",
            "path",
            fields.LineStringField(srid=4326, null=True, blank=True),
        )
        new_state = project_state.clone()
        operation.state_forwards("gis", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("gis", editor, project_state, new_state)
        self.assertColumnExists("gis_neighborhood", "path")

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertEqual(
                GeometryColumns.objects.filter(**{GeometryColumns.table_name_col(): "gis_neighborhood"}).count(),
                2
            )
        self.current_state = new_state

    def test_remove_gis_field(self):
        """
        Tests the RemoveField operation with a GIS-enabled column.
        """
        project_state = self.set_up_test_model()
        operation = migrations.RemoveField("Neighborhood", "geom")
        new_state = project_state.clone()
        operation.state_forwards("gis", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("gis", editor, project_state, new_state)
        self.assertColumnNotExists("gis_neighborhood", "geom")

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertEqual(
                GeometryColumns.objects.filter(**{GeometryColumns.table_name_col(): "gis_neighborhood"}).count(),
                0
            )
        self.current_state = new_state
