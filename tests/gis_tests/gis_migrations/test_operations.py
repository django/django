from __future__ import unicode_literals

from django.contrib.gis.db.models import fields
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, migrations, models
from django.db.migrations.migration import Migration
from django.db.migrations.state import ProjectState
from django.test import (
    TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)

from ..utils import mysql

if connection.features.gis_enabled:
    try:
        GeometryColumns = connection.ops.geometry_columns()
        HAS_GEOMETRY_COLUMNS = True
    except NotImplementedError:
        HAS_GEOMETRY_COLUMNS = False


@skipUnlessDBFeature('gis_enabled')
class OperationTests(TransactionTestCase):
    available_apps = ['gis_tests.gis_migrations']

    def tearDown(self):
        # Delete table after testing
        if hasattr(self, 'current_state'):
            self.apply_operations('gis', self.current_state, [migrations.DeleteModel('Neighborhood')])
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

    def set_up_test_model(self, force_raster_creation=False):
        test_fields = [
            ('id', models.AutoField(primary_key=True)),
            ('name', models.CharField(max_length=100, unique=True)),
            ('geom', fields.MultiPolygonField(srid=4326))
        ]
        if connection.features.supports_raster or force_raster_creation:
            test_fields += [('rast', fields.RasterField(srid=4326))]
        operations = [migrations.CreateModel('Neighborhood', test_fields)]
        return self.apply_operations('gis', ProjectState(), operations)

    def assertGeometryColumnsCount(self, expected_count):
        table_name = 'gis_neighborhood'
        if connection.features.uppercases_column_names:
            table_name = table_name.upper()
        self.assertEqual(
            GeometryColumns.objects.filter(**{
                GeometryColumns.table_name_col(): table_name,
            }).count(),
            expected_count
        )

    def assertSpatialIndexExists(self, table, column):
        with connection.cursor() as cursor:
            indexes = connection.introspection.get_indexes(cursor, table)
        self.assertIn(column, indexes)

    def alter_gis_model(self, migration_class, model_name, field_name,
            blank=False, field_class=None):
        project_state = self.set_up_test_model()
        self.current_state = project_state
        args = [model_name, field_name]
        if field_class:
            args.append(field_class(srid=4326, blank=blank))
        operation = migration_class(*args)
        new_state = project_state.clone()
        operation.state_forwards('gis', new_state)
        with connection.schema_editor() as editor:
            operation.database_forwards('gis', editor, project_state, new_state)
        self.current_state = new_state

    def test_add_geom_field(self):
        """
        Test the AddField operation with a geometry-enabled column.
        """
        self.alter_gis_model(migrations.AddField, 'Neighborhood',
            'path', False, fields.LineStringField)
        self.assertColumnExists('gis_neighborhood', 'path')

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertGeometryColumnsCount(2)

        # Test spatial indices when available
        if self.has_spatial_indexes:
            self.assertSpatialIndexExists('gis_neighborhood', 'path')

    @skipUnlessDBFeature('supports_raster')
    def test_add_raster_field(self):
        """
        Test the AddField operation with a raster-enabled column.
        """
        self.alter_gis_model(migrations.AddField, 'Neighborhood',
            'heatmap', False, fields.RasterField)
        self.assertColumnExists('gis_neighborhood', 'heatmap')

        # Test spatial indices when available
        if self.has_spatial_indexes:
            self.assertSpatialIndexExists('gis_neighborhood', 'heatmap')

    @skipIfDBFeature('supports_raster')
    def test_create_raster_model_on_db_without_raster_support(self):
        """
        Test creating a model with a raster field on a db without raster support.
        """
        msg = 'Raster fields require backends with raster support.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.set_up_test_model(True)

    @skipIfDBFeature('supports_raster')
    def test_add_raster_field_on_db_without_raster_support(self):
        """
        Test adding a raster field on a db without raster support.
        """
        msg = 'Raster fields require backends with raster support.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.alter_gis_model(
                migrations.AddField, 'Neighborhood', 'heatmap',
                False, fields.RasterField
            )

    def test_add_blank_geom_field(self):
        """
        Should be able to add a GeometryField with blank=True.
        """
        self.alter_gis_model(migrations.AddField, 'Neighborhood',
            'path', True, fields.LineStringField)
        self.assertColumnExists('gis_neighborhood', 'path')

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertGeometryColumnsCount(2)

        # Test spatial indices when available
        if self.has_spatial_indexes:
            self.assertSpatialIndexExists('gis_neighborhood', 'path')

    @skipUnlessDBFeature('supports_raster')
    def test_add_blank_raster_field(self):
        """
        Should be able to add a RasterField with blank=True.
        """
        self.alter_gis_model(migrations.AddField, 'Neighborhood',
            'heatmap', True, fields.RasterField)
        self.assertColumnExists('gis_neighborhood', 'heatmap')

        # Test spatial indices when available
        if self.has_spatial_indexes:
            self.assertSpatialIndexExists('gis_neighborhood', 'heatmap')

    def test_remove_geom_field(self):
        """
        Test the RemoveField operation with a geometry-enabled column.
        """
        self.alter_gis_model(migrations.RemoveField, 'Neighborhood', 'geom')
        self.assertColumnNotExists('gis_neighborhood', 'geom')

        # Test GeometryColumns when available
        if HAS_GEOMETRY_COLUMNS:
            self.assertGeometryColumnsCount(0)

    @skipUnlessDBFeature('supports_raster')
    def test_remove_raster_field(self):
        """
        Test the RemoveField operation with a raster-enabled column.
        """
        self.alter_gis_model(migrations.RemoveField, 'Neighborhood', 'rast')
        self.assertColumnNotExists('gis_neighborhood', 'rast')

    def test_create_model_spatial_index(self):
        self.current_state = self.set_up_test_model()

        if not self.has_spatial_indexes:
            self.skipTest('No support for Spatial indexes')

        self.assertSpatialIndexExists('gis_neighborhood', 'geom')

        if connection.features.supports_raster:
            self.assertSpatialIndexExists('gis_neighborhood', 'rast')

    @property
    def has_spatial_indexes(self):
        if mysql:
            with connection.cursor() as cursor:
                return connection.introspection.supports_spatial_index(cursor, 'gis_neighborhood')
        return True
