"""
Tests for geography support in PostGIS
"""

import os

from django.contrib.gis.db import models
from django.contrib.gis.db.models.functions import Area, Distance
from django.contrib.gis.measure import D
from django.core.exceptions import ValidationError
from django.db import NotSupportedError, connection
from django.db.models.functions import Cast
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from ..utils import FuncTestMixin
from .models import City, CityUnique, County, Zipcode


class GeographyTest(TestCase):
    fixtures = ["initial"]

    def test01_fixture_load(self):
        "Ensure geography features loaded properly."
        self.assertEqual(8, City.objects.count())

    @skipUnlessDBFeature("supports_distances_lookups", "supports_distance_geodetic")
    def test02_distance_lookup(self):
        "Testing distance lookup support on non-point geography fields."
        z = Zipcode.objects.get(code="77002")
        cities1 = list(
            City.objects.filter(point__distance_lte=(z.poly, D(mi=500)))
            .order_by("name")
            .values_list("name", flat=True)
        )
        cities2 = list(
            City.objects.filter(point__dwithin=(z.poly, D(mi=500)))
            .order_by("name")
            .values_list("name", flat=True)
        )
        for cities in [cities1, cities2]:
            self.assertEqual(["Dallas", "Houston", "Oklahoma City"], cities)

    @skipUnlessDBFeature("supports_geography", "supports_geometry_field_unique_index")
    def test_geography_unique(self):
        """
        Cast geography fields to geometry type when validating uniqueness to
        remove the reliance on unavailable ~= operator.
        """
        htown = City.objects.get(name="Houston")
        CityUnique.objects.create(point=htown.point)
        duplicate = CityUnique(point=htown.point)
        msg = "City unique with this Point already exists."
        with self.assertRaisesMessage(ValidationError, msg):
            duplicate.validate_unique()

    @skipUnlessDBFeature("supports_geography")
    def test_operators_functions_unavailable_for_geography(self):
        """
        Geography fields are cast to geometry if the relevant operators or
        functions are not available.
        """
        z = Zipcode.objects.get(code="77002")
        point_field = "%s.%s::geometry" % (
            connection.ops.quote_name(City._meta.db_table),
            connection.ops.quote_name("point"),
        )
        # ST_Within.
        qs = City.objects.filter(point__within=z.poly)
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(qs.count(), 1)
        self.assertIn(f"ST_Within({point_field}", ctx.captured_queries[0]["sql"])
        # @ operator.
        qs = City.objects.filter(point__contained=z.poly)
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(qs.count(), 1)
        self.assertIn(f"{point_field} @", ctx.captured_queries[0]["sql"])
        # ~= operator.
        htown = City.objects.get(name="Houston")
        qs = City.objects.filter(point__exact=htown.point)
        with CaptureQueriesContext(connection) as ctx:
            self.assertEqual(qs.count(), 1)
        self.assertIn(f"{point_field} ~=", ctx.captured_queries[0]["sql"])

    def test05_geography_layermapping(self):
        "Testing LayerMapping support on models with geography fields."
        # There is a similar test in `layermap` that uses the same data set,
        # but the County model here is a bit different.
        from django.contrib.gis.utils import LayerMapping

        # Getting the shapefile and mapping dictionary.
        shp_path = os.path.realpath(
            os.path.join(os.path.dirname(__file__), "..", "data")
        )
        co_shp = os.path.join(shp_path, "counties", "counties.shp")
        co_mapping = {
            "name": "Name",
            "state": "State",
            "mpoly": "MULTIPOLYGON",
        }
        # Reference county names, number of polygons, and state names.
        names = ["Bexar", "Galveston", "Harris", "Honolulu", "Pueblo"]
        num_polys = [1, 2, 1, 19, 1]  # Number of polygons for each.
        st_names = ["Texas", "Texas", "Texas", "Hawaii", "Colorado"]

        lm = LayerMapping(County, co_shp, co_mapping, source_srs=4269, unique="name")
        lm.save(silent=True, strict=True)

        for c, name, num_poly, state in zip(
            County.objects.order_by("name"), names, num_polys, st_names
        ):
            self.assertEqual(4326, c.mpoly.srid)
            self.assertEqual(num_poly, len(c.mpoly))
            self.assertEqual(name, c.name)
            self.assertEqual(state, c.state)


class GeographyFunctionTests(FuncTestMixin, TestCase):
    fixtures = ["initial"]

    @skipUnlessDBFeature("supports_extent_aggr")
    def test_cast_aggregate(self):
        """
        Cast a geography to a geometry field for an aggregate function that
        expects a geometry input.
        """
        if not connection.features.supports_geography:
            self.skipTest("This test needs geography support")
        expected = (
            -96.8016128540039,
            29.7633724212646,
            -95.3631439208984,
            32.782058715820,
        )
        res = City.objects.filter(name__in=("Houston", "Dallas")).aggregate(
            extent=models.Extent(Cast("point", models.PointField()))
        )
        for val, exp in zip(res["extent"], expected):
            self.assertAlmostEqual(exp, val, 4)

    @skipUnlessDBFeature("has_Distance_function", "supports_distance_geodetic")
    def test_distance_function(self):
        """
        Testing Distance() support on non-point geography fields.
        """
        if connection.ops.oracle:
            ref_dists = [0, 4899.68, 8081.30, 9115.15]
        elif connection.ops.spatialite:
            if connection.ops.spatial_version < (5,):
                # SpatiaLite < 5 returns non-zero distance for polygons and points
                # covered by that polygon.
                ref_dists = [326.61, 4899.68, 8081.30, 9115.15]
            else:
                ref_dists = [0, 4899.68, 8081.30, 9115.15]
        else:
            ref_dists = [0, 4891.20, 8071.64, 9123.95]
        htown = City.objects.get(name="Houston")
        qs = Zipcode.objects.annotate(
            distance=Distance("poly", htown.point),
            distance2=Distance(htown.point, "poly"),
        )
        for z, ref in zip(qs, ref_dists):
            self.assertAlmostEqual(z.distance.m, ref, 2)

        if connection.ops.postgis:
            # PostGIS casts geography to geometry when distance2 is calculated.
            ref_dists = [0, 4899.68, 8081.30, 9115.15]
        for z, ref in zip(qs, ref_dists):
            self.assertAlmostEqual(z.distance2.m, ref, 2)

        if not connection.ops.spatialite:
            # Distance function combined with a lookup.
            hzip = Zipcode.objects.get(code="77002")
            self.assertEqual(qs.get(distance__lte=0), hzip)

    @skipUnlessDBFeature("has_Area_function", "supports_area_geodetic")
    def test_geography_area(self):
        """
        Testing that Area calculations work on geography columns.
        """
        # SELECT ST_Area(poly) FROM geogapp_zipcode WHERE code='77002';
        z = Zipcode.objects.annotate(area=Area("poly")).get(code="77002")
        # Round to the nearest thousand as possible values (depending on
        # the database and geolib) include 5439084, 5439100, 5439101.
        rounded_value = z.area.sq_m
        rounded_value -= z.area.sq_m % 1000
        self.assertEqual(rounded_value, 5439000)

    @skipUnlessDBFeature("has_Area_function")
    @skipIfDBFeature("supports_area_geodetic")
    def test_geodetic_area_raises_if_not_supported(self):
        with self.assertRaisesMessage(
            NotSupportedError, "Area on geodetic coordinate systems not supported."
        ):
            Zipcode.objects.annotate(area=Area("poly")).get(code="77002")
