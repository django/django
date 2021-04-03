import json
import math
import re
from decimal import Decimal

from django.contrib.gis.db.models import GeometryField, PolygonField, functions
from django.contrib.gis.geos import (
    GEOSGeometry, LineString, Point, Polygon, fromstr,
)
from django.contrib.gis.measure import Area
from django.db import NotSupportedError, connection
from django.db.models import IntegerField, Sum, Value
from django.test import TestCase, skipUnlessDBFeature

from ..utils import FuncTestMixin
from .models import City, Country, CountryWebMercator, State, Track


class GISFunctionsTests(FuncTestMixin, TestCase):
    """
    Testing functions from django/contrib/gis/db/models/functions.py.
    Area/Distance/Length/Perimeter are tested in distapp/tests.

    Please keep the tests in function's alphabetic order.
    """
    fixtures = ['initial']

    def test_asgeojson(self):
        if not connection.features.has_AsGeoJSON_function:
            with self.assertRaises(NotSupportedError):
                list(Country.objects.annotate(json=functions.AsGeoJSON('mpoly')))
            return

        pueblo_json = '{"type":"Point","coordinates":[-104.609252,38.255001]}'
        houston_json = json.loads(
            '{"type":"Point","crs":{"type":"name","properties":'
            '{"name":"EPSG:4326"}},"coordinates":[-95.363151,29.763374]}'
        )
        victoria_json = json.loads(
            '{"type":"Point","bbox":[-123.30519600,48.46261100,-123.30519600,48.46261100],'
            '"coordinates":[-123.305196,48.462611]}'
        )
        chicago_json = json.loads(
            '{"type":"Point","crs":{"type":"name","properties":{"name":"EPSG:4326"}},'
            '"bbox":[-87.65018,41.85039,-87.65018,41.85039],"coordinates":[-87.65018,41.85039]}'
        )
        if 'crs' in connection.features.unsupported_geojson_options:
            del houston_json['crs']
            del chicago_json['crs']
        if 'bbox' in connection.features.unsupported_geojson_options:
            del chicago_json['bbox']
            del victoria_json['bbox']
        if 'precision' in connection.features.unsupported_geojson_options:
            chicago_json['coordinates'] = [-87.650175, 41.850385]

        # Precision argument should only be an integer
        with self.assertRaises(TypeError):
            City.objects.annotate(geojson=functions.AsGeoJSON('point', precision='foo'))

        # Reference queries and values.
        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 0)
        # FROM "geoapp_city" WHERE "geoapp_city"."name" = 'Pueblo';
        self.assertJSONEqual(
            pueblo_json,
            City.objects.annotate(geojson=functions.AsGeoJSON('point')).get(name='Pueblo').geojson
        )

        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 2) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Houston';
        # This time we want to include the CRS by using the `crs` keyword.
        self.assertJSONEqual(
            City.objects.annotate(json=functions.AsGeoJSON('point', crs=True)).get(name='Houston').json,
            houston_json,
        )

        # SELECT ST_AsGeoJson("geoapp_city"."point", 8, 1) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Houston';
        # This time we include the bounding box by using the `bbox` keyword.
        self.assertJSONEqual(
            City.objects.annotate(
                geojson=functions.AsGeoJSON('point', bbox=True)
            ).get(name='Victoria').geojson,
            victoria_json,
        )

        # SELECT ST_AsGeoJson("geoapp_city"."point", 5, 3) FROM "geoapp_city"
        # WHERE "geoapp_city"."name" = 'Chicago';
        # Finally, we set every available keyword.
        # MariaDB doesn't limit the number of decimals in bbox.
        if connection.ops.mariadb:
            chicago_json['bbox'] = [-87.650175, 41.850385, -87.650175, 41.850385]
        try:
            self.assertJSONEqual(
                City.objects.annotate(
                    geojson=functions.AsGeoJSON('point', bbox=True, crs=True, precision=5)
                ).get(name='Chicago').geojson,
                chicago_json,
            )
        except AssertionError:
            # Give a second chance with different coords rounding.
            chicago_json['coordinates'][1] = 41.85038
            self.assertJSONEqual(
                City.objects.annotate(
                    geojson=functions.AsGeoJSON('point', bbox=True, crs=True, precision=5)
                ).get(name='Chicago').geojson,
                chicago_json,
            )

    @skipUnlessDBFeature("has_AsGML_function")
    def test_asgml(self):
        # Should throw a TypeError when trying to obtain GML from a
        # non-geometry field.
        qs = City.objects.all()
        with self.assertRaises(TypeError):
            qs.annotate(gml=functions.AsGML('name'))
        ptown = City.objects.annotate(gml=functions.AsGML('point', precision=9)).get(name='Pueblo')

        if connection.ops.oracle:
            # No precision parameter for Oracle :-/
            gml_regex = re.compile(
                r'^<gml:Point srsName="EPSG:4326" xmlns:gml="http://www.opengis.net/gml">'
                r'<gml:coordinates decimal="\." cs="," ts=" ">-104.60925\d+,38.25500\d+ '
                r'</gml:coordinates></gml:Point>'
            )
        else:
            gml_regex = re.compile(
                r'^<gml:Point srsName="EPSG:4326"><gml:coordinates>'
                r'-104\.60925\d+,38\.255001</gml:coordinates></gml:Point>'
            )
        self.assertTrue(gml_regex.match(ptown.gml))
        self.assertIn(
            '<gml:pos srsDimension="2">',
            City.objects.annotate(gml=functions.AsGML('point', version=3)).get(name='Pueblo').gml
        )

    @skipUnlessDBFeature("has_AsKML_function")
    def test_askml(self):
        # Should throw a TypeError when trying to obtain KML from a
        # non-geometry field.
        with self.assertRaises(TypeError):
            City.objects.annotate(kml=functions.AsKML('name'))

        # Ensuring the KML is as expected.
        ptown = City.objects.annotate(kml=functions.AsKML('point', precision=9)).get(name='Pueblo')
        self.assertEqual('<Point><coordinates>-104.609252,38.255001</coordinates></Point>', ptown.kml)

    @skipUnlessDBFeature("has_AsSVG_function")
    def test_assvg(self):
        with self.assertRaises(TypeError):
            City.objects.annotate(svg=functions.AsSVG('point', precision='foo'))
        # SELECT AsSVG(geoapp_city.point, 0, 8) FROM geoapp_city WHERE name = 'Pueblo';
        svg1 = 'cx="-104.609252" cy="-38.255001"'
        # Even though relative, only one point so it's practically the same except for
        # the 'c' letter prefix on the x,y values.
        svg2 = svg1.replace('c', '')
        self.assertEqual(svg1, City.objects.annotate(svg=functions.AsSVG('point')).get(name='Pueblo').svg)
        self.assertEqual(svg2, City.objects.annotate(svg=functions.AsSVG('point', relative=5)).get(name='Pueblo').svg)

    @skipUnlessDBFeature('has_AsWKB_function')
    def test_aswkb(self):
        wkb = City.objects.annotate(
            wkb=functions.AsWKB(Point(1, 2, srid=4326)),
        ).first().wkb
        # WKB is either XDR or NDR encoded.
        self.assertIn(
            bytes(wkb),
            (
                b'\x00\x00\x00\x00\x01?\xf0\x00\x00\x00\x00\x00\x00@\x00\x00'
                b'\x00\x00\x00\x00\x00',
                b'\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\xf0?\x00\x00'
                b'\x00\x00\x00\x00\x00@',
            ),
        )

    @skipUnlessDBFeature('has_AsWKT_function')
    def test_aswkt(self):
        wkt = City.objects.annotate(
            wkt=functions.AsWKT(Point(1, 2, srid=4326)),
        ).first().wkt
        self.assertEqual(wkt, 'POINT (1.0 2.0)' if connection.ops.oracle else 'POINT(1 2)')

    @skipUnlessDBFeature("has_Azimuth_function")
    def test_azimuth(self):
        # Returns the azimuth in radians.
        azimuth_expr = functions.Azimuth(Point(0, 0, srid=4326), Point(1, 1, srid=4326))
        self.assertAlmostEqual(City.objects.annotate(azimuth=azimuth_expr).first().azimuth, math.pi / 4)
        # Returns None if the two points are coincident.
        azimuth_expr = functions.Azimuth(Point(0, 0, srid=4326), Point(0, 0, srid=4326))
        self.assertIsNone(City.objects.annotate(azimuth=azimuth_expr).first().azimuth)

    @skipUnlessDBFeature("has_BoundingCircle_function")
    def test_bounding_circle(self):
        def circle_num_points(num_seg):
            # num_seg is the number of segments per quarter circle.
            return (4 * num_seg) + 1

        expected_areas = (169, 136) if connection.ops.postgis else (171, 126)
        qs = Country.objects.annotate(circle=functions.BoundingCircle('mpoly')).order_by('name')
        self.assertAlmostEqual(qs[0].circle.area, expected_areas[0], 0)
        self.assertAlmostEqual(qs[1].circle.area, expected_areas[1], 0)
        if connection.ops.postgis:
            # By default num_seg=48.
            self.assertEqual(qs[0].circle.num_points, circle_num_points(48))
            self.assertEqual(qs[1].circle.num_points, circle_num_points(48))

        tests = [12, Value(12, output_field=IntegerField())]
        for num_seq in tests:
            with self.subTest(num_seq=num_seq):
                qs = Country.objects.annotate(
                    circle=functions.BoundingCircle('mpoly', num_seg=num_seq),
                ).order_by('name')
                if connection.ops.postgis:
                    self.assertGreater(qs[0].circle.area, 168.4, 0)
                    self.assertLess(qs[0].circle.area, 169.5, 0)
                    self.assertAlmostEqual(qs[1].circle.area, 136, 0)
                    self.assertEqual(qs[0].circle.num_points, circle_num_points(12))
                    self.assertEqual(qs[1].circle.num_points, circle_num_points(12))
                else:
                    self.assertAlmostEqual(qs[0].circle.area, expected_areas[0], 0)
                    self.assertAlmostEqual(qs[1].circle.area, expected_areas[1], 0)

    @skipUnlessDBFeature("has_Centroid_function")
    def test_centroid(self):
        qs = State.objects.exclude(poly__isnull=True).annotate(centroid=functions.Centroid('poly'))
        tol = 1.8 if connection.ops.mysql else (0.1 if connection.ops.oracle else 0.00001)
        for state in qs:
            self.assertTrue(state.poly.centroid.equals_exact(state.centroid, tol))

        with self.assertRaisesMessage(TypeError, "'Centroid' takes exactly 1 argument (2 given)"):
            State.objects.annotate(centroid=functions.Centroid('poly', 'poly'))

    @skipUnlessDBFeature("has_Difference_function")
    def test_difference(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.annotate(diff=functions.Difference('mpoly', geom))
        # Oracle does something screwy with the Texas geometry.
        if connection.ops.oracle:
            qs = qs.exclude(name='Texas')

        for c in qs:
            self.assertTrue(c.mpoly.difference(geom).equals(c.diff))

    @skipUnlessDBFeature("has_Difference_function", "has_Transform_function")
    def test_difference_mixed_srid(self):
        """Testing with mixed SRID (Country has default 4326)."""
        geom = Point(556597.4, 2632018.6, srid=3857)  # Spherical Mercator
        qs = Country.objects.annotate(difference=functions.Difference('mpoly', geom))
        # Oracle does something screwy with the Texas geometry.
        if connection.ops.oracle:
            qs = qs.exclude(name='Texas')
        for c in qs:
            self.assertTrue(c.mpoly.difference(geom).equals(c.difference))

    @skipUnlessDBFeature("has_Envelope_function")
    def test_envelope(self):
        countries = Country.objects.annotate(envelope=functions.Envelope('mpoly'))
        for country in countries:
            self.assertTrue(country.envelope.equals(country.mpoly.envelope))

    @skipUnlessDBFeature("has_ForcePolygonCW_function")
    def test_force_polygon_cw(self):
        rings = (
            ((0, 0), (5, 0), (0, 5), (0, 0)),
            ((1, 1), (1, 3), (3, 1), (1, 1)),
        )
        rhr_rings = (
            ((0, 0), (0, 5), (5, 0), (0, 0)),
            ((1, 1), (3, 1), (1, 3), (1, 1)),
        )
        State.objects.create(name='Foo', poly=Polygon(*rings))
        st = State.objects.annotate(force_polygon_cw=functions.ForcePolygonCW('poly')).get(name='Foo')
        self.assertEqual(rhr_rings, st.force_polygon_cw.coords)

    @skipUnlessDBFeature("has_GeoHash_function")
    def test_geohash(self):
        # Reference query:
        # SELECT ST_GeoHash(point) FROM geoapp_city WHERE name='Houston';
        # SELECT ST_GeoHash(point, 5) FROM geoapp_city WHERE name='Houston';
        ref_hash = '9vk1mfq8jx0c8e0386z6'
        h1 = City.objects.annotate(geohash=functions.GeoHash('point')).get(name='Houston')
        h2 = City.objects.annotate(geohash=functions.GeoHash('point', precision=5)).get(name='Houston')
        self.assertEqual(ref_hash, h1.geohash[:len(ref_hash)])
        self.assertEqual(ref_hash[:5], h2.geohash)

    @skipUnlessDBFeature('has_GeometryDistance_function')
    def test_geometry_distance(self):
        point = Point(-90, 40, srid=4326)
        qs = City.objects.annotate(distance=functions.GeometryDistance('point', point)).order_by('distance')
        distances = (
            2.99091995527296,
            5.33507274054713,
            9.33852187483721,
            9.91769193646233,
            11.556465744884,
            14.713098433352,
            34.3635252198568,
            276.987855073372,
        )
        for city, expected_distance in zip(qs, distances):
            with self.subTest(city=city):
                self.assertAlmostEqual(city.distance, expected_distance)

    @skipUnlessDBFeature("has_Intersection_function")
    def test_intersection(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.annotate(inter=functions.Intersection('mpoly', geom))
        for c in qs:
            if connection.features.empty_intersection_returns_none:
                self.assertIsNone(c.inter)
            else:
                self.assertIs(c.inter.empty, True)

    @skipUnlessDBFeature("has_IsValid_function")
    def test_isvalid(self):
        valid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
        invalid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 1 1, 1 0, 0 0))')
        State.objects.create(name='valid', poly=valid_geom)
        State.objects.create(name='invalid', poly=invalid_geom)
        valid = State.objects.filter(name='valid').annotate(isvalid=functions.IsValid('poly')).first()
        invalid = State.objects.filter(name='invalid').annotate(isvalid=functions.IsValid('poly')).first()
        self.assertIs(valid.isvalid, True)
        self.assertIs(invalid.isvalid, False)

    @skipUnlessDBFeature("has_Area_function")
    def test_area_with_regular_aggregate(self):
        # Create projected country objects, for this test to work on all backends.
        for c in Country.objects.all():
            CountryWebMercator.objects.create(name=c.name, mpoly=c.mpoly.transform(3857, clone=True))
        # Test in projected coordinate system
        qs = CountryWebMercator.objects.annotate(area_sum=Sum(functions.Area('mpoly')))
        # Some backends (e.g. Oracle) cannot group by multipolygon values, so
        # defer such fields in the aggregation query.
        for c in qs.defer('mpoly'):
            result = c.area_sum
            # If the result is a measure object, get value.
            if isinstance(result, Area):
                result = result.sq_m
            self.assertAlmostEqual((result - c.mpoly.area) / c.mpoly.area, 0)

    @skipUnlessDBFeature("has_Area_function")
    def test_area_lookups(self):
        # Create projected countries so the test works on all backends.
        CountryWebMercator.objects.bulk_create(
            CountryWebMercator(name=c.name, mpoly=c.mpoly.transform(3857, clone=True))
            for c in Country.objects.all()
        )
        qs = CountryWebMercator.objects.annotate(area=functions.Area('mpoly'))
        self.assertEqual(qs.get(area__lt=Area(sq_km=500000)), CountryWebMercator.objects.get(name='New Zealand'))

        with self.assertRaisesMessage(ValueError, 'AreaField only accepts Area measurement objects.'):
            qs.get(area__lt=500000)

    @skipUnlessDBFeature("has_LineLocatePoint_function")
    def test_line_locate_point(self):
        pos_expr = functions.LineLocatePoint(LineString((0, 0), (0, 3), srid=4326), Point(0, 1, srid=4326))
        self.assertAlmostEqual(State.objects.annotate(pos=pos_expr).first().pos, 0.3333333)

    @skipUnlessDBFeature("has_MakeValid_function")
    def test_make_valid(self):
        invalid_geom = fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 1 1, 1 0, 0 0))')
        State.objects.create(name='invalid', poly=invalid_geom)
        invalid = State.objects.filter(name='invalid').annotate(repaired=functions.MakeValid('poly')).first()
        self.assertIs(invalid.repaired.valid, True)
        self.assertTrue(invalid.repaired.equals(fromstr('POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))', srid=invalid.poly.srid)))

    @skipUnlessDBFeature('has_MakeValid_function')
    def test_make_valid_multipolygon(self):
        invalid_geom = fromstr(
            'POLYGON((0 0, 0 1 , 1 1 , 1 0, 0 0), '
            '(10 0, 10 1, 11 1, 11 0, 10 0))'
        )
        State.objects.create(name='invalid', poly=invalid_geom)
        invalid = State.objects.filter(name='invalid').annotate(
            repaired=functions.MakeValid('poly'),
        ).get()
        self.assertIs(invalid.repaired.valid, True)
        self.assertTrue(invalid.repaired.equals(fromstr(
            'MULTIPOLYGON (((0 0, 0 1, 1 1, 1 0, 0 0)), '
            '((10 0, 10 1, 11 1, 11 0, 10 0)))',
            srid=invalid.poly.srid,
        )))
        self.assertEqual(len(invalid.repaired), 2)

    @skipUnlessDBFeature('has_MakeValid_function')
    def test_make_valid_output_field(self):
        # output_field is GeometryField instance because different geometry
        # types can be returned.
        output_field = functions.MakeValid(
            Value(Polygon(), PolygonField(srid=42)),
        ).output_field
        self.assertIs(output_field.__class__, GeometryField)
        self.assertEqual(output_field.srid, 42)

    @skipUnlessDBFeature("has_MemSize_function")
    def test_memsize(self):
        ptown = City.objects.annotate(size=functions.MemSize('point')).get(name='Pueblo')
        # Exact value depends on database and version.
        self.assertTrue(20 <= ptown.size <= 105)

    @skipUnlessDBFeature("has_NumGeom_function")
    def test_num_geom(self):
        # Both 'countries' only have two geometries.
        for c in Country.objects.annotate(num_geom=functions.NumGeometries('mpoly')):
            self.assertEqual(2, c.num_geom)

        qs = City.objects.filter(point__isnull=False).annotate(num_geom=functions.NumGeometries('point'))
        for city in qs:
            # The results for the number of geometries on non-collections
            # depends on the database.
            if connection.ops.mysql or connection.ops.mariadb:
                self.assertIsNone(city.num_geom)
            else:
                self.assertEqual(1, city.num_geom)

    @skipUnlessDBFeature("has_NumPoint_function")
    def test_num_points(self):
        coords = [(-95.363151, 29.763374), (-95.448601, 29.713803)]
        Track.objects.create(name='Foo', line=LineString(coords))
        qs = Track.objects.annotate(num_points=functions.NumPoints('line'))
        self.assertEqual(qs.first().num_points, 2)
        mpoly_qs = Country.objects.annotate(num_points=functions.NumPoints('mpoly'))
        if not connection.features.supports_num_points_poly:
            for c in mpoly_qs:
                self.assertIsNone(c.num_points)
            return

        for c in mpoly_qs:
            self.assertEqual(c.mpoly.num_points, c.num_points)

        for c in City.objects.annotate(num_points=functions.NumPoints('point')):
            self.assertEqual(c.num_points, 1)

    @skipUnlessDBFeature("has_PointOnSurface_function")
    def test_point_on_surface(self):
        qs = Country.objects.annotate(point_on_surface=functions.PointOnSurface('mpoly'))
        for country in qs:
            self.assertTrue(country.mpoly.intersection(country.point_on_surface))

    @skipUnlessDBFeature("has_Reverse_function")
    def test_reverse_geom(self):
        coords = [(-95.363151, 29.763374), (-95.448601, 29.713803)]
        Track.objects.create(name='Foo', line=LineString(coords))
        track = Track.objects.annotate(reverse_geom=functions.Reverse('line')).get(name='Foo')
        coords.reverse()
        self.assertEqual(tuple(coords), track.reverse_geom.coords)

    @skipUnlessDBFeature("has_Scale_function")
    def test_scale(self):
        xfac, yfac = 2, 3
        tol = 5  # The low precision tolerance is for SpatiaLite
        qs = Country.objects.annotate(scaled=functions.Scale('mpoly', xfac, yfac))
        for country in qs:
            for p1, p2 in zip(country.mpoly, country.scaled):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        self.assertAlmostEqual(c1[0] * xfac, c2[0], tol)
                        self.assertAlmostEqual(c1[1] * yfac, c2[1], tol)
        # Test float/Decimal values
        qs = Country.objects.annotate(scaled=functions.Scale('mpoly', 1.5, Decimal('2.5')))
        self.assertGreater(qs[0].scaled.area, qs[0].mpoly.area)

    @skipUnlessDBFeature("has_SnapToGrid_function")
    def test_snap_to_grid(self):
        # Let's try and break snap_to_grid() with bad combinations of arguments.
        for bad_args in ((), range(3), range(5)):
            with self.assertRaises(ValueError):
                Country.objects.annotate(snap=functions.SnapToGrid('mpoly', *bad_args))
        for bad_args in (('1.0',), (1.0, None), tuple(map(str, range(4)))):
            with self.assertRaises(TypeError):
                Country.objects.annotate(snap=functions.SnapToGrid('mpoly', *bad_args))

        # Boundary for San Marino, courtesy of Bjorn Sandvik of thematicmapping.org
        # from the world borders dataset he provides.
        wkt = ('MULTIPOLYGON(((12.41580 43.95795,12.45055 43.97972,12.45389 43.98167,'
               '12.46250 43.98472,12.47167 43.98694,12.49278 43.98917,'
               '12.50555 43.98861,12.51000 43.98694,12.51028 43.98277,'
               '12.51167 43.94333,12.51056 43.93916,12.49639 43.92333,'
               '12.49500 43.91472,12.48778 43.90583,12.47444 43.89722,'
               '12.46472 43.89555,12.45917 43.89611,12.41639 43.90472,'
               '12.41222 43.90610,12.40782 43.91366,12.40389 43.92667,'
               '12.40500 43.94833,12.40889 43.95499,12.41580 43.95795)))')
        Country.objects.create(name='San Marino', mpoly=fromstr(wkt))

        # Because floating-point arithmetic isn't exact, we set a tolerance
        # to pass into GEOS `equals_exact`.
        tol = 0.000000001

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.1)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 44,12.5 44,12.5 43.9,12.4 43.9,12.4 44)))')
        self.assertTrue(
            ref.equals_exact(
                Country.objects.annotate(
                    snap=functions.SnapToGrid('mpoly', 0.1)
                ).get(name='San Marino').snap,
                tol
            )
        )

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.05, 0.23)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr('MULTIPOLYGON(((12.4 43.93,12.45 43.93,12.5 43.93,12.45 43.93,12.4 43.93)))')
        self.assertTrue(
            ref.equals_exact(
                Country.objects.annotate(
                    snap=functions.SnapToGrid('mpoly', 0.05, 0.23)
                ).get(name='San Marino').snap,
                tol
            )
        )

        # SELECT AsText(ST_SnapToGrid("geoapp_country"."mpoly", 0.5, 0.17, 0.05, 0.23)) FROM "geoapp_country"
        # WHERE "geoapp_country"."name" = 'San Marino';
        ref = fromstr(
            'MULTIPOLYGON(((12.4 43.87,12.45 43.87,12.45 44.1,12.5 44.1,12.5 43.87,12.45 43.87,12.4 43.87)))'
        )
        self.assertTrue(
            ref.equals_exact(
                Country.objects.annotate(
                    snap=functions.SnapToGrid('mpoly', 0.05, 0.23, 0.5, 0.17)
                ).get(name='San Marino').snap,
                tol
            )
        )

    @skipUnlessDBFeature("has_SymDifference_function")
    def test_sym_difference(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.annotate(sym_difference=functions.SymDifference('mpoly', geom))
        # Oracle does something screwy with the Texas geometry.
        if connection.ops.oracle:
            qs = qs.exclude(name='Texas')
        for country in qs:
            self.assertTrue(country.mpoly.sym_difference(geom).equals(country.sym_difference))

    @skipUnlessDBFeature("has_Transform_function")
    def test_transform(self):
        # Pre-transformed points for Houston and Pueblo.
        ptown = fromstr('POINT(992363.390841912 481455.395105533)', srid=2774)

        # Asserting the result of the transform operation with the values in
        #  the pre-transformed points.
        h = City.objects.annotate(pt=functions.Transform('point', ptown.srid)).get(name='Pueblo')
        self.assertEqual(2774, h.pt.srid)
        # Precision is low due to version variations in PROJ and GDAL.
        self.assertLess(ptown.x - h.pt.x, 1)
        self.assertLess(ptown.y - h.pt.y, 1)

    @skipUnlessDBFeature("has_Translate_function")
    def test_translate(self):
        xfac, yfac = 5, -23
        qs = Country.objects.annotate(translated=functions.Translate('mpoly', xfac, yfac))
        for c in qs:
            for p1, p2 in zip(c.mpoly, c.translated):
                for r1, r2 in zip(p1, p2):
                    for c1, c2 in zip(r1.coords, r2.coords):
                        # The low precision is for SpatiaLite
                        self.assertAlmostEqual(c1[0] + xfac, c2[0], 5)
                        self.assertAlmostEqual(c1[1] + yfac, c2[1], 5)

    # Some combined function tests
    @skipUnlessDBFeature(
        "has_Difference_function", "has_Intersection_function",
        "has_SymDifference_function", "has_Union_function")
    def test_diff_intersection_union(self):
        geom = Point(5, 23, srid=4326)
        qs = Country.objects.all().annotate(
            difference=functions.Difference('mpoly', geom),
            sym_difference=functions.SymDifference('mpoly', geom),
            union=functions.Union('mpoly', geom),
            intersection=functions.Intersection('mpoly', geom),
        )

        if connection.ops.oracle:
            # Should be able to execute the queries; however, they won't be the same
            # as GEOS (because Oracle doesn't use GEOS internally like PostGIS or
            # SpatiaLite).
            return
        for c in qs:
            self.assertTrue(c.mpoly.difference(geom).equals(c.difference))
            if connection.features.empty_intersection_returns_none:
                self.assertIsNone(c.intersection)
            else:
                self.assertIs(c.intersection.empty, True)
            self.assertTrue(c.mpoly.sym_difference(geom).equals(c.sym_difference))
            self.assertTrue(c.mpoly.union(geom).equals(c.union))

    @skipUnlessDBFeature("has_Union_function")
    def test_union(self):
        """Union with all combinations of geometries/geometry fields."""
        geom = Point(-95.363151, 29.763374, srid=4326)

        union = City.objects.annotate(union=functions.Union('point', geom)).get(name='Dallas').union
        expected = fromstr('MULTIPOINT(-96.801611 32.782057,-95.363151 29.763374)', srid=4326)
        self.assertTrue(expected.equals(union))

        union = City.objects.annotate(union=functions.Union(geom, 'point')).get(name='Dallas').union
        self.assertTrue(expected.equals(union))

        union = City.objects.annotate(union=functions.Union('point', 'point')).get(name='Dallas').union
        expected = GEOSGeometry('POINT(-96.801611 32.782057)', srid=4326)
        self.assertTrue(expected.equals(union))

        union = City.objects.annotate(union=functions.Union(geom, geom)).get(name='Dallas').union
        self.assertTrue(geom.equals(union))

    @skipUnlessDBFeature("has_Union_function", "has_Transform_function")
    def test_union_mixed_srid(self):
        """The result SRID depends on the order of parameters."""
        geom = Point(61.42915, 55.15402, srid=4326)
        geom_3857 = geom.transform(3857, clone=True)
        tol = 0.001

        for city in City.objects.annotate(union=functions.Union('point', geom_3857)):
            expected = city.point | geom
            self.assertTrue(city.union.equals_exact(expected, tol))
            self.assertEqual(city.union.srid, 4326)

        for city in City.objects.annotate(union=functions.Union(geom_3857, 'point')):
            expected = geom_3857 | city.point.transform(3857, clone=True)
            self.assertTrue(expected.equals_exact(city.union, tol))
            self.assertEqual(city.union.srid, 3857)

    def test_argument_validation(self):
        with self.assertRaisesMessage(ValueError, 'SRID is required for all geometries.'):
            City.objects.annotate(geo=functions.GeoFunc(Point(1, 1)))

        msg = 'GeoFunc function requires a GeometryField in position 1, got CharField.'
        with self.assertRaisesMessage(TypeError, msg):
            City.objects.annotate(geo=functions.GeoFunc('name'))

        msg = 'GeoFunc function requires a geometric argument in position 1.'
        with self.assertRaisesMessage(TypeError, msg):
            City.objects.annotate(union=functions.GeoFunc(1, 'point')).get(name='Dallas')
