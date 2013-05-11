from __future__ import absolute_import

import os

from django.db import connections
from django.test import TestCase
from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.geometry.test_data import TEST_DATA
from django.contrib.gis.tests.utils import HAS_SPATIAL_DB
from django.utils.unittest import skipUnless

if HAS_GDAL:
    from django.contrib.gis.gdal import Driver
    from django.contrib.gis.utils.ogrinspect import ogrinspect

    from .models import AllOGRFields


@skipUnless(HAS_GDAL and HAS_SPATIAL_DB, "GDAL and spatial db are required.")
class OGRInspectTest(TestCase):
    maxDiff = 1024

    def test_poly(self):
        shp_file = os.path.join(TEST_DATA, 'test_poly', 'test_poly.shp')
        model_def = ogrinspect(shp_file, 'MyModel')

        expected = [
            '# This is an auto-generated Django model module created by ogrinspect.',
            'from django.contrib.gis.db import models',
            '',
            'class MyModel(models.Model):',
            '    float = models.FloatField()',
            '    int = models.FloatField()',
            '    str = models.CharField(max_length=80)',
            '    geom = models.PolygonField(srid=-1)',
            '    objects = models.GeoManager()',
        ]

        self.assertEqual(model_def, '\n'.join(expected))

    def test_date_field(self):
        shp_file = os.path.join(TEST_DATA, 'cities', 'cities.shp')
        model_def = ogrinspect(shp_file, 'City')

        expected = [
            '# This is an auto-generated Django model module created by ogrinspect.',
            'from django.contrib.gis.db import models',
            '',
            'class City(models.Model):',
            '    name = models.CharField(max_length=80)',
            '    population = models.FloatField()',
            '    density = models.FloatField()',
            '    created = models.DateField()',
            '    geom = models.PointField(srid=-1)',
            '    objects = models.GeoManager()',
        ]

        self.assertEqual(model_def, '\n'.join(expected))

    def test_time_field(self):
        # Only possible to test this on PostGIS at the momemnt.  MySQL
        # complains about permissions, and SpatiaLite/Oracle are
        # insanely difficult to get support compiled in for in GDAL.
        if not connections['default'].ops.postgis:
            self.skipTest("This database does not support 'ogrinspect'ion")

        # Getting the database identifier used by OGR, if None returned
        # GDAL does not have the support compiled in.
        ogr_db = get_ogr_db_string()
        if not ogr_db:
            self.skipTest("Your GDAL installation does not support PostGIS databases")

        # Writing shapefiles via GDAL currently does not support writing OGRTime
        # fields, so we need to actually use a database
        model_def = ogrinspect(ogr_db, 'Measurement',
                               layer_key=AllOGRFields._meta.db_table,
                               decimal=['f_decimal'])

        self.assertTrue(model_def.startswith(
            '# This is an auto-generated Django model module created by ogrinspect.\n'
            'from django.contrib.gis.db import models\n'
            '\n'
            'class Measurement(models.Model):\n'
        ))

        # The ordering of model fields might vary depending on several factors (version of GDAL, etc.)
        self.assertIn('    f_decimal = models.DecimalField(max_digits=0, decimal_places=0)', model_def)
        self.assertIn('    f_int = models.IntegerField()', model_def)
        self.assertIn('    f_datetime = models.DateTimeField()', model_def)
        self.assertIn('    f_time = models.TimeField()', model_def)
        self.assertIn('    f_float = models.FloatField()', model_def)
        self.assertIn('    f_char = models.CharField(max_length=10)', model_def)
        self.assertIn('    f_date = models.DateField()', model_def)

        self.assertTrue(model_def.endswith(
            '    geom = models.PolygonField()\n'
            '    objects = models.GeoManager()'
        ))


def get_ogr_db_string():
    """
    Construct the DB string that GDAL will use to inspect the database.
    GDAL will create its own connection to the database, so we re-use the
    connection settings from the Django test.
    """
    db = connections.databases['default']

    # Map from the django backend into the OGR driver name and database identifier
    # http://www.gdal.org/ogr/ogr_formats.html
    #
    # TODO: Support Oracle (OCI).
    drivers = {
        'django.contrib.gis.db.backends.postgis': ('PostgreSQL', "PG:dbname='%(db_name)s'", ' '),
        'django.contrib.gis.db.backends.mysql': ('MySQL', 'MYSQL:"%(db_name)s"', ','),
        'django.contrib.gis.db.backends.spatialite': ('SQLite', '%(db_name)s', '')
    }

    drv_name, db_str, param_sep = drivers[db['ENGINE']]

    # Ensure that GDAL library has driver support for the database.
    try:
        Driver(drv_name)
    except:
        return None

    # SQLite/Spatialite in-memory databases
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
