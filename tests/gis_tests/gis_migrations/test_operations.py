from __future__ import unicode_literals

from django.db import connection, migrations, models
from django.db.migrations.migration import Migration
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase, skipUnlessDBFeature

from ..utils import mysql

if connection.features.gis_enabled:
    from django.contrib.gis.db.models import fields
    try:
        GeometryColumns = connection.ops.geometry_columns()
        HAS_GEOMETRY_COLUMNS = True
    except NotImplementedError:
        HAS_GEOMETRY_COLUMNS = False


@skipUnlessDBFeature("gis_enabled")
class OperationTests(TransactionTestCase):
    available_apps = ["gis_tests.gis_migrations"]

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
                ('geom', fields.MultiPolygonField(srid=4326)),
            ],
        )]
        return self.apply_operations('gis', ProjectState(), operations)

    def assertGeometryColumnsCount(self, expected_count):
        table_name = "gis_neighborhood"
        if connection.features.uppercases_column_names:
            table_name = table_name.upper()
        self.assertEqual(
            GeometryColumns.objects.filter(**{
                GeometryColumns.table_name_col(): table_name,
            }).count(),
            expected_count
        )

    def test_add_gis_field(self):
        """
        Tests the AddField operation with a GIS-enabled column.
        """
        project_state = self.set_up_test_model()
        self.current_state = project_state
        operation = migrations.AddField(
            "Neighborhood",
            "path",
            fields.LineStringField(srid=4326),
        )
        new_state = project_state.clone()
        operation.state_forwards("gis", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("gis", editor, project_state, new_state)
        self.current_state = new_state
        self.assertColumnExists("gis_neighborhood", "path")

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertGeometryColumnsCount(2)

        if self.has_spatial_indexes:
            with connection.cursor() as cursor:
                indexes = connection.introspection.get_indexes(cursor, "gis_neighborhood")
            self.assertIn('path', indexes)

    def test_add_blank_gis_field(self):
        """
        Should be able to add a GeometryField with blank=True.
        """
        project_state = self.set_up_test_model()
        self.current_state = project_state
        operation = migrations.AddField(
            "Neighborhood",
            "path",
            fields.LineStringField(blank=True, srid=4326),
        )
        new_state = project_state.clone()
        operation.state_forwards("gis", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("gis", editor, project_state, new_state)
        self.current_state = new_state
        self.assertColumnExists("gis_neighborhood", "path")

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertGeometryColumnsCount(2)

        if self.has_spatial_indexes:
            with connection.cursor() as cursor:
                indexes = connection.introspection.get_indexes(cursor, "gis_neighborhood")
            self.assertIn('path', indexes)

    def test_remove_gis_field(self):
        """
        Tests the RemoveField operation with a GIS-enabled column.
        """
        project_state = self.set_up_test_model()
        self.current_state = project_state
        operation = migrations.RemoveField("Neighborhood", "geom")
        new_state = project_state.clone()
        operation.state_forwards("gis", new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards("gis", editor, project_state, new_state)
        self.current_state = new_state
        self.assertColumnNotExists("gis_neighborhood", "geom")

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertGeometryColumnsCount(0)

    def test_create_model_spatial_index(self):
        self.current_state = self.set_up_test_model()

        if not self.has_spatial_indexes:
            self.skipTest("No support for Spatial indexes")

        with connection.cursor() as cursor:
            indexes = connection.introspection.get_indexes(cursor, "gis_neighborhood")
        self.assertIn('geom', indexes)

    @property
    def has_spatial_indexes(self):
        if mysql:
            with connection.cursor() as cursor:
                return connection.introspection.supports_spatial_index(cursor, "gis_neighborhood")
        return True
