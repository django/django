from __future__ import unicode_literals

from unittest import skipUnless

from django.db import connection
from django.db.models import Q
from django.contrib.gis.geos import HAS_GEOS
from django.contrib.gis.measure import D  # alias for Distance
from django.contrib.gis.tests.utils import (
    HAS_SPATIAL_DB, mysql, oracle, postgis, spatialite, no_oracle, no_spatialite
)
from django.test import TestCase

if HAS_GEOS and HAS_SPATIAL_DB:
    from django.contrib.gis.geos import GEOSGeometry, LineString

    from .models import (AustraliaCity, Interstate, SouthTexasInterstate,
        SouthTexasCity, SouthTexasCityFt, CensusZipcode, SouthTexasZipcode)


@skipUnless(HAS_GEOS and HAS_SPATIAL_DB and not mysql,
    "Geos and spatial db (not mysql) are required.")
class DistanceTest(TestCase):

    if HAS_GEOS and HAS_SPATIAL_DB:
        # A point we are testing distances with -- using a WGS84
        # coordinate that'll be implicitly transformed to that to
        # the coordinate system of the field, EPSG:32140 (Texas South Central
        # w/units in meters)
        stx_pnt = GEOSGeometry('POINT (-95.370401017314293 29.704867409475465)', 4326)
        # Another one for Australia
        au_pnt = GEOSGeometry('POINT (150.791 -34.4919)', 4326)

    def get_names(self, qs):
        cities = [c.name for c in qs]
        cities.sort()
        return cities

    def test_init(self):
        """
        Test initialization of distance models.
        """
        self.assertEqual(9, SouthTexasCity.objects.count())
        self.assertEqual(9, SouthTexasCityFt.objects.count())
        self.assertEqual(11, AustraliaCity.objects.count())
        self.assertEqual(4, SouthTexasZipcode.objects.count())
        self.assertEqual(4, CensusZipcode.objects.count())
        self.assertEqual(1, Interstate.objects.count())
        self.assertEqual(1, SouthTexasInterstate.objects.count())

    @no_spatialite
    def test_dwithin(self):
        """
        Test the `dwithin` lookup type.
        """
        # Distances -- all should be equal (except for the
        # degree/meter pair in au_cities, that's somewhat
        # approximate).
        tx_dists = [(7000, 22965.83), D(km=7), D(mi=4.349)]
        au_dists = [(0.5, 32000), D(km=32), D(mi=19.884)]

        # Expected cities for Australia and Texas.
        tx_cities = ['Downtown Houston', 'Southside Place']
        au_cities = ['Mittagong', 'Shellharbour', 'Thirroul', 'Wollongong']

        # Performing distance queries on two projected coordinate systems one
        # with units in meters and the other in units of U.S. survey feet.
        for dist in tx_dists:
            if isinstance(dist, tuple):
                dist1, dist2 = dist
            else:
                dist1 = dist2 = dist
            qs1 = SouthTexasCity.objects.filter(point__dwithin=(self.stx_pnt, dist1))
            qs2 = SouthTexasCityFt.objects.filter(point__dwithin=(self.stx_pnt, dist2))
            for qs in qs1, qs2:
                self.assertEqual(tx_cities, self.get_names(qs))

        # Now performing the `dwithin` queries on a geodetic coordinate system.
        for dist in au_dists:
            if isinstance(dist, D) and not oracle:
                type_error = True
            else:
                type_error = False

            if isinstance(dist, tuple):
                if oracle:
                    dist = dist[1]
                else:
                    dist = dist[0]

            # Creating the query set.
            qs = AustraliaCity.objects.order_by('name')
            if type_error:
                # A ValueError should be raised on PostGIS when trying to pass
                # Distance objects into a DWithin query using a geodetic field.
                self.assertRaises(ValueError, AustraliaCity.objects.filter(point__dwithin=(self.au_pnt, dist)).count)
            else:
                self.assertListEqual(au_cities, self.get_names(qs.filter(point__dwithin=(self.au_pnt, dist))))

    def test_distance_projected(self):
        """
        Test the `distance` GeoQuerySet method on projected coordinate systems.
        """
        # The point for La Grange, TX
        lagrange = GEOSGeometry('POINT(-96.876369 29.905320)', 4326)
        # Reference distances in feet and in meters. Got these values from
        # using the provided raw SQL statements.
        #  SELECT ST_Distance(point, ST_Transform(ST_GeomFromText('POINT(-96.876369 29.905320)', 4326), 32140)) FROM distapp_southtexascity;
        m_distances = [147075.069813, 139630.198056, 140888.552826,
                       138809.684197, 158309.246259, 212183.594374,
                       70870.188967, 165337.758878, 139196.085105]
        #  SELECT ST_Distance(point, ST_Transform(ST_GeomFromText('POINT(-96.876369 29.905320)', 4326), 2278)) FROM distapp_southtexascityft;
        # Oracle 11 thinks this is not a projected coordinate system, so it's
        # not tested.
        ft_distances = [482528.79154625, 458103.408123001, 462231.860397575,
                        455411.438904354, 519386.252102563, 696139.009211594,
                        232513.278304279, 542445.630586414, 456679.155883207]

        # Testing using different variations of parameters and using models
        # with different projected coordinate systems.
        dist1 = SouthTexasCity.objects.distance(lagrange, field_name='point')
        dist2 = SouthTexasCity.objects.distance(lagrange)  # Using GEOSGeometry parameter
        if spatialite or oracle:
            dist_qs = [dist1, dist2]
        else:
            dist3 = SouthTexasCityFt.objects.distance(lagrange.ewkt)  # Using EWKT string parameter.
            dist4 = SouthTexasCityFt.objects.distance(lagrange)
            dist_qs = [dist1, dist2, dist3, dist4]

        # Original query done on PostGIS, have to adjust AlmostEqual tolerance
        # for Oracle.
        tol = 2 if oracle else 5

        # Ensuring expected distances are returned for each distance queryset.
        for qs in dist_qs:
            for i, c in enumerate(qs):
                self.assertAlmostEqual(m_distances[i], c.distance.m, tol)
                self.assertAlmostEqual(ft_distances[i], c.distance.survey_ft, tol)

    @no_spatialite
    def test_distance_geodetic(self):
        """
        Test the `distance` GeoQuerySet method on geodetic coordinate systems.
        """
        tol = 2 if oracle else 5

        # Testing geodetic distance calculation with a non-point geometry
        # (a LineString of Wollongong and Shellharbour coords).
        ls = LineString(((150.902, -34.4245), (150.87, -34.5789)))
        if oracle or connection.ops.geography:
            # Reference query:
            #  SELECT ST_distance_sphere(point, ST_GeomFromText('LINESTRING(150.9020 -34.4245,150.8700 -34.5789)', 4326)) FROM distapp_australiacity ORDER BY name;
            distances = [1120954.92533513, 140575.720018241, 640396.662906304,
                         60580.9693849269, 972807.955955075, 568451.8357838,
                         40435.4335201384, 0, 68272.3896586844, 12375.0643697706, 0]
            qs = AustraliaCity.objects.distance(ls).order_by('name')
            for city, distance in zip(qs, distances):
                # Testing equivalence to within a meter.
                self.assertAlmostEqual(distance, city.distance.m, 0)
        else:
            # PostGIS 1.4 and below is limited to disance queries only
            # to/from point geometries, check for raising of ValueError.
            self.assertRaises(ValueError, AustraliaCity.objects.distance, ls)
            self.assertRaises(ValueError, AustraliaCity.objects.distance, ls.wkt)

        # Got the reference distances using the raw SQL statements:
        #  SELECT ST_distance_spheroid(point, ST_GeomFromText('POINT(151.231341 -33.952685)', 4326), 'SPHEROID["WGS 84",6378137.0,298.257223563]') FROM distapp_australiacity WHERE (NOT (id = 11));
        #  SELECT ST_distance_sphere(point, ST_GeomFromText('POINT(151.231341 -33.952685)', 4326)) FROM distapp_australiacity WHERE (NOT (id = 11));  st_distance_sphere
        if connection.ops.postgis and connection.ops.proj_version_tuple() >= (4, 7, 0):
            # PROJ.4 versions 4.7+ have updated datums, and thus different
            # distance values.
            spheroid_distances = [60504.0628957201, 77023.9489850262, 49154.8867574404,
                                  90847.4358768573, 217402.811919332, 709599.234564757,
                                  640011.483550888, 7772.00667991925, 1047861.78619339,
                                  1165126.55236034]
            sphere_distances = [60580.9693849267, 77144.0435286473, 49199.4415344719,
                                90804.7533823494, 217713.384600405, 709134.127242793,
                                639828.157159169, 7786.82949717788, 1049204.06569028,
                                1162623.7238134]

        else:
            spheroid_distances = [60504.0628825298, 77023.948962654, 49154.8867507115,
                                  90847.435881812, 217402.811862568, 709599.234619957,
                                  640011.483583758, 7772.00667666425, 1047861.7859506,
                                  1165126.55237647]
            sphere_distances = [60580.7612632291, 77143.7785056615, 49199.2725132184,
                                90804.4414289463, 217712.63666124, 709131.691061906,
                                639825.959074112, 7786.80274606706, 1049200.46122281,
                                1162619.7297006]

        # Testing with spheroid distances first.
        hillsdale = AustraliaCity.objects.get(name='Hillsdale')
        qs = AustraliaCity.objects.exclude(id=hillsdale.id).distance(hillsdale.point, spheroid=True)
        for i, c in enumerate(qs):
            self.assertAlmostEqual(spheroid_distances[i], c.distance.m, tol)
        if postgis:
            # PostGIS uses sphere-only distances by default, testing these as well.
            qs = AustraliaCity.objects.exclude(id=hillsdale.id).distance(hillsdale.point)
            for i, c in enumerate(qs):
                self.assertAlmostEqual(sphere_distances[i], c.distance.m, tol)

    @no_oracle  # Oracle already handles geographic distance calculation.
    def test_distance_transform(self):
        """
        Test the `distance` GeoQuerySet method used with `transform` on a geographic field.
        """
        # Normally you can't compute distances from a geometry field
        # that is not a PointField (on PostGIS 1.4 and below).
        if not connection.ops.geography:
            self.assertRaises(ValueError, CensusZipcode.objects.distance, self.stx_pnt)

        # We'll be using a Polygon (created by buffering the centroid
        # of 77005 to 100m) -- which aren't allowed in geographic distance
        # queries normally, however our field has been transformed to
        # a non-geographic system.
        z = SouthTexasZipcode.objects.get(name='77005')

        # Reference query:
        # SELECT ST_Distance(ST_Transform("distapp_censuszipcode"."poly", 32140), ST_GeomFromText('<buffer_wkt>', 32140)) FROM "distapp_censuszipcode";
        dists_m = [3553.30384972258, 1243.18391525602, 2186.15439472242]

        # Having our buffer in the SRID of the transformation and of the field
        # -- should get the same results. The first buffer has no need for
        # transformation SQL because it is the same SRID as what was given
        # to `transform()`.  The second buffer will need to be transformed,
        # however.
        buf1 = z.poly.centroid.buffer(100)
        buf2 = buf1.transform(4269, clone=True)
        ref_zips = ['77002', '77025', '77401']

        for buf in [buf1, buf2]:
            qs = CensusZipcode.objects.exclude(name='77005').transform(32140).distance(buf)
            self.assertListEqual(ref_zips, self.get_names(qs))
            for i, z in enumerate(qs):
                self.assertAlmostEqual(z.distance.m, dists_m[i], 5)

    def test_distance_lookups(self):
        """
        Test the `distance_lt`, `distance_gt`, `distance_lte`, and `distance_gte` lookup types.
        """
        # Retrieving the cities within a 20km 'donut' w/a 7km radius 'hole'
        # (thus, Houston and Southside place will be excluded as tested in
        # the `test02_dwithin` above).
        qs1 = SouthTexasCity.objects.filter(point__distance_gte=(self.stx_pnt, D(km=7))).filter(point__distance_lte=(self.stx_pnt, D(km=20)))

        # Can't determine the units on SpatiaLite from PROJ.4 string, and
        # Oracle 11 incorrectly thinks it is not projected.
        if spatialite or oracle:
            dist_qs = (qs1,)
        else:
            qs2 = SouthTexasCityFt.objects.filter(point__distance_gte=(self.stx_pnt, D(km=7))).filter(point__distance_lte=(self.stx_pnt, D(km=20)))
            dist_qs = (qs1, qs2)

        for qs in dist_qs:
            cities = self.get_names(qs)
            self.assertEqual(cities, ['Bellaire', 'Pearland', 'West University Place'])

        # Doing a distance query using Polygons instead of a Point.
        z = SouthTexasZipcode.objects.get(name='77005')
        qs = SouthTexasZipcode.objects.exclude(name='77005').filter(poly__distance_lte=(z.poly, D(m=275)))
        self.assertEqual(['77025', '77401'], self.get_names(qs))
        # If we add a little more distance 77002 should be included.
        qs = SouthTexasZipcode.objects.exclude(name='77005').filter(poly__distance_lte=(z.poly, D(m=300)))
        self.assertEqual(['77002', '77025', '77401'], self.get_names(qs))

    def test_geodetic_distance_lookups(self):
        """
        Test distance lookups on geodetic coordinate systems.
        """
        # Line is from Canberra to Sydney.  Query is for all other cities within
        # a 100km of that line (which should exclude only Hobart & Adelaide).
        line = GEOSGeometry('LINESTRING(144.9630 -37.8143,151.2607 -33.8870)', 4326)
        dist_qs = AustraliaCity.objects.filter(point__distance_lte=(line, D(km=100)))

        if oracle or connection.ops.geography:
            # Oracle and PostGIS 1.5 can do distance lookups on arbitrary geometries.
            self.assertEqual(9, dist_qs.count())
            self.assertEqual(['Batemans Bay', 'Canberra', 'Hillsdale',
                              'Melbourne', 'Mittagong', 'Shellharbour',
                              'Sydney', 'Thirroul', 'Wollongong'],
                             self.get_names(dist_qs))
        else:
            # PostGIS 1.4 and below only allows geodetic distance queries (utilizing
            # ST_Distance_Sphere/ST_Distance_Spheroid) from Points to PointFields
            # on geometry columns.
            self.assertRaises(ValueError, dist_qs.count)

            # Ensured that a ValueError was raised, none of the rest of the test is
            # support on this backend, so bail now.
            if spatialite:
                return

        # Too many params (4 in this case) should raise a ValueError.
        self.assertRaises(ValueError, len,
                          AustraliaCity.objects.filter(point__distance_lte=('POINT(5 23)', D(km=100), 'spheroid', '4')))

        # Not enough params should raise a ValueError.
        self.assertRaises(ValueError, len,
                          AustraliaCity.objects.filter(point__distance_lte=('POINT(5 23)',)))

        # Getting all cities w/in 550 miles of Hobart.
        hobart = AustraliaCity.objects.get(name='Hobart')
        qs = AustraliaCity.objects.exclude(name='Hobart').filter(point__distance_lte=(hobart.point, D(mi=550)))
        cities = self.get_names(qs)
        self.assertEqual(cities, ['Batemans Bay', 'Canberra', 'Melbourne'])

        # Cities that are either really close or really far from Wollongong --
        # and using different units of distance.
        wollongong = AustraliaCity.objects.get(name='Wollongong')
        d1, d2 = D(yd=19500), D(nm=400)  # Yards (~17km) & Nautical miles.

        # Normal geodetic distance lookup (uses `distance_sphere` on PostGIS.
        gq1 = Q(point__distance_lte=(wollongong.point, d1))
        gq2 = Q(point__distance_gte=(wollongong.point, d2))
        qs1 = AustraliaCity.objects.exclude(name='Wollongong').filter(gq1 | gq2)

        # Geodetic distance lookup but telling GeoDjango to use `distance_spheroid`
        # instead (we should get the same results b/c accuracy variance won't matter
        # in this test case).
        if postgis:
            gq3 = Q(point__distance_lte=(wollongong.point, d1, 'spheroid'))
            gq4 = Q(point__distance_gte=(wollongong.point, d2, 'spheroid'))
            qs2 = AustraliaCity.objects.exclude(name='Wollongong').filter(gq3 | gq4)
            querysets = [qs1, qs2]
        else:
            querysets = [qs1]

        for qs in querysets:
            cities = self.get_names(qs)
            self.assertEqual(cities, ['Adelaide', 'Hobart', 'Shellharbour', 'Thirroul'])

    def test_area(self):
        """
        Test the `area` GeoQuerySet method.
        """
        # Reference queries:
        # SELECT ST_Area(poly) FROM distapp_southtexaszipcode;
        area_sq_m = [5437908.90234375, 10183031.4389648, 11254471.0073242, 9881708.91772461]
        # Tolerance has to be lower for Oracle and differences
        # with GEOS 3.0.0RC4
        tol = 2
        for i, z in enumerate(SouthTexasZipcode.objects.area()):
            self.assertAlmostEqual(area_sq_m[i], z.area.sq_m, tol)

    def test_length(self):
        """
        Test the `length` GeoQuerySet method.
        """
        # Reference query (should use `length_spheroid`).
        # SELECT ST_length_spheroid(ST_GeomFromText('<wkt>', 4326) 'SPHEROID["WGS 84",6378137,298.257223563, AUTHORITY["EPSG","7030"]]');
        len_m1 = 473504.769553813
        len_m2 = 4617.668

        if spatialite:
            # Does not support geodetic coordinate systems.
            self.assertRaises(ValueError, Interstate.objects.length)
        else:
            qs = Interstate.objects.length()
            tol = 2 if oracle else 3
            self.assertAlmostEqual(len_m1, qs[0].length.m, tol)

        # Now doing length on a projected coordinate system.
        i10 = SouthTexasInterstate.objects.length().get(name='I-10')
        self.assertAlmostEqual(len_m2, i10.length.m, 2)

    @no_spatialite
    def test_perimeter(self):
        """
        Test the `perimeter` GeoQuerySet method.
        """
        # Reference query:
        # SELECT ST_Perimeter(distapp_southtexaszipcode.poly) FROM distapp_southtexaszipcode;
        perim_m = [18404.3550889361, 15627.2108551001, 20632.5588368978, 17094.5996143697]
        tol = 2 if oracle else 7
        for i, z in enumerate(SouthTexasZipcode.objects.perimeter()):
            self.assertAlmostEqual(perim_m[i], z.perimeter.m, tol)

        # Running on points; should return 0.
        for i, c in enumerate(SouthTexasCity.objects.perimeter(model_att='perim')):
            self.assertEqual(0, c.perim.m)

    def test_measurement_null_fields(self):
        """
        Test the measurement GeoQuerySet methods on fields with NULL values.
        """
        # Creating SouthTexasZipcode w/NULL value.
        SouthTexasZipcode.objects.create(name='78212')
        # Performing distance/area queries against the NULL PolygonField,
        # and ensuring the result of the operations is None.
        htown = SouthTexasCity.objects.get(name='Downtown Houston')
        z = SouthTexasZipcode.objects.distance(htown.point).area().get(name='78212')
        self.assertIsNone(z.distance)
        self.assertIsNone(z.area)
