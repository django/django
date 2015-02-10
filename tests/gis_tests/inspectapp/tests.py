from __future__ import unicode_literals

import os
import re
from unittest import skipUnless

from django.contrib.gis.gdal import HAS_GDAL
from django.core.management import call_command
from django.db import connection, connections
from django.test import TestCase, skipUnlessDBFeature
from django.utils.six import StringIO

from ..test_data import TEST_DATA

if HAS_GDAL:
    from django.contrib.gis.gdal import Driver, GDALException
    from django.contrib.gis.utils.ogrinspect import ogrinspect

    from .models import AllOGRFields


@skipUnless(HAS_GDAL, "InspectDbTests needs GDAL support")
@skipUnlessDBFeature("gis_enabled")
class InspectDbTests(TestCase):
    def test_geom_columns(self):
        """
        Test the geo-enabled inspectdb command.
        """
        out = StringIO()
        call_command('inspectdb',
                 table_name_filter=lambda tn: tn.startswith('inspectapp_'),
                 stdout=out)
        output = out.getvalue()
        if connection.features.supports_geometry_field_introspection:
            self.assertIn('geom = models.PolygonField()', output)
            self.assertIn('point = models.PointField()', output)
        else:
            self.assertIn('geom = models.GeometryField(', output)
            self.assertIn('point = models.GeometryField(', output)
        self.assertIn('objects = models.GeoManager()', output)


@skipUnless(HAS_GDAL, "OGRInspectTest needs GDAL support")
@skipUnlessDBFeature("gis_enabled")
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

        self.assertIsNotNone(re.search(
            r'    geom = models.PolygonField\(([^\)])*\)\n'  # Some backends may have srid=-1
            r'    objects = models.GeoManager\(\)', model_def))

    def test_management_command(self):
        shp_file = os.path.join(TEST_DATA, 'cities', 'cities.shp')
        out = StringIO()
        call_command('ogrinspect', shp_file, 'City', stdout=out)
        output = out.getvalue()
        self.assertIn('class City(models.Model):', output)


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

    db_engine = db['ENGINE']
    if db_engine not in drivers:
        return None

    drv_name, db_str, param_sep = drivers[db_engine]

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
