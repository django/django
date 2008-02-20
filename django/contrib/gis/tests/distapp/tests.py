import os, unittest
from decimal import Decimal

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, Point, LineString
from django.contrib.gis.measure import D # alias for Distance
from django.contrib.gis.db.models import GeoQ
from django.contrib.gis.tests.utils import oracle

from models import SouthTexasCity, AustraliaCity
from data import au_cities, stx_cities

class DistanceTest(unittest.TestCase):

    # A point we are testing distances with -- using a WGS84
    # coordinate that'll be implicitly transormed to that to
    # the coordinate system of the field, EPSG:32140 (Texas South Central
    # w/units in meters)
    stx_pnt = GEOSGeometry('POINT (-95.370401017314293 29.704867409475465)', 4326)
    
    def get_cities(self, qs):
        cities = [c.name for c in qs]
        cities.sort()
        return cities

    def test01_init(self):
        "Initialization of distance models."
        
        def load_cities(city_model, srid, data_tup):
            for name, x, y in data_tup:
                c = city_model(name=name, point=Point(x, y, srid=srid))
                c.save()
        
        load_cities(SouthTexasCity, 32140, stx_cities)
        load_cities(AustraliaCity, 4326, au_cities)

        self.assertEqual(10, SouthTexasCity.objects.count())
        self.assertEqual(11, AustraliaCity.objects.count())

    def test02_dwithin(self):
        "Testing the `dwithin` lookup type."
        pnt = self.stx_pnt
        dists = [7000, D(km=7), D(mi=4.349)]
        for dist in dists:
            qs = SouthTexasCity.objects.filter(point__dwithin=(self.stx_pnt, dist))
            cities = self.get_cities(qs)
            self.assertEqual(cities, ['Downtown Houston', 'Southside Place'])

    def test03_distance_aggregate(self):
        "Testing the `distance` GeoQuerySet method."
        # The point for La Grange, TX
        lagrange = GEOSGeometry('POINT(-96.876369 29.905320)', 4326)
        # Got these from using the raw SQL statement:
        #  SELECT ST_Distance(point, ST_Transform(ST_GeomFromText('POINT(-96.876369 29.905320)', 4326),32140)) FROM distapp_southtexascity;
        distances = [147075.069813, 139630.198056, 140888.552826,
                     138809.684197, 158309.246259, 212183.594374,
                     70870.188967, 165337.758878, 102128.654360, 
                     139196.085105]

        # Testing when the field name is explicitly set.
        dist1 = SouthTexasCity.objects.distance('point', lagrange)
        dist2 = SouthTexasCity.objects.distance(lagrange)  # Using GEOSGeometry parameter
        dist3 = SouthTexasCity.objects.distance(lagrange.ewkt) # Using EWKT string parameter.

        # Original query done on PostGIS, have to adjust AlmostEqual tolerance
        # for Oracle.
        if oracle: tol = 2
        else: tol = 5

        # Ensuring expected distances are returned for each distance queryset.
        for qs in [dist1, dist2, dist3]:
            for i, c in enumerate(qs):
                self.assertAlmostEqual(distances[i], c.distance, tol)

        # Now testing geodetic distance aggregation.
        hillsdale = AustraliaCity.objects.get(name='Hillsdale')
        if not oracle:
            # PostGIS is limited to disance queries only to/from point geometries,
            # ensuring a TypeError is raised if something else is put in.
            self.assertRaises(TypeError, AustraliaCity.objects.distance, 'LINESTRING(0 0, 1 1)')
            self.assertRaises(TypeError, AustraliaCity.objects.distance, LineString((0, 0), (1, 1)))

        # Got these distances using the raw SQL statement:
        #  SELECT ST_distance_spheroid(point, ST_GeomFromText('POINT(151.231341 -33.952685)', 4326), 'SPHEROID["WGS 84",6378137.0,298.257223563]') FROM distapp_australiacity WHERE (NOT (id = 11));
        geodetic_distances = [60504.0628825298, 77023.948962654, 49154.8867507115, 90847.435881812, 217402.811862568, 709599.234619957, 640011.483583758, 7772.00667666425, 1047861.7859506, 1165126.55237647]

        # Ensuring the expected distances are returned.
        qs = AustraliaCity.objects.exclude(id=hillsdale.id).distance(hillsdale.point)
        for i, c in enumerate(qs):
            self.assertAlmostEqual(geodetic_distances[i], c.distance, tol)

    def test04_distance_lookups(self):
        "Testing the `distance_lt`, `distance_gt`, `distance_lte`, and `distance_gte` lookup types."
        # Only two cities (Houston and Southside Place) should be
        # within 7km of the given point.
        dists = [D(km=7), D(mi=4.349), # Distance instances in different units.
                 7000, 7000.0, Decimal(7000), # int, float, Decimal parameters.
                 ]

        for dist in dists:
            qs = SouthTexasCity.objects.filter(point__dwithin=(self.stx_pnt, dist))
            for c in qs:
                cities = self.get_cities(qs)
                self.assertEqual(cities, ['Downtown Houston', 'Southside Place'])

        # Now only retrieving the cities within a 20km 'donut' w/a 7km radius 'hole'
        # (thus, Houston and Southside place will be excluded)
        qs = SouthTexasCity.objects.filter(point__distance_gte=(self.stx_pnt, D(km=7))).filter(point__distance_lte=(self.stx_pnt, D(km=20)))
        cities = self.get_cities(qs)
        self.assertEqual(cities, ['Bellaire', 'Pearland', 'West University Place'])

    def test05_geodetic_distance(self):
        "Testing distance lookups on geodetic coordinate systems."
        
        if not oracle:
            # Oracle doesn't have this limitation -- PostGIS only allows geodetic
            # distance queries from Points to PointFields.
            mp = GEOSGeometry('MULTIPOINT(0 0, 5 23)')
            self.assertRaises(TypeError,
                              AustraliaCity.objects.filter(point__distance_lte=(mp, D(km=100))))
            
        hobart = AustraliaCity.objects.get(name='Hobart')
        
        # Getting all cities w/in 550 miles of Hobart.
        qs = AustraliaCity.objects.exclude(name='Hobart').filter(point__distance_lte=(hobart.point, D(mi=550)))
        cities = self.get_cities(qs)
        self.assertEqual(cities, ['Batemans Bay', 'Canberra', 'Melbourne'])

        # Cities that are either really close or really far from Wollongong --
        # and using different units of distance.
        wollongong = AustraliaCity.objects.get(name='Wollongong')
        gq1 = GeoQ(point__distance_lte=(wollongong.point, D(yd=19500))) # Yards (~17km)
        gq2 = GeoQ(point__distance_gte=(wollongong.point, D(nm=400)))   # Nautical Miles
        qs = AustraliaCity.objects.exclude(name='Wollongong').filter(gq1 | gq2)
        cities = self.get_cities(qs)
        self.assertEqual(cities, ['Adelaide', 'Hobart', 'Shellharbour', 'Thirroul'])


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(DistanceTest))
    return s
