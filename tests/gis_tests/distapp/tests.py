from django.contrib.gis.db.models.functions import (
    Area,
    Distance,
    Length,
    Perimeter,
    Transform,
    Union,
)
from django.contrib.gis.geos import GEOSGeometry, LineString, Point
from django.contrib.gis.measure import D  # alias for Distance
from django.db import NotSupportedError, connection
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Q,
    Value,
    When,
)
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from ..utils import FuncTestMixin
from .models import (
    AustraliaCity,
    CensusZipcode,
    Interstate,
    SouthTexasCity,
    SouthTexasCityFt,
    SouthTexasInterstate,
    SouthTexasZipcode,
)


class DistanceTest(TestCase):
    fixtures = ["initial"]

    def setUp(self):
        # A point we are testing distances with -- using a WGS84
        # coordinate that'll be implicitly transformed to that to
        # the coordinate system of the field, EPSG:32140 (Texas South Central
        # w/units in meters)
        self.stx_pnt = GEOSGeometry(
            "POINT (-95.370401017314293 29.704867409475465)", 4326
        )
        # Another one for Australia
        self.au_pnt = GEOSGeometry("POINT (150.791 -34.4919)", 4326)

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

    @skipUnlessDBFeature("supports_dwithin_lookup")
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
        tx_cities = ["Downtown Houston", "Southside Place"]
        au_cities = ["Mittagong", "Shellharbour", "Thirroul", "Wollongong"]

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
                with self.subTest(dist=dist, qs=qs):
                    self.assertEqual(tx_cities, self.get_names(qs))

        # With a complex geometry expression
        self.assertFalse(
            SouthTexasCity.objects.exclude(point__dwithin=(Union("point", "point"), 0))
        )

        # Now performing the `dwithin` queries on a geodetic coordinate system.
        for dist in au_dists:
            with self.subTest(dist=dist):
                type_error = isinstance(dist, D) and not connection.ops.oracle
                if isinstance(dist, tuple):
                    if connection.ops.oracle or connection.ops.spatialite:
                        # Result in meters
                        dist = dist[1]
                    else:
                        # Result in units of the field
                        dist = dist[0]

                # Creating the query set.
                qs = AustraliaCity.objects.order_by("name")
                if type_error:
                    # A ValueError should be raised on PostGIS when trying to
                    # pass Distance objects into a DWithin query using a
                    # geodetic field.
                    with self.assertRaises(ValueError):
                        AustraliaCity.objects.filter(
                            point__dwithin=(self.au_pnt, dist)
                        ).count()
                else:
                    self.assertEqual(
                        au_cities,
                        self.get_names(qs.filter(point__dwithin=(self.au_pnt, dist))),
                    )

    @skipUnlessDBFeature("supports_distances_lookups")
    def test_distance_lookups(self):
        # Retrieving the cities within a 20km 'donut' w/a 7km radius 'hole'
        # (thus, Houston and Southside place will be excluded as tested in
        # the `test02_dwithin` above).
        for model in [SouthTexasCity, SouthTexasCityFt]:
            stx_pnt = self.stx_pnt.transform(
                model._meta.get_field("point").srid, clone=True
            )
            qs = model.objects.filter(point__distance_gte=(stx_pnt, D(km=7))).filter(
                point__distance_lte=(stx_pnt, D(km=20)),
            )
            cities = self.get_names(qs)
            self.assertEqual(cities, ["Bellaire", "Pearland", "West University Place"])

        # Doing a distance query using Polygons instead of a Point.
        z = SouthTexasZipcode.objects.get(name="77005")
        qs = SouthTexasZipcode.objects.exclude(name="77005").filter(
            poly__distance_lte=(z.poly, D(m=275))
        )
        self.assertEqual(["77025", "77401"], self.get_names(qs))
        # If we add a little more distance 77002 should be included.
        qs = SouthTexasZipcode.objects.exclude(name="77005").filter(
            poly__distance_lte=(z.poly, D(m=300))
        )
        self.assertEqual(["77002", "77025", "77401"], self.get_names(qs))

    @skipUnlessDBFeature("supports_distances_lookups", "supports_distance_geodetic")
    def test_geodetic_distance_lookups(self):
        """
        Test distance lookups on geodetic coordinate systems.
        """
        # Line is from Canberra to Sydney. Query is for all other cities within
        # a 100km of that line (which should exclude only Hobart & # Adelaide).
        line = GEOSGeometry("LINESTRING(144.9630 -37.8143,151.2607 -33.8870)", 4326)
        dist_qs = AustraliaCity.objects.filter(point__distance_lte=(line, D(km=100)))
        expected_cities = [
            "Batemans Bay",
            "Canberra",
            "Hillsdale",
            "Melbourne",
            "Mittagong",
            "Shellharbour",
            "Sydney",
            "Thirroul",
            "Wollongong",
        ]
        if connection.ops.spatialite:
            # SpatiaLite is less accurate and returns 102.8km for Batemans Bay.
            expected_cities.pop(0)
        self.assertEqual(expected_cities, self.get_names(dist_qs))

        msg = "2, 3, or 4-element tuple required for 'distance_lte' lookup."
        with self.assertRaisesMessage(ValueError, msg):  # Too many params.
            len(
                AustraliaCity.objects.filter(
                    point__distance_lte=(
                        "POINT(5 23)",
                        D(km=100),
                        "spheroid",
                        "4",
                        None,
                    )
                )
            )

        with self.assertRaisesMessage(ValueError, msg):  # Too few params.
            len(AustraliaCity.objects.filter(point__distance_lte=("POINT(5 23)",)))

        msg = "For 4-element tuples the last argument must be the 'spheroid' directive."
        with self.assertRaisesMessage(ValueError, msg):
            len(
                AustraliaCity.objects.filter(
                    point__distance_lte=("POINT(5 23)", D(km=100), "spheroid", "4")
                )
            )

        # Getting all cities w/in 550 miles of Hobart.
        hobart = AustraliaCity.objects.get(name="Hobart")
        qs = AustraliaCity.objects.exclude(name="Hobart").filter(
            point__distance_lte=(hobart.point, D(mi=550))
        )
        cities = self.get_names(qs)
        self.assertEqual(cities, ["Batemans Bay", "Canberra", "Melbourne"])

        # Cities that are either really close or really far from Wollongong --
        # and using different units of distance.
        wollongong = AustraliaCity.objects.get(name="Wollongong")
        d1, d2 = D(yd=19500), D(nm=400)  # Yards (~17km) & Nautical miles.

        # Normal geodetic distance lookup (uses `distance_sphere` on PostGIS.
        gq1 = Q(point__distance_lte=(wollongong.point, d1))
        gq2 = Q(point__distance_gte=(wollongong.point, d2))
        qs1 = AustraliaCity.objects.exclude(name="Wollongong").filter(gq1 | gq2)

        # Geodetic distance lookup but telling GeoDjango to use
        # `distance_spheroid` instead (we should get the same results b/c
        # accuracy variance won't matter in this test case).
        querysets = [qs1]
        if connection.features.has_DistanceSpheroid_function:
            gq3 = Q(point__distance_lte=(wollongong.point, d1, "spheroid"))
            gq4 = Q(point__distance_gte=(wollongong.point, d2, "spheroid"))
            qs2 = AustraliaCity.objects.exclude(name="Wollongong").filter(gq3 | gq4)
            querysets.append(qs2)

        for qs in querysets:
            cities = self.get_names(qs)
            self.assertEqual(cities, ["Adelaide", "Hobart", "Shellharbour", "Thirroul"])

    @skipUnlessDBFeature("supports_distances_lookups")
    def test_distance_lookups_with_expression_rhs(self):
        stx_pnt = self.stx_pnt.transform(
            SouthTexasCity._meta.get_field("point").srid, clone=True
        )
        qs = SouthTexasCity.objects.filter(
            point__distance_lte=(stx_pnt, F("radius")),
        ).order_by("name")
        self.assertEqual(
            self.get_names(qs),
            [
                "Bellaire",
                "Downtown Houston",
                "Southside Place",
                "West University Place",
            ],
        )

        # With a combined expression
        qs = SouthTexasCity.objects.filter(
            point__distance_lte=(stx_pnt, F("radius") * 2),
        ).order_by("name")
        self.assertEqual(len(qs), 5)
        self.assertIn("Pearland", self.get_names(qs))

        # With spheroid param
        if connection.features.supports_distance_geodetic:
            hobart = AustraliaCity.objects.get(name="Hobart")
            AustraliaCity.objects.update(ref_point=hobart.point)
            for ref_point in [hobart.point, F("ref_point")]:
                qs = AustraliaCity.objects.filter(
                    point__distance_lte=(ref_point, F("radius") * 70, "spheroid"),
                ).order_by("name")
                self.assertEqual(
                    self.get_names(qs), ["Canberra", "Hobart", "Melbourne"]
                )

        # With a complex geometry expression
        self.assertFalse(
            SouthTexasCity.objects.filter(
                point__distance_gt=(Union("point", "point"), 0)
            )
        )
        self.assertEqual(
            SouthTexasCity.objects.filter(
                point__distance_lte=(Union("point", "point"), 0)
            ).count(),
            SouthTexasCity.objects.count(),
        )

    @skipUnlessDBFeature("supports_distances_lookups")
    def test_distance_annotation_group_by(self):
        stx_pnt = self.stx_pnt.transform(
            SouthTexasCity._meta.get_field("point").srid,
            clone=True,
        )
        qs = (
            SouthTexasCity.objects.annotate(
                relative_distance=Case(
                    When(point__distance_lte=(stx_pnt, D(km=20)), then=Value(20)),
                    default=Value(100),
                    output_field=IntegerField(),
                ),
            )
            .values("relative_distance")
            .annotate(count=Count("pk"))
        )
        self.assertCountEqual(
            qs,
            [
                {"relative_distance": 20, "count": 5},
                {"relative_distance": 100, "count": 4},
            ],
        )

    def test_mysql_geodetic_distance_error(self):
        if not connection.ops.mysql:
            self.skipTest("This is a MySQL-specific test.")
        msg = (
            "Only numeric values of degree units are allowed on geodetic distance "
            "queries."
        )
        with self.assertRaisesMessage(ValueError, msg):
            AustraliaCity.objects.filter(
                point__distance_lte=(Point(0, 0), D(m=100))
            ).exists()

    @skipUnlessDBFeature("supports_dwithin_lookup")
    def test_dwithin_subquery(self):
        """dwithin lookup in a subquery using OuterRef as a parameter."""
        qs = CensusZipcode.objects.annotate(
            annotated_value=Exists(
                SouthTexasCity.objects.filter(
                    point__dwithin=(OuterRef("poly"), D(m=10)),
                )
            )
        ).filter(annotated_value=True)
        self.assertEqual(self.get_names(qs), ["77002", "77025", "77401"])

    @skipUnlessDBFeature("supports_dwithin_lookup", "supports_dwithin_distance_expr")
    def test_dwithin_with_expression_rhs(self):
        # LineString of Wollongong and Adelaide coords.
        ls = LineString(((150.902, -34.4245), (138.6, -34.9258)), srid=4326)
        qs = AustraliaCity.objects.filter(
            point__dwithin=(ls, F("allowed_distance")),
        ).order_by("name")
        self.assertEqual(
            self.get_names(qs),
            ["Adelaide", "Mittagong", "Shellharbour", "Thirroul", "Wollongong"],
        )

    @skipIfDBFeature("supports_dwithin_distance_expr")
    def test_dwithin_with_expression_rhs_not_supported(self):
        ls = LineString(((150.902, -34.4245), (138.6, -34.9258)), srid=4326)
        msg = (
            "This backend does not support expressions for specifying "
            "distance in the dwithin lookup."
        )
        with self.assertRaisesMessage(NotSupportedError, msg):
            list(
                AustraliaCity.objects.filter(
                    point__dwithin=(ls, F("allowed_distance")),
                )
            )


