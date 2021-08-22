import os
import re
from io import StringIO

from django.contrib.gis.gdal import GDAL_VERSION, Driver, GDALException
from django.contrib.gis.utils.ogrinspect import ogrinspect
from django.core.management import call_command
from django.db import connection, connections
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import modify_settings

from ..test_data import TEST_DATA
from .models import AllOGRFields


class InspectDbTests(TestCase):
    def test_geom_columns(self):
        """
        Test the geo-enabled inspectdb command.
        """
        out = StringIO()
        call_command(
            'inspectdb',
            table_name_filter=lambda tn: tn == 'inspectapp_allogrfields',
            stdout=out
        )
        output = out.getvalue()
        if connection.features.supports_geometry_field_introspection:
            self.assertIn('geom = models.PolygonField()', output)
            self.assertIn('point = models.PointField()', output)
        else:
            self.assertIn('geom = models.GeometryField(', output)
            self.assertIn('point = models.GeometryField(', output)

    @skipUnlessDBFeature("supports_3d_storage")
    def test_3d_columns(self):
        out = StringIO()
        call_command(
            'inspectdb',
            table_name_filter=lambda tn: tn == 'inspectapp_fields3d',
            stdout=out
        )
        output = out.getvalue()
        if connection.features.supports_geometry_field_introspection:
            self.assertIn('point = models.PointField(dim=3)', output)
            if connection.features.supports_geography:
                self.assertIn('pointg = models.PointField(geography=True, dim=3)', output)
            else:
                self.assertIn('pointg = models.PointField(dim=3)', output)
            self.assertIn('line = models.LineStringField(dim=3)', output)
            self.assertIn('poly = models.PolygonField(dim=3)', output)
        else:
            self.assertIn('point = models.GeometryField(', output)
            self.assertIn('pointg = models.GeometryField(', output)
            self.assertIn('line = models.GeometryField(', output)
            self.assertIn('poly = models.GeometryField(', output)


