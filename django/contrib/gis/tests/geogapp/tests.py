"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.contrib.gis.measure import D
from django.test import TestCase
from models import City, Zipcode

class GeographyTest(TestCase):

    def test01_fixture_load(self):
        "Ensure geography features loaded properly."
        self.assertEqual(8, City.objects.count())

    def test02_distance_lookup(self):
        "Testing GeoQuerySet distance lookup support on non-point geometry fields."
        z = Zipcode.objects.get(code='77002')
        cities = list(City.objects
                      .filter(point__distance_lte=(z.poly, D(mi=500)))
                      .order_by('name')
                      .values_list('name', flat=True))
        self.assertEqual(['Dallas', 'Houston', 'Oklahoma City'], cities)

    def test03_distance_method(self):
        "Testing GeoQuerySet.distance() support on non-point geometry fields."
        # Can't do this with geometry fields:
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