"""
=============================
Distance functions on PostGIS
=============================

                                              | Projected Geometry | Lon/lat Geometry | Geography (4326)

ST_Distance(geom1, geom2)                     |    OK (meters)     |   :-( (degrees)  |    OK (meters)

ST_Distance(geom1, geom2, use_spheroid=False) |    N/A             |   N/A            |    OK (meters), less accurate, quick

Distance_Sphere(geom1, geom2)                 |    N/A             |   OK (meters)    |    N/A

Distance_Spheroid(geom1, geom2, spheroid)     |    N/A             |   OK (meters)    |    N/A

ST_Perimeter(geom1)                           |    OK              |   :-( (degrees)  |    OK


================================
Distance functions on SpatiaLite
================================

                                                | Projected Geometry | Lon/lat Geometry

ST_Distance(geom1, geom2)                       |    OK (meters)     |      N/A

ST_Distance(geom1, geom2, use_ellipsoid=True)   |    N/A             |      OK (meters)

ST_Distance(geom1, geom2, use_ellipsoid=False)  |    N/A             |      OK (meters), less accurate, quick

Perimeter(geom1)                                |    OK              |      :-( (degrees)

"""  # NOQA


class DistanceFunctionsTests(FuncTestMixin, TestCase):
    fixtures = ["initial"]

    @skipUnlessDBFeature("has_Area_function")
    def test_area(self):
        # Reference queries:
        # SELECT ST_Area(poly) FROM distapp_southtexaszipcode;
        area_sq_m = [
            5437908.90234375,
            10183031.4389648,
            11254471.0073242,
            9881708.91772461,
        ]
        # Tolerance has to be lower for Oracle
        tol = 2
        for i, z in enumerate(
            SouthTexasZipcode.objects.annotate(area=Area("poly")).order_by("name")
        ):
            self.assertAlmostEqual(area_sq_m[i], z.area.sq_m, tol)

    @skipUnlessDBFeature("has_Distance_function")
    def test_distance_simple(self):
        """
        Test a simple distance query, with projected coordinates and without
        transformation.
        """
        lagrange = GEOSGeometry("POINT(805066.295722839 4231496.29461335)", 32140)
        houston = (
            SouthTexasCity.objects.annotate(dist=Distance("point", lagrange))
            .order_by("id")
            .first()
        )
        tol = 2 if connection.ops.oracle else 5
        self.assertAlmostEqual(houston.dist.m, 147075.069813, tol)

    @skipUnlessDBFeature("has_Distance_function", "has_Transform_function")
    def test_distance_projected(self):
        """
        Test the `Distance` function on projected coordinate systems.
        """
        # The point for La Grange, TX
        lagrange = GEOSGeometry("POINT(-96.876369 29.905320)", 4326)
        # Reference distances in feet and in meters. Got these values from
        # using the provided raw SQL statements.
        #  SELECT ST_Distance(
        #      point,
        #      ST_Transform(
        #          ST_GeomFromText('POINT(-96.876369 29.905320)', 4326),
        #          32140
        #      )
        #  )
        #  FROM distapp_southtexascity;
        m_distances = [
            147075.069813,
            139630.198056,
            140888.552826,
            138809.684197,
            158309.246259,
            212183.594374,
            70870.188967,
            165337.758878,
            139196.085105,
        ]
        #  SELECT ST_Distance(
        #      point,
        #      ST_Transform(
        #          ST_GeomFromText('POINT(-96.876369 29.905320)', 4326),
        #          2278
        #      )
        #  )
        #  FROM distapp_southtexascityft;
        ft_distances = [
            482528.79154625,
            458103.408123001,
            462231.860397575,
            455411.438904354,
            519386.252102563,
            696139.009211594,
            232513.278304279,
            542445.630586414,
            456679.155883207,
        ]

        # Testing using different variations of parameters and using models
        # with different projected coordinate systems.
        dist1 = SouthTexasCity.objects.annotate(
            distance=Distance("point", lagrange)
        ).order_by("id")
        dist2 = SouthTexasCityFt.objects.annotate(
            distance=Distance("point", lagrange)
        ).order_by("id")
        dist_qs = [dist1, dist2]

        # Ensuring expected distances are returned for each distance queryset.
        for qs in dist_qs:
            for i, c in enumerate(qs):
                with self.subTest(c=c):
                    self.assertAlmostEqual(m_distances[i], c.distance.m, -1)
                    self.assertAlmostEqual(ft_distances[i], c.distance.survey_ft, -1)

    @skipUnlessDBFeature("has_Distance_function", "supports_distance_geodetic")
    def test_distance_geodetic(self):
        """
        Test the `Distance` function on geodetic coordinate systems.
        """
        # Testing geodetic distance calculation with a non-point geometry
        # (a LineString of Wollongong and Shellharbour coords).
        ls = LineString(((150.902, -34.4245), (150.87, -34.5789)), srid=4326)

        # Reference query:
        #  SELECT ST_distance_sphere(
        #      point,
        #      ST_GeomFromText(
        #          'LINESTRING(150.9020 -34.4245,150.8700 -34.5789)',
        #          4326
        #      )
        #  )
        #  FROM distapp_australiacity ORDER BY name;
        distances = [
            1120954.92533513,
            140575.720018241,
            640396.662906304,
            60580.9693849269,
            972807.955955075,
            568451.8357838,
            40435.4335201384,
            0,
            68272.3896586844,
            12375.0643697706,
            0,
        ]
        qs = AustraliaCity.objects.annotate(distance=Distance("point", ls)).order_by(
            "name"
        )
        for city, distance in zip(qs, distances):
            with self.subTest(city=city, distance=distance):
                # Testing equivalence to within a meter (kilometer on
                # SpatiaLite).
                tol = -3 if connection.ops.spatialite else 0
                self.assertAlmostEqual(distance, city.distance.m, tol)

    @skipUnlessDBFeature("has_Distance_function", "supports_distance_geodetic")
    def test_distance_geodetic_spheroid(self):
        tol = 2 if connection.ops.oracle else 4

        # Got the reference distances using the raw SQL statements:
        #  SELECT ST_distance_spheroid(
        #      point,
        #      ST_GeomFromText('POINT(151.231341 -33.952685)', 4326),
        #      'SPHEROID["WGS 84",6378137.0,298.257223563]'
        #  )
        #  FROM distapp_australiacity WHERE (NOT (id = 11));
        #  SELECT ST_distance_sphere(
        #      point,
        #      ST_GeomFromText('POINT(151.231341 -33.952685)', 4326)
        #  )
        #  FROM distapp_australiacity
        #  WHERE (NOT (id = 11));  st_distance_sphere
        spheroid_distances = [
            60504.0628957201,
            77023.9489850262,
            49154.8867574404,
            90847.4358768573,
            217402.811919332,
            709599.234564757,
            640011.483550888,
            7772.00667991925,
            1047861.78619339,
            1165126.55236034,
        ]
        sphere_distances = [
            60580.9693849267,
            77144.0435286473,
            49199.4415344719,
            90804.7533823494,
            217713.384600405,
            709134.127242793,
            639828.157159169,
            7786.82949717788,
            1049204.06569028,
            1162623.7238134,
        ]
        # Testing with spheroid distances first.
        hillsdale = AustraliaCity.objects.get(name="Hillsdale")
        qs = (
            AustraliaCity.objects.exclude(id=hillsdale.id)
            .annotate(distance=Distance("point", hillsdale.point, spheroid=True))
            .order_by("id")
        )
        for i, c in enumerate(qs):
            with self.subTest(c=c):
                self.assertAlmostEqual(spheroid_distances[i], c.distance.m, tol)
        if connection.ops.postgis or connection.ops.spatialite:
            # PostGIS uses sphere-only distances by default, testing these as
            # well.
            qs = (
                AustraliaCity.objects.exclude(id=hillsdale.id)
                .annotate(distance=Distance("point", hillsdale.point))
                .order_by("id")
            )
            for i, c in enumerate(qs):
                with self.subTest(c=c):
                    self.assertAlmostEqual(sphere_distances[i], c.distance.m, tol)

    @skipIfDBFeature("supports_distance_geodetic")
    @skipUnlessDBFeature("has_Distance_function")
    def test_distance_function_raw_result(self):
        distance = (
            Interstate.objects.annotate(
                d=Distance(Point(0, 0, srid=4326), Point(0, 1, srid=4326)),
            )
            .first()
            .d
        )
        self.assertEqual(distance, 1)

    @skipUnlessDBFeature("has_Distance_function")
    def test_distance_function_d_lookup(self):
        qs = Interstate.objects.annotate(
            d=Distance(Point(0, 0, srid=3857), Point(0, 1, srid=3857)),
        ).filter(d=D(m=1))
        self.assertTrue(qs.exists())

    @skipUnlessDBFeature("supports_tolerance_parameter")
    def test_distance_function_tolerance_escaping(self):
        qs = (
            Interstate.objects.annotate(
                d=Distance(
                    Point(500, 500, srid=3857),
                    Point(0, 0, srid=3857),
                    tolerance="0.05) = 1 OR 1=1 OR (1+1",
                ),
            )
            .filter(d=D(m=1))
            .values("pk")
        )
        msg = "The tolerance parameter has the wrong type"
        with self.assertRaisesMessage(TypeError, msg):
            qs.exists()

    @skipUnlessDBFeature("supports_tolerance_parameter")
    def test_distance_function_tolerance(self):
        # Tolerance is greater than distance.
        qs = (
            Interstate.objects.annotate(
                d=Distance(
                    Point(0, 0, srid=3857),
                    Point(1, 1, srid=3857),
                    tolerance=1.5,
                ),
            )
            .filter(d=0)
            .values("pk")
        )
        self.assertIs(qs.exists(), True)

    @skipIfDBFeature("supports_distance_geodetic")
    @skipUnlessDBFeature("has_Distance_function")
    def test_distance_function_raw_result_d_lookup(self):
        qs = Interstate.objects.annotate(
            d=Distance(Point(0, 0, srid=4326), Point(0, 1, srid=4326)),
        ).filter(d=D(m=1))
        msg = "Distance measure is supplied, but units are unknown for result."
        with self.assertRaisesMessage(ValueError, msg):
            list(qs)

    @skipUnlessDBFeature("has_Distance_function", "has_Transform_function")
    def test_distance_transform(self):
        """
        Test the `Distance` function used with `Transform` on a geographic
        field.
        """
        # We'll be using a Polygon (created by buffering the centroid
        # of 77005 to 100m) -- which aren't allowed in geographic distance
        # queries normally, however our field has been transformed to
        # a non-geographic system.
        z = SouthTexasZipcode.objects.get(name="77005")

        # Reference query:
        # SELECT ST_Distance(
        #   ST_Transform("distapp_censuszipcode"."poly", 32140),
        #   ST_GeomFromText('<buffer_wkt>', 32140))
        # FROM "distapp_censuszipcode";
        dists_m = [3553.30384972258, 1243.18391525602, 2186.15439472242]

        # Having our buffer in the SRID of the transformation and of the field
        # -- should get the same results. The first buffer has no need for
        # transformation SQL because it is the same SRID as what was given
        # to `transform()`. The second buffer will need to be transformed,
        # however.
        buf1 = z.poly.centroid.buffer(100)
        buf2 = buf1.transform(4269, clone=True)
        ref_zips = ["77002", "77025", "77401"]

        for buf in [buf1, buf2]:
            qs = (
                CensusZipcode.objects.exclude(name="77005")
                .annotate(distance=Distance(Transform("poly", 32140), buf))
                .order_by("name")
            )
            self.assertEqual(ref_zips, sorted(c.name for c in qs))
            for i, z in enumerate(qs):
                self.assertAlmostEqual(z.distance.m, dists_m[i], 5)

    @skipUnlessDBFeature("has_Distance_function")
    def test_distance_order_by(self):
        qs = (
            SouthTexasCity.objects.annotate(
                distance=Distance("point", Point(3, 3, srid=32140))
            )
            .order_by("distance")
            .values_list("name", flat=True)
            .filter(name__in=("San Antonio", "Pearland"))
        )
        self.assertSequenceEqual(qs, ["San Antonio", "Pearland"])

    @skipUnlessDBFeature("has_Length_function")
    def test_length(self):
        """
        Test the `Length` function.
        """
        # Reference query (should use `length_spheroid`).
        #  SELECT ST_length_spheroid(
        #      ST_GeomFromText('<wkt>', 4326)
        #      'SPHEROID["WGS 84",6378137,298.257223563,
        #        AUTHORITY["EPSG","7030"]]'
        #  );
        len_m1 = 473504.769553813
        len_m2 = 4617.668

        if connection.features.supports_length_geodetic:
            qs = Interstate.objects.annotate(length=Length("path"))
            tol = 2 if connection.ops.oracle else 3
            self.assertAlmostEqual(len_m1, qs[0].length.m, tol)
            # TODO: test with spheroid argument (True and False)
        else:
            # Does not support geodetic coordinate systems.
            with self.assertRaises(NotSupportedError):
                list(Interstate.objects.annotate(length=Length("path")))

        # Now doing length on a projected coordinate system.
        i10 = SouthTexasInterstate.objects.annotate(length=Length("path")).get(
            name="I-10"
        )
        self.assertAlmostEqual(len_m2, i10.length.m, 2)
        self.assertTrue(
            SouthTexasInterstate.objects.annotate(length=Length("path"))
            .filter(length__gt=4000)
            .exists()
        )
        # Length with an explicit geometry value.
        qs = Interstate.objects.annotate(length=Length(i10.path))
        self.assertAlmostEqual(qs.first().length.m, len_m2, 2)

    @skipUnlessDBFeature("has_Perimeter_function")
    def test_perimeter(self):
        """
        Test the `Perimeter` function.
        """
        # Reference query:
        #  SELECT ST_Perimeter(distapp_southtexaszipcode.poly)
        #  FROM distapp_southtexaszipcode;
        perim_m = [
            18404.3550889361,
            15627.2108551001,
            20632.5588368978,
            17094.5996143697,
        ]
        tol = 2 if connection.ops.oracle else 7
        qs = SouthTexasZipcode.objects.annotate(perimeter=Perimeter("poly")).order_by(
            "name"
        )
        for i, z in enumerate(qs):
            self.assertAlmostEqual(perim_m[i], z.perimeter.m, tol)

        # Running on points; should return 0.
        qs = SouthTexasCity.objects.annotate(perim=Perimeter("point"))
        for city in qs:
            self.assertEqual(0, city.perim.m)

    @skipUnlessDBFeature("has_Perimeter_function")
    def test_perimeter_geodetic(self):
        # Currently only Oracle supports calculating the perimeter on geodetic
        # geometries (without being transformed).
        qs1 = CensusZipcode.objects.annotate(perim=Perimeter("poly"))
        if connection.features.supports_perimeter_geodetic:
            self.assertAlmostEqual(qs1[0].perim.m, 18406.3818954314, 3)
        else:
            with self.assertRaises(NotSupportedError):
                list(qs1)
        # But should work fine when transformed to projected coordinates
        qs2 = CensusZipcode.objects.annotate(
            perim=Perimeter(Transform("poly", 32140))
        ).filter(name="77002")
        self.assertAlmostEqual(qs2[0].perim.m, 18404.355, 3)

    @skipUnlessDBFeature(
        "supports_null_geometries", "has_Area_function", "has_Distance_function"
    )
    def test_measurement_null_fields(self):
        """
        Test the measurement functions on fields with NULL values.
        """
        # Creating SouthTexasZipcode w/NULL value.
        SouthTexasZipcode.objects.create(name="78212")
        # Performing distance/area queries against the NULL PolygonField,
        # and ensuring the result of the operations is None.
        htown = SouthTexasCity.objects.get(name="Downtown Houston")
        z = SouthTexasZipcode.objects.annotate(
            distance=Distance("poly", htown.point), area=Area("poly")
        ).get(name="78212")
        self.assertIsNone(z.distance)
        self.assertIsNone(z.area)
