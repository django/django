"""
Tests for geography support in PostGIS 1.5+
"""
from __future__ import absolute_import

import os

from django.contrib.gis.gdal import HAS_GDAL
from django.contrib.gis.geos import HAS_GEOS
from django.contrib.gis.measure import D
from django.contrib.gis.tests.utils import postgis
from django.test import TestCase
from django.utils._os import upath
from django.utils.unittest import skipUnless

if HAS_GEOS:
    from .models import City, County, Zipcode


@skipUnless(HAS_GEOS and postgis, "Geos and postgis are required.")
class GeographyTest(TestCase):

    def test01_fixture_load(self):
        "Ensure geography features loaded properly."
        self.assertEqual(8, City.objects.count())

    def test02_distance_lookup(self):
        "Testing GeoQuerySet distance lookup support on non-point geography fields."
        z = Zipcode.objects.get(code='77002')
        cities1 = list(City.objects
                       .filter(point__distance_lte=(z.poly, D(mi=500)))
                       .order_by('name')
                       .values_list('name', flat=True))
        cities2 = list(City.objects
                       .filter(point__dwithin=(z.poly, D(mi=500)))
                       .order_by('name')
                       .values_list('name', flat=True))
        for cities in [cities1, cities2]:
            self.assertEqual(['Dallas', 'Houston', 'Oklahoma City'], cities)

    def test03_distance_method(self):
        "Testing GeoQuerySet.distance() support on non-point geography fields."
        # `GeoQuerySet.distance` is not allowed geometry fields.
        htown = City.objects.get(name='Houston')
        qs = Zipcode.objects.distance(htown.point)

    def test04_invalid_operators_functions(self):
        "Ensuring exceptions are raised for operators & functions invalid on geography fields."
        # Only a subset of the geometry functions & operator are available
        # to PostGIS geography types.  For more information, visit:
        #  http://postgis.refractions.net/documentation/manual-1.5/ch08.html#PostGIS_GeographyFunctions
        z = Zipcode.objects.get(code='77002')
        # ST_Within not available.
        self.assertRaises(ValueError, City.objects.filter(point__within=z.poly).count)
        # `@` operator not available.
        self.assertRaises(ValueError, City.objects.filter(point__contained=z.poly).count)

        # Regression test for #14060, `~=` was never really implemented for PostGIS.
        htown = City.objects.get(name='Houston')
        self.assertRaises(ValueError, City.objects.get, point__exact=htown.point)

    @skipUnless(HAS_GDAL, "GDAL is required.")
    def test05_geography_layermapping(self):
        "Testing LayerMapping support on models with geography fields."
        # There is a similar test in `layermap` that uses the same data set,
        # but the County model here is a bit different.
        from django.contrib.gis.utils import LayerMapping

        # Getting the shapefile and mapping dictionary.
        shp_path = os.path.realpath(os.path.join(os.path.dirname(upath(__file__)), '..', 'data'))
        co_shp = os.path.join(shp_path, 'counties', 'counties.shp')
        co_mapping = {'name' : 'Name',
                      'state' : 'State',
                      'mpoly' : 'MULTIPOLYGON',
                      }

        # Reference county names, number of polygons, and state names.
        names = ['Bexar', 'Galveston', 'Harris', 'Honolulu', 'Pueblo']
        num_polys = [1, 2, 1, 19, 1] # Number of polygons for each.
        st_names = ['Texas', 'Texas', 'Texas', 'Hawaii', 'Colorado']

        lm = LayerMapping(County, co_shp, co_mapping, source_srs=4269, unique='name')
        lm.save(silent=True, strict=True)

        for c, name, num_poly, state in zip(County.objects.order_by('name'), names, num_polys, st_names):
            self.assertEqual(4326, c.mpoly.srid)
            self.assertEqual(num_poly, len(c.mpoly))
            self.assertEqual(name, c.name)
            self.assertEqual(state, c.state)

    def test06_geography_area(self):
        "Testing that Area calculations work on geography columns."
        # SELECT ST_Area(poly) FROM geogapp_zipcode WHERE code='77002';
        ref_area = 5439084.70637573
        tol = 5
        z = Zipcode.objects.area().get(code='77002')
        self.assertAlmostEqual(z.area.sq_m, ref_area, tol)