@modify_settings(
    INSTALLED_APPS={'append': 'django.contrib.gis'},
)
class OGRInspectTest(SimpleTestCase):
    expected_srid = 'srid=-1' if GDAL_VERSION < (2, 2) else ''
    maxDiff = 1024

    def test_poly(self):
        shp_file = os.path.join(TEST_DATA, 'test_poly', 'test_poly.shp')
        model_def = ogrinspect(shp_file, 'MyModel')

        expected = [
            '# This is an auto-generated Django model module created by ogrinspect.',
            'from django.contrib.gis.db import models',
            '',
            '',
            'class MyModel(models.Model):',
            '    float = models.FloatField()',
            '    int = models.BigIntegerField()',
            '    str = models.CharField(max_length=80)',
            '    geom = models.PolygonField(%s)' % self.expected_srid,
        ]

        self.assertEqual(model_def, '\n'.join(expected))

    def test_poly_multi(self):
        shp_file = os.path.join(TEST_DATA, 'test_poly', 'test_poly.shp')
        model_def = ogrinspect(shp_file, 'MyModel', multi_geom=True)
        self.assertIn('geom = models.MultiPolygonField(%s)' % self.expected_srid, model_def)
        # Same test with a 25D-type geometry field
        shp_file = os.path.join(TEST_DATA, 'gas_lines', 'gas_leitung.shp')
        model_def = ogrinspect(shp_file, 'MyModel', multi_geom=True)
        srid = '-1' if GDAL_VERSION < (2, 3) else '31253'
        self.assertIn('geom = models.MultiLineStringField(srid=%s)' % srid, model_def)

    def test_date_field(self):
        shp_file = os.path.join(TEST_DATA, 'cities', 'cities.shp')
        model_def = ogrinspect(shp_file, 'City')

        expected = [
            '# This is an auto-generated Django model module created by ogrinspect.',
            'from django.contrib.gis.db import models',
            '',
            '',
            'class City(models.Model):',
            '    name = models.CharField(max_length=80)',
            '    population = models.BigIntegerField()',
            '    density = models.FloatField()',
            '    created = models.DateField()',
            '    geom = models.PointField(%s)' % self.expected_srid,
        ]

        self.assertEqual(model_def, '\n'.join(expected))

    def test_time_field(self):
        # Getting the database identifier used by OGR, if None returned
        # GDAL does not have the support compiled in.
        ogr_db = get_ogr_db_string()
        if not ogr_db:
            self.skipTest("Unable to setup an OGR connection to your database")

        try:
            # Writing shapefiles via GDAL currently does not support writing OGRTime
            # fields, so we need to actually use a database
            model_def = ogrinspect(ogr_db, 'Measurement',
                                   layer_key=AllOGRFields._meta.db_table,
                                   decimal=['f_decimal'])
        except GDALException:
            self.skipTest("Unable to setup an OGR connection to your database")

        self.assertTrue(model_def.startswith(
            '# This is an auto-generated Django model module created by ogrinspect.\n'
            'from django.contrib.gis.db import models\n'
            '\n'
            '\n'
            'class Measurement(models.Model):\n'
        ))

        # The ordering of model fields might vary depending on several factors (version of GDAL, etc.)
        if connection.vendor == 'sqlite':
            # SpatiaLite introspection is somewhat lacking (#29461).
            self.assertIn('    f_decimal = models.CharField(max_length=0)', model_def)
        else:
            self.assertIn('    f_decimal = models.DecimalField(max_digits=0, decimal_places=0)', model_def)
        self.assertIn('    f_int = models.IntegerField()', model_def)
        if not connection.ops.mariadb:
            # Probably a bug between GDAL and MariaDB on time fields.
            self.assertIn('    f_datetime = models.DateTimeField()', model_def)
            self.assertIn('    f_time = models.TimeField()', model_def)
        if connection.vendor == 'sqlite':
            self.assertIn('    f_float = models.CharField(max_length=0)', model_def)
        else:
            self.assertIn('    f_float = models.FloatField()', model_def)
        max_length = 0 if connection.vendor == 'sqlite' else 10
        self.assertIn('    f_char = models.CharField(max_length=%s)' % max_length, model_def)
        self.assertIn('    f_date = models.DateField()', model_def)

        # Some backends may have srid=-1
        self.assertIsNotNone(re.search(r'    geom = models.PolygonField\(([^\)])*\)', model_def))

    def test_management_command(self):
        shp_file = os.path.join(TEST_DATA, 'cities', 'cities.shp')
        out = StringIO()
        call_command('ogrinspect', shp_file, 'City', stdout=out)
        output = out.getvalue()
        self.assertIn('class City(models.Model):', output)

    def test_mapping_option(self):
        expected = (
            "    geom = models.PointField(%s)\n"
            "\n"
            "\n"
            "# Auto-generated `LayerMapping` dictionary for City model\n"
            "city_mapping = {\n"
            "    'name': 'Name',\n"
            "    'population': 'Population',\n"
            "    'density': 'Density',\n"
            "    'created': 'Created',\n"
            "    'geom': 'POINT',\n"
            "}\n" % self.expected_srid)
        shp_file = os.path.join(TEST_DATA, 'cities', 'cities.shp')
        out = StringIO()
        call_command('ogrinspect', shp_file, '--mapping', 'City', stdout=out)
        self.assertIn(expected, out.getvalue())


def get_ogr_db_string():
    """
    Construct the DB string that GDAL will use to inspect the database.
    GDAL will create its own connection to the database, so we re-use the
    connection settings from the Django test.
    """
    db = connections.databases['default']

    # Map from the django backend into the OGR driver name and database identifier
    # https://gdal.org/drivers/vector/
    #
    # TODO: Support Oracle (OCI).
    drivers = {
        'django.contrib.gis.db.backends.postgis': ('PostgreSQL', "PG:dbname='%(db_name)s'", ' '),
        'django.contrib.gis.db.backends.mysql': ('MySQL', 'MYSQL:"%(db_name)s"', ','),
        'django.contrib.gis.db.backends.spatialite': ('SQLite', '%(db_name)s', '')
    }

    db_engine = db['ENGINE']
    if db_engine not in drivers:
        return None

    drv_name, db_str, param_sep = drivers[db_engine]

    # Ensure that GDAL library has driver support for the database.
    try:
        Driver(drv_name)
    except GDALException:
        return None

    # SQLite/SpatiaLite in-memory databases
    if db['NAME'] == ":memory:":
        return None

    # Build the params of the OGR database connection string
    params = [db_str % {'db_name': db['NAME']}]

    def add(key, template):
        value = db.get(key, None)
        # Don't add the parameter if it is not in django's settings
        if value:
            params.append(template % value)
    add('HOST', "host='%s'")
    add('PORT', "port='%s'")
    add('USER', "user='%s'")
    add('PASSWORD', "password='%s'")

    return param_sep.join(params)
