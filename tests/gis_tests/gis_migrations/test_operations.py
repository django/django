from unittest import skipIf

from django.contrib.gis.db.models import fields
from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.exceptions import ImproperlyConfigured
from django.db import connection, migrations, models
from django.db.migrations.migration import Migration
from django.db.migrations.state import ProjectState
from django.test import (
    TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature,
)

from ..utils import mysql, spatialite

if connection.features.gis_enabled:
    try:
        GeometryColumns = connection.ops.geometry_columns()
        HAS_GEOMETRY_COLUMNS = True
    except NotImplementedError:
        HAS_GEOMETRY_COLUMNS = False


@skipUnlessDBFeature('gis_enabled')
class OperationTestCase(TransactionTestCase):
    available_apps = ['gis_tests.gis_migrations']

    def tearDown(self):
        # Delete table after testing
        if hasattr(self, 'current_state'):
            self.apply_operations('gis', self.current_state, [migrations.DeleteModel('Neighborhood')])
        super(OperationTestCase, self).tearDown()

    @property
    def has_spatial_indexes(self):
        if mysql:
            with connection.cursor() as cursor:
                return connection.introspection.supports_spatial_index(cursor, 'gis_neighborhood')
        return True

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
            test_fields += [('rast', fields.RasterField(srid=4326, null=True))]
        operations = [migrations.CreateModel('Neighborhood', test_fields)]
        self.current_state = self.apply_operations('gis', ProjectState(), operations)

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

    def assertSpatialIndexExists(self, table, column, raster=False):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, table)
        if raster:
            self.assertTrue(any(
                'st_convexhull(%s)' % column in c['definition']
                for c in constraints.values()
                if c['definition'] is not None
            ))
        else:
            self.assertIn([column], [c['columns'] for c in constraints.values()])

    def alter_gis_model(self, migration_class, model_name, field_name,
                        blank=False, field_class=None, field_class_kwargs=None):
        args = [model_name, field_name]
        if field_class:
            field_class_kwargs = field_class_kwargs or {'srid': 4326, 'blank': blank}
            args.append(field_class(**field_class_kwargs))
        operation = migration_class(*args)
        old_state = self.current_state.clone()
        operation.state_forwards('gis', self.current_state)
        with connection.schema_editor() as editor:
            operation.database_forwards('gis', editor, old_state, self.current_state)


class OperationTests(OperationTestCase):

    def setUp(self):
        super(OperationTests, self).setUp()
        self.set_up_test_model()

    def test_add_geom_field(self):
        """
        Test the AddField operation with a geometry-enabled column.
        """
        self.alter_gis_model(migrations.AddField, 'Neighborhood', 'path', False, fields.LineStringField)
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
        self.alter_gis_model(migrations.AddField, 'Neighborhood', 'heatmap', False, fields.RasterField)
        self.assertColumnExists('gis_neighborhood', 'heatmap')

        # Test spatial indices when available
        if self.has_spatial_indexes:
            self.assertSpatialIndexExists('gis_neighborhood', 'heatmap', raster=True)

    def test_add_blank_geom_field(self):
        """
        Should be able to add a GeometryField with blank=True.
        """
        self.alter_gis_model(migrations.AddField, 'Neighborhood', 'path', True, fields.LineStringField)
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
        self.alter_gis_model(migrations.AddField, 'Neighborhood', 'heatmap', True, fields.RasterField)
        self.assertColumnExists('gis_neighborhood', 'heatmap')

        # Test spatial indices when available
        if self.has_spatial_indexes:
            self.assertSpatialIndexExists('gis_neighborhood', 'heatmap', raster=True)

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
        if not self.has_spatial_indexes:
            self.skipTest('No support for Spatial indexes')

        self.assertSpatialIndexExists('gis_neighborhood', 'geom')

        if connection.features.supports_raster:
            self.assertSpatialIndexExists('gis_neighborhood', 'rast', raster=True)

    @skipUnlessDBFeature("supports_3d_storage")
    @skipIf(spatialite, "Django currently doesn't support altering Spatialite geometry fields")
    def test_alter_geom_field_dim(self):
        Neighborhood = self.current_state.apps.get_model('gis', 'Neighborhood')
        p1 = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        Neighborhood.objects.create(name='TestDim', geom=MultiPolygon(p1, p1))
        # Add 3rd dimension.
        self.alter_gis_model(
            migrations.AlterField, 'Neighborhood', 'geom', False,
            fields.MultiPolygonField, field_class_kwargs={'srid': 4326, 'dim': 3}
        )
        self.assertTrue(Neighborhood.objects.first().geom.hasz)
        # Rewind to 2 dimensions.
        self.alter_gis_model(
            migrations.AlterField, 'Neighborhood', 'geom', False,
            fields.MultiPolygonField, field_class_kwargs={'srid': 4326, 'dim': 2}
        )
        self.assertFalse(Neighborhood.objects.first().geom.hasz)


@skipIfDBFeature('supports_raster')
class NoRasterSupportTests(OperationTestCase):
    def test_create_raster_model_on_db_without_raster_support(self):
        msg = 'Raster fields require backends with raster support.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.set_up_test_model(force_raster_creation=True)

    def test_add_raster_field_on_db_without_raster_support(self):
        msg = 'Raster fields require backends with raster support.'
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            self.set_up_test_model()
            self.alter_gis_model(
                migrations.AddField, 'Neighborhood', 'heatmap',
                False, fields.RasterField
            )
