import os, unittest
from decimal import Decimal
from models import *
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.measure import D # alias for Distance
from django.contrib.gis.tests.utils import oracle

shp_path = os.path.dirname(__file__)
city_shp = os.path.join(shp_path, 'cities/cities.shp')
#county_shp = os.path.join(shp_path, 'counties/counties.shp')

class DistanceTest(unittest.TestCase):

    def test01_init(self):
        "LayerMapping initialization of distance models."
        
        city_lm = LayerMapping(City, city_shp, city_mapping, transform=False)
        city_lm.save()

        # TODO: complete tests with distance from multipolygons.
        #county_lm = LayerMapping(County, county_shp, county_mapping, transform=False)
        #county_lm.save()
        
        self.assertEqual(12, City.objects.count())
        #self.assertEqual(60, County.objects.count())

    # TODO: Complete tests for `dwithin` lookups.
    #def test02_dwithin(self):
    #    "Testing the `dwithin` lookup type."
    #    pass

    def test03_distance_aggregate(self):
        "Testing the `distance` GeoQuerySet method."
        # The point for La Grange, TX
        lagrange = GEOSGeometry('POINT(-96.876369 29.905320)', 4326)
        # Got these from using the raw SQL statement:
        #  SELECT ST_Distance(point, ST_Transform(ST_GeomFromText('POINT(-96.876369 29.905320)', 4326),32140)) FROM distapp_city;
        distances = [147075.069813436, 139630.198056286, 140888.552826286,
                     138809.684197415, 158309.246259353, 212183.594374882,
                     70870.1889675217, 319225.965633536, 165337.758878256,
                     92630.7446925393, 102128.654360872, 139196.085105372]
        dist1 = City.objects.distance('point', lagrange)
        dist2 = City.objects.distance(lagrange)

        # Original query done on PostGIS, have to adjust AlmostEqual tolerance
        # for Oracle.
        if oracle: tol = 3
        else: tol = 7

        for qs in [dist1, dist2]:
            for i, c in enumerate(qs):
                self.assertAlmostEqual(distances[i], c.distance, tol)

    def test04_distance_lookups(self):
        "Testing the `distance_lt`, `distance_gt`, `distance_lte`, and `distance_gte` lookup types."
        # The point we are testing distances with -- using a WGS84
        # coordinate that'll be implicitly transormed to that to
        # the coordinate system of the field, EPSG:32140 (Texas South Central
        # w/units in meters)
        pnt = GEOSGeometry('POINT (-95.370401017314293 29.704867409475465)', 4326)

        # Only two cities (Houston and Southside Place) should be
        # within 7km of the given point.
        qs1 = City.objects.filter(point__distance_lte=(pnt, D(km=7))) # Query w/Distance instance.
        qs2 = City.objects.filter(point__distance_lte=(pnt, 7000)) # Query w/int (units are assumed to be that of the field)
        qs3 = City.objects.filter(point__distance_lte=(pnt, 7000.0)) # Query w/float
        qs4 = City.objects.filter(point__distance_lte=(pnt, Decimal(7000))) # Query w/Decimal

        for qs in [qs1, qs2, qs3, qs4]:
            for c in qs:
                self.assertEqual(2, qs.count())
                self.failIf(not c.name in ['Downtown Houston', 'Southside Place'])

        # Now only retrieving the cities within a 20km 'donut' w/a 7km radius 'hole'
        # (thus, Houston and Southside place will be excluded)
        qs = City.objects.filter(point__distance_gte=(pnt, D(km=7))).filter(point__distance_lte=(pnt, D(km=20)))
        self.assertEqual(3, qs.count())
        for c in qs:
            self.failIf(not c.name in ['Pearland', 'Bellaire', 'West University Place'])

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(DistanceTest))
    return s
