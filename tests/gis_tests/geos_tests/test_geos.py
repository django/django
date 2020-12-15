import ctypes
import itertools
import json
import pickle
import random
from binascii import a2b_hex
from io import BytesIO
from unittest import mock, skipIf

from django.contrib.gis import gdal
from django.contrib.gis.geos import (
    GeometryCollection, GEOSException, GEOSGeometry, LinearRing, LineString,
    MultiLineString, MultiPoint, MultiPolygon, Point, Polygon, fromfile,
    fromstr,
)
from django.contrib.gis.geos.libgeos import geos_version_tuple
from django.contrib.gis.shortcuts import numpy
from django.template import Context
from django.template.engine import Engine
from django.test import SimpleTestCase

from ..test_data import TestDataMixin


class GEOSTest(SimpleTestCase, TestDataMixin):

    def test_wkt(self):
        "Testing WKT output."
        for g in self.geometries.wkt_out:
            geom = fromstr(g.wkt)
            if geom.hasz:
                self.assertEqual(g.ewkt, geom.wkt)

    def test_hex(self):
        "Testing HEX output."
        for g in self.geometries.hex_wkt:
            geom = fromstr(g.wkt)
            self.assertEqual(g.hex, geom.hex.decode())

    def test_hexewkb(self):
        "Testing (HEX)EWKB output."
        # For testing HEX(EWKB).
        ogc_hex = b'01010000000000000000000000000000000000F03F'
        ogc_hex_3d = b'01010000800000000000000000000000000000F03F0000000000000040'
        # `SELECT ST_AsHEXEWKB(ST_GeomFromText('POINT(0 1)', 4326));`
        hexewkb_2d = b'0101000020E61000000000000000000000000000000000F03F'
        # `SELECT ST_AsHEXEWKB(ST_GeomFromEWKT('SRID=4326;POINT(0 1 2)'));`
        hexewkb_3d = b'01010000A0E61000000000000000000000000000000000F03F0000000000000040'

        pnt_2d = Point(0, 1, srid=4326)
        pnt_3d = Point(0, 1, 2, srid=4326)

        # OGC-compliant HEX will not have SRID value.
        self.assertEqual(ogc_hex, pnt_2d.hex)
        self.assertEqual(ogc_hex_3d, pnt_3d.hex)

        # HEXEWKB should be appropriate for its dimension -- have to use an
        # a WKBWriter w/dimension set accordingly, else GEOS will insert
        # garbage into 3D coordinate if there is none.
        self.assertEqual(hexewkb_2d, pnt_2d.hexewkb)
        self.assertEqual(hexewkb_3d, pnt_3d.hexewkb)
        self.assertIs(GEOSGeometry(hexewkb_3d).hasz, True)

        # Same for EWKB.
        self.assertEqual(memoryview(a2b_hex(hexewkb_2d)), pnt_2d.ewkb)
        self.assertEqual(memoryview(a2b_hex(hexewkb_3d)), pnt_3d.ewkb)

        # Redundant sanity check.
        self.assertEqual(4326, GEOSGeometry(hexewkb_2d).srid)

    def test_kml(self):
        "Testing KML output."
        for tg in self.geometries.wkt_out:
            geom = fromstr(tg.wkt)
            kml = getattr(tg, 'kml', False)
            if kml:
                self.assertEqual(kml, geom.kml)

    def test_errors(self):
        "Testing the Error handlers."
        # string-based
        for err in self.geometries.errors:
            with self.assertRaises((GEOSException, ValueError)):
                fromstr(err.wkt)

        # Bad WKB
        with self.assertRaises(GEOSException):
            GEOSGeometry(memoryview(b'0'))

        class NotAGeometry:
            pass

        # Some other object
        with self.assertRaises(TypeError):
            GEOSGeometry(NotAGeometry())
        # None
        with self.assertRaises(TypeError):
            GEOSGeometry(None)

    def test_wkb(self):
        "Testing WKB output."
        for g in self.geometries.hex_wkt:
            geom = fromstr(g.wkt)
            wkb = geom.wkb
            self.assertEqual(wkb.hex().upper(), g.hex)

    def test_create_hex(self):
        "Testing creation from HEX."
        for g in self.geometries.hex_wkt:
            geom_h = GEOSGeometry(g.hex)
            # we need to do this so decimal places get normalized
            geom_t = fromstr(g.wkt)
            self.assertEqual(geom_t.wkt, geom_h.wkt)

    def test_create_wkb(self):
        "Testing creation from WKB."
        for g in self.geometries.hex_wkt:
            wkb = memoryview(bytes.fromhex(g.hex))
            geom_h = GEOSGeometry(wkb)
            # we need to do this so decimal places get normalized
            geom_t = fromstr(g.wkt)
            self.assertEqual(geom_t.wkt, geom_h.wkt)

    def test_ewkt(self):
        "Testing EWKT."
        srids = (-1, 32140)
        for srid in srids:
            for p in self.geometries.polygons:
                ewkt = 'SRID=%d;%s' % (srid, p.wkt)
                poly = fromstr(ewkt)
                self.assertEqual(srid, poly.srid)
                self.assertEqual(srid, poly.shell.srid)
                self.assertEqual(srid, fromstr(poly.ewkt).srid)  # Checking export

    def test_json(self):
        "Testing GeoJSON input/output (via GDAL)."
        for g in self.geometries.json_geoms:
            geom = GEOSGeometry(g.wkt)
            if not hasattr(g, 'not_equal'):
                # Loading jsons to prevent decimal differences
                self.assertEqual(json.loads(g.json), json.loads(geom.json))
                self.assertEqual(json.loads(g.json), json.loads(geom.geojson))
            self.assertEqual(GEOSGeometry(g.wkt, 4326), GEOSGeometry(geom.json))

    def test_json_srid(self):
        geojson_data = {
            "type": "Point",
            "coordinates": [2, 49],
            "crs": {
                "type": "name",
                "properties": {
                    "name": "urn:ogc:def:crs:EPSG::4322"
                }
            }
        }
        self.assertEqual(GEOSGeometry(json.dumps(geojson_data)), Point(2, 49, srid=4322))

    def test_fromfile(self):
        "Testing the fromfile() factory."
        ref_pnt = GEOSGeometry('POINT(5 23)')

        wkt_f = BytesIO()
        wkt_f.write(ref_pnt.wkt.encode())
        wkb_f = BytesIO()
        wkb_f.write(bytes(ref_pnt.wkb))

        # Other tests use `fromfile()` on string filenames so those
        # aren't tested here.
        for fh in (wkt_f, wkb_f):
            fh.seek(0)
            pnt = fromfile(fh)
            self.assertEqual(ref_pnt, pnt)

    def test_eq(self):
        "Testing equivalence."
        p = fromstr('POINT(5 23)')
        self.assertEqual(p, p.wkt)
        self.assertNotEqual(p, 'foo')
        ls = fromstr('LINESTRING(0 0, 1 1, 5 5)')
        self.assertEqual(ls, ls.wkt)
        self.assertNotEqual(p, 'bar')
        self.assertEqual(p, 'POINT(5.0 23.0)')
        # Error shouldn't be raise on equivalence testing with
        # an invalid type.
        for g in (p, ls):
            self.assertIsNotNone(g)
            self.assertNotEqual(g, {'foo': 'bar'})
            self.assertIsNot(g, False)

    def test_hash(self):
        point_1 = Point(5, 23)
        point_2 = Point(5, 23, srid=4326)
        point_3 = Point(5, 23, srid=32632)
        multipoint_1 = MultiPoint(point_1, srid=4326)
        multipoint_2 = MultiPoint(point_2)
        multipoint_3 = MultiPoint(point_3)
        self.assertNotEqual(hash(point_1), hash(point_2))
        self.assertNotEqual(hash(point_1), hash(point_3))
        self.assertNotEqual(hash(point_2), hash(point_3))
        self.assertNotEqual(hash(multipoint_1), hash(multipoint_2))
        self.assertEqual(hash(multipoint_2), hash(multipoint_3))
        self.assertNotEqual(hash(multipoint_1), hash(point_1))
        self.assertNotEqual(hash(multipoint_2), hash(point_2))
        self.assertNotEqual(hash(multipoint_3), hash(point_3))

    def test_eq_with_srid(self):
        "Testing non-equivalence with different srids."
        p0 = Point(5, 23)
        p1 = Point(5, 23, srid=4326)
        p2 = Point(5, 23, srid=32632)
        # GEOS
        self.assertNotEqual(p0, p1)
        self.assertNotEqual(p1, p2)
        # EWKT
        self.assertNotEqual(p0, p1.ewkt)
        self.assertNotEqual(p1, p0.ewkt)
        self.assertNotEqual(p1, p2.ewkt)
        # Equivalence with matching SRIDs
        self.assertEqual(p2, p2)
        self.assertEqual(p2, p2.ewkt)
        # WKT contains no SRID so will not equal
        self.assertNotEqual(p2, p2.wkt)
        # SRID of 0
        self.assertEqual(p0, 'SRID=0;POINT (5 23)')
        self.assertNotEqual(p1, 'SRID=0;POINT (5 23)')

    def test_points(self):
        "Testing Point objects."
        prev = fromstr('POINT(0 0)')
        for p in self.geometries.points:
            # Creating the point from the WKT
            pnt = fromstr(p.wkt)
            self.assertEqual(pnt.geom_type, 'Point')
            self.assertEqual(pnt.geom_typeid, 0)
            self.assertEqual(pnt.dims, 0)
            self.assertEqual(p.x, pnt.x)
            self.assertEqual(p.y, pnt.y)
            self.assertEqual(pnt, fromstr(p.wkt))
            self.assertIs(pnt == prev, False)  # Use assertIs() to test __eq__.

            # Making sure that the point's X, Y components are what we expect
            self.assertAlmostEqual(p.x, pnt.tuple[0], 9)
            self.assertAlmostEqual(p.y, pnt.tuple[1], 9)

            # Testing the third dimension, and getting the tuple arguments
            if hasattr(p, 'z'):
                self.assertIs(pnt.hasz, True)
                self.assertEqual(p.z, pnt.z)
                self.assertEqual(p.z, pnt.tuple[2], 9)
                tup_args = (p.x, p.y, p.z)
                set_tup1 = (2.71, 3.14, 5.23)
                set_tup2 = (5.23, 2.71, 3.14)
            else:
                self.assertIs(pnt.hasz, False)
                self.assertIsNone(pnt.z)
                tup_args = (p.x, p.y)
                set_tup1 = (2.71, 3.14)
                set_tup2 = (3.14, 2.71)

            # Centroid operation on point should be point itself
            self.assertEqual(p.centroid, pnt.centroid.tuple)

            # Now testing the different constructors
            pnt2 = Point(tup_args)  # e.g., Point((1, 2))
            pnt3 = Point(*tup_args)  # e.g., Point(1, 2)
            self.assertEqual(pnt, pnt2)
            self.assertEqual(pnt, pnt3)

            # Now testing setting the x and y
            pnt.y = 3.14
            pnt.x = 2.71
            self.assertEqual(3.14, pnt.y)
            self.assertEqual(2.71, pnt.x)

            # Setting via the tuple/coords property
            pnt.tuple = set_tup1
            self.assertEqual(set_tup1, pnt.tuple)
            pnt.coords = set_tup2
            self.assertEqual(set_tup2, pnt.coords)

            prev = pnt  # setting the previous geometry

    def test_point_reverse(self):
        point = GEOSGeometry('POINT(144.963 -37.8143)', 4326)
        self.assertEqual(point.srid, 4326)
        point.reverse()
        self.assertEqual(point.ewkt, 'SRID=4326;POINT (-37.8143 144.963)')

    def test_multipoints(self):
        "Testing MultiPoint objects."
        for mp in self.geometries.multipoints:
            mpnt = fromstr(mp.wkt)
            self.assertEqual(mpnt.geom_type, 'MultiPoint')
            self.assertEqual(mpnt.geom_typeid, 4)
            self.assertEqual(mpnt.dims, 0)

            self.assertAlmostEqual(mp.centroid[0], mpnt.centroid.tuple[0], 9)
            self.assertAlmostEqual(mp.centroid[1], mpnt.centroid.tuple[1], 9)

            with self.assertRaises(IndexError):
                mpnt.__getitem__(len(mpnt))
            self.assertEqual(mp.centroid, mpnt.centroid.tuple)
            self.assertEqual(mp.coords, tuple(m.tuple for m in mpnt))
            for p in mpnt:
                self.assertEqual(p.geom_type, 'Point')
                self.assertEqual(p.geom_typeid, 0)
                self.assertIs(p.empty, False)
                self.assertIs(p.valid, True)

    def test_linestring(self):
        "Testing LineString objects."
        prev = fromstr('POINT(0 0)')
        for line in self.geometries.linestrings:
            ls = fromstr(line.wkt)
            self.assertEqual(ls.geom_type, 'LineString')
            self.assertEqual(ls.geom_typeid, 1)
            self.assertEqual(ls.dims, 1)
            self.assertIs(ls.empty, False)
            self.assertIs(ls.ring, False)
            if hasattr(line, 'centroid'):
                self.assertEqual(line.centroid, ls.centroid.tuple)
            if hasattr(line, 'tup'):
                self.assertEqual(line.tup, ls.tuple)

            self.assertEqual(ls, fromstr(line.wkt))
            self.assertIs(ls == prev, False)  # Use assertIs() to test __eq__.
            with self.assertRaises(IndexError):
                ls.__getitem__(len(ls))
            prev = ls

            # Creating a LineString from a tuple, list, and numpy array
            self.assertEqual(ls, LineString(ls.tuple))  # tuple
            self.assertEqual(ls, LineString(*ls.tuple))  # as individual arguments
            self.assertEqual(ls, LineString([list(tup) for tup in ls.tuple]))  # as list
            # Point individual arguments
            self.assertEqual(ls.wkt, LineString(*tuple(Point(tup) for tup in ls.tuple)).wkt)
            if numpy:
                self.assertEqual(ls, LineString(numpy.array(ls.tuple)))  # as numpy array

        with self.assertRaisesMessage(TypeError, 'Each coordinate should be a sequence (list or tuple)'):
            LineString((0, 0))

        with self.assertRaisesMessage(ValueError, 'LineString requires at least 2 points, got 1.'):
            LineString([(0, 0)])

        if numpy:
            with self.assertRaisesMessage(ValueError, 'LineString requires at least 2 points, got 1.'):
                LineString(numpy.array([(0, 0)]))

        with mock.patch('django.contrib.gis.geos.linestring.numpy', False):
            with self.assertRaisesMessage(TypeError, 'Invalid initialization input for LineStrings.'):
                LineString('wrong input')

        # Test __iter__().
        self.assertEqual(list(LineString((0, 0), (1, 1), (2, 2))), [(0, 0), (1, 1), (2, 2)])

    def test_linestring_reverse(self):
        line = GEOSGeometry('LINESTRING(144.963 -37.8143,151.2607 -33.887)', 4326)
        self.assertEqual(line.srid, 4326)
        line.reverse()
        self.assertEqual(line.ewkt, 'SRID=4326;LINESTRING (151.2607 -33.887, 144.963 -37.8143)')

    def _test_is_counterclockwise(self):
        lr = LinearRing((0, 0), (1, 0), (0, 1), (0, 0))
        self.assertIs(lr.is_counterclockwise, True)
        lr.reverse()
        self.assertIs(lr.is_counterclockwise, False)
        msg = 'Orientation of an empty LinearRing cannot be determined.'
        with self.assertRaisesMessage(ValueError, msg):
            LinearRing().is_counterclockwise

    @skipIf(geos_version_tuple() < (3, 7), 'GEOS >= 3.7.0 is required')
    def test_is_counterclockwise(self):
        self._test_is_counterclockwise()

    @skipIf(geos_version_tuple() < (3, 7), 'GEOS >= 3.7.0 is required')
    def test_is_counterclockwise_geos_error(self):
        with mock.patch('django.contrib.gis.geos.prototypes.cs_is_ccw') as mocked:
            mocked.return_value = 0
            mocked.func_name = 'GEOSCoordSeq_isCCW'
            msg = 'Error encountered in GEOS C function "GEOSCoordSeq_isCCW".'
            with self.assertRaisesMessage(GEOSException, msg):
                LinearRing((0, 0), (1, 0), (0, 1), (0, 0)).is_counterclockwise

    @mock.patch('django.contrib.gis.geos.libgeos.geos_version', lambda: b'3.6.9')
    def test_is_counterclockwise_fallback(self):
        self._test_is_counterclockwise()

    def test_multilinestring(self):
        "Testing MultiLineString objects."
        prev = fromstr('POINT(0 0)')
        for line in self.geometries.multilinestrings:
            ml = fromstr(line.wkt)
            self.assertEqual(ml.geom_type, 'MultiLineString')
            self.assertEqual(ml.geom_typeid, 5)
            self.assertEqual(ml.dims, 1)

            self.assertAlmostEqual(line.centroid[0], ml.centroid.x, 9)
            self.assertAlmostEqual(line.centroid[1], ml.centroid.y, 9)

            self.assertEqual(ml, fromstr(line.wkt))
            self.assertIs(ml == prev, False)  # Use assertIs() to test __eq__.
            prev = ml

            for ls in ml:
                self.assertEqual(ls.geom_type, 'LineString')
                self.assertEqual(ls.geom_typeid, 1)
                self.assertIs(ls.empty, False)

            with self.assertRaises(IndexError):
                ml.__getitem__(len(ml))
            self.assertEqual(ml.wkt, MultiLineString(*tuple(s.clone() for s in ml)).wkt)
            self.assertEqual(ml, MultiLineString(*tuple(LineString(s.tuple) for s in ml)))

    def test_linearring(self):
        "Testing LinearRing objects."
        for rr in self.geometries.linearrings:
            lr = fromstr(rr.wkt)
            self.assertEqual(lr.geom_type, 'LinearRing')
            self.assertEqual(lr.geom_typeid, 2)
            self.assertEqual(lr.dims, 1)
            self.assertEqual(rr.n_p, len(lr))
            self.assertIs(lr.valid, True)
            self.assertIs(lr.empty, False)

            # Creating a LinearRing from a tuple, list, and numpy array
            self.assertEqual(lr, LinearRing(lr.tuple))
            self.assertEqual(lr, LinearRing(*lr.tuple))
            self.assertEqual(lr, LinearRing([list(tup) for tup in lr.tuple]))
            if numpy:
                self.assertEqual(lr, LinearRing(numpy.array(lr.tuple)))

        with self.assertRaisesMessage(ValueError, 'LinearRing requires at least 4 points, got 3.'):
            LinearRing((0, 0), (1, 1), (0, 0))

        with self.assertRaisesMessage(ValueError, 'LinearRing requires at least 4 points, got 1.'):
            LinearRing([(0, 0)])

        if numpy:
            with self.assertRaisesMessage(ValueError, 'LinearRing requires at least 4 points, got 1.'):
                LinearRing(numpy.array([(0, 0)]))

    def test_linearring_json(self):
        self.assertJSONEqual(
            LinearRing((0, 0), (0, 1), (1, 1), (0, 0)).json,
            '{"coordinates": [[0, 0], [0, 1], [1, 1], [0, 0]], "type": "LineString"}',
        )

    def test_polygons_from_bbox(self):
        "Testing `from_bbox` class method."
        bbox = (-180, -90, 180, 90)
        p = Polygon.from_bbox(bbox)
        self.assertEqual(bbox, p.extent)

        # Testing numerical precision
        x = 3.14159265358979323
        bbox = (0, 0, 1, x)
        p = Polygon.from_bbox(bbox)
        y = p.extent[-1]
        self.assertEqual(format(x, '.13f'), format(y, '.13f'))

    def test_polygons(self):
        "Testing Polygon objects."

        prev = fromstr('POINT(0 0)')
        for p in self.geometries.polygons:
            # Creating the Polygon, testing its properties.
            poly = fromstr(p.wkt)
            self.assertEqual(poly.geom_type, 'Polygon')
            self.assertEqual(poly.geom_typeid, 3)
            self.assertEqual(poly.dims, 2)
            self.assertIs(poly.empty, False)
            self.assertIs(poly.ring, False)
            self.assertEqual(p.n_i, poly.num_interior_rings)
            self.assertEqual(p.n_i + 1, len(poly))  # Testing __len__
            self.assertEqual(p.n_p, poly.num_points)

            # Area & Centroid
            self.assertAlmostEqual(p.area, poly.area, 9)
            self.assertAlmostEqual(p.centroid[0], poly.centroid.tuple[0], 9)
            self.assertAlmostEqual(p.centroid[1], poly.centroid.tuple[1], 9)

            # Testing the geometry equivalence
            self.assertEqual(poly, fromstr(p.wkt))
            # Should not be equal to previous geometry
            self.assertIs(poly == prev, False)  # Use assertIs() to test __eq__.
            self.assertIs(poly != prev, True)  # Use assertIs() to test __ne__.

            # Testing the exterior ring
            ring = poly.exterior_ring
            self.assertEqual(ring.geom_type, 'LinearRing')
            self.assertEqual(ring.geom_typeid, 2)
            if p.ext_ring_cs:
                self.assertEqual(p.ext_ring_cs, ring.tuple)
                self.assertEqual(p.ext_ring_cs, poly[0].tuple)  # Testing __getitem__

            # Testing __getitem__ and __setitem__ on invalid indices
            with self.assertRaises(IndexError):
                poly.__getitem__(len(poly))
            with self.assertRaises(IndexError):
                poly.__setitem__(len(poly), False)
            with self.assertRaises(IndexError):
                poly.__getitem__(-1 * len(poly) - 1)

            # Testing __iter__
            for r in poly:
                self.assertEqual(r.geom_type, 'LinearRing')
                self.assertEqual(r.geom_typeid, 2)

            # Testing polygon construction.
            with self.assertRaises(TypeError):
                Polygon(0, [1, 2, 3])
            with self.assertRaises(TypeError):
                Polygon('foo')

            # Polygon(shell, (hole1, ... holeN))
            ext_ring, *int_rings = poly
            self.assertEqual(poly, Polygon(ext_ring, int_rings))

            # Polygon(shell_tuple, hole_tuple1, ... , hole_tupleN)
            ring_tuples = tuple(r.tuple for r in poly)
            self.assertEqual(poly, Polygon(*ring_tuples))

            # Constructing with tuples of LinearRings.
            self.assertEqual(poly.wkt, Polygon(*tuple(r for r in poly)).wkt)
            self.assertEqual(poly.wkt, Polygon(*tuple(LinearRing(r.tuple) for r in poly)).wkt)

    def test_polygons_templates(self):
        # Accessing Polygon attributes in templates should work.
        engine = Engine()
        template = engine.from_string('{{ polygons.0.wkt }}')
        polygons = [fromstr(p.wkt) for p in self.geometries.multipolygons[:2]]
        content = template.render(Context({'polygons': polygons}))
        self.assertIn('MULTIPOLYGON (((100', content)

    def test_polygon_comparison(self):
        p1 = Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        p2 = Polygon(((0, 0), (0, 1), (1, 0), (0, 0)))
        self.assertGreater(p1, p2)
        self.assertLess(p2, p1)

        p3 = Polygon(((0, 0), (0, 1), (1, 1), (2, 0), (0, 0)))
        p4 = Polygon(((0, 0), (0, 1), (2, 2), (1, 0), (0, 0)))
        self.assertGreater(p4, p3)
        self.assertLess(p3, p4)

    def test_multipolygons(self):
        "Testing MultiPolygon objects."
        fromstr('POINT (0 0)')
        for mp in self.geometries.multipolygons:
            mpoly = fromstr(mp.wkt)
            self.assertEqual(mpoly.geom_type, 'MultiPolygon')
            self.assertEqual(mpoly.geom_typeid, 6)
            self.assertEqual(mpoly.dims, 2)
            self.assertEqual(mp.valid, mpoly.valid)

            if mp.valid:
                self.assertEqual(mp.num_geom, mpoly.num_geom)
                self.assertEqual(mp.n_p, mpoly.num_coords)
                self.assertEqual(mp.num_geom, len(mpoly))
                with self.assertRaises(IndexError):
                    mpoly.__getitem__(len(mpoly))
                for p in mpoly:
                    self.assertEqual(p.geom_type, 'Polygon')
                    self.assertEqual(p.geom_typeid, 3)
                    self.assertIs(p.valid, True)
                self.assertEqual(mpoly.wkt, MultiPolygon(*tuple(poly.clone() for poly in mpoly)).wkt)

    def test_memory_hijinks(self):
        "Testing Geometry __del__() on rings and polygons."
        # #### Memory issues with rings and poly

        # These tests are needed to ensure sanity with writable geometries.

        # Getting a polygon with interior rings, and pulling out the interior rings
        poly = fromstr(self.geometries.polygons[1].wkt)
        ring1 = poly[0]
        ring2 = poly[1]

        # These deletes should be 'harmless' since they are done on child geometries
        del ring1
        del ring2
        ring1 = poly[0]
        ring2 = poly[1]

        # Deleting the polygon
        del poly

        # Access to these rings is OK since they are clones.
        str(ring1)
        str(ring2)

    def test_coord_seq(self):
        "Testing Coordinate Sequence objects."
        for p in self.geometries.polygons:
            if p.ext_ring_cs:
                # Constructing the polygon and getting the coordinate sequence
                poly = fromstr(p.wkt)
                cs = poly.exterior_ring.coord_seq

                self.assertEqual(p.ext_ring_cs, cs.tuple)  # done in the Polygon test too.
                self.assertEqual(len(p.ext_ring_cs), len(cs))  # Making sure __len__ works

                # Checks __getitem__ and __setitem__
                for i in range(len(p.ext_ring_cs)):
                    c1 = p.ext_ring_cs[i]  # Expected value
                    c2 = cs[i]  # Value from coordseq
                    self.assertEqual(c1, c2)

                    # Constructing the test value to set the coordinate sequence with
                    if len(c1) == 2:
                        tset = (5, 23)
                    else:
                        tset = (5, 23, 8)
                    cs[i] = tset

                    # Making sure every set point matches what we expect
                    for j in range(len(tset)):
                        cs[i] = tset
                        self.assertEqual(tset[j], cs[i][j])

    def test_relate_pattern(self):
        "Testing relate() and relate_pattern()."
        g = fromstr('POINT (0 0)')
        with self.assertRaises(GEOSException):
            g.relate_pattern(0, 'invalid pattern, yo')
        for rg in self.geometries.relate_geoms:
            a = fromstr(rg.wkt_a)
            b = fromstr(rg.wkt_b)
            self.assertEqual(rg.result, a.relate_pattern(b, rg.pattern))
            self.assertEqual(rg.pattern, a.relate(b))

    def test_intersection(self):
        "Testing intersects() and intersection()."
        for i in range(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            i1 = fromstr(self.geometries.intersect_geoms[i].wkt)
            self.assertIs(a.intersects(b), True)
            i2 = a.intersection(b)
            self.assertEqual(i1, i2)
            self.assertEqual(i1, a & b)  # __and__ is intersection operator
            a &= b  # testing __iand__
            self.assertEqual(i1, a)

    def test_union(self):
        "Testing union()."
        for i in range(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            u1 = fromstr(self.geometries.union_geoms[i].wkt)
            u2 = a.union(b)
            self.assertEqual(u1, u2)
            self.assertEqual(u1, a | b)  # __or__ is union operator
            a |= b  # testing __ior__
            self.assertEqual(u1, a)

    def test_unary_union(self):
        "Testing unary_union."
        for i in range(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            u1 = fromstr(self.geometries.union_geoms[i].wkt)
            u2 = GeometryCollection(a, b).unary_union
            self.assertTrue(u1.equals(u2))

    def test_difference(self):
        "Testing difference()."
        for i in range(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            d1 = fromstr(self.geometries.diff_geoms[i].wkt)
            d2 = a.difference(b)
            self.assertEqual(d1, d2)
            self.assertEqual(d1, a - b)  # __sub__ is difference operator
            a -= b  # testing __isub__
            self.assertEqual(d1, a)

    def test_symdifference(self):
        "Testing sym_difference()."
        for i in range(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            d1 = fromstr(self.geometries.sdiff_geoms[i].wkt)
            d2 = a.sym_difference(b)
            self.assertEqual(d1, d2)
            self.assertEqual(d1, a ^ b)  # __xor__ is symmetric difference operator
            a ^= b  # testing __ixor__
            self.assertEqual(d1, a)

    def test_buffer(self):
        bg = self.geometries.buffer_geoms[0]
        g = fromstr(bg.wkt)

        # Can't use a floating-point for the number of quadsegs.
        with self.assertRaises(ctypes.ArgumentError):
            g.buffer(bg.width, quadsegs=1.1)

        self._test_buffer(self.geometries.buffer_geoms, 'buffer')

    def test_buffer_with_style(self):
        bg = self.geometries.buffer_with_style_geoms[0]
        g = fromstr(bg.wkt)

        # Can't use a floating-point for the number of quadsegs.
        with self.assertRaises(ctypes.ArgumentError):
            g.buffer_with_style(bg.width, quadsegs=1.1)

        # Can't use a floating-point for the end cap style.
        with self.assertRaises(ctypes.ArgumentError):
            g.buffer_with_style(bg.width, end_cap_style=1.2)
        # Can't use a end cap style that is not in the enum.
        with self.assertRaises(GEOSException):
            g.buffer_with_style(bg.width, end_cap_style=55)

        # Can't use a floating-point for the join style.
        with self.assertRaises(ctypes.ArgumentError):
            g.buffer_with_style(bg.width, join_style=1.3)
        # Can't use a join style that is not in the enum.
        with self.assertRaises(GEOSException):
            g.buffer_with_style(bg.width, join_style=66)

        self._test_buffer(
            itertools.chain(self.geometries.buffer_geoms, self.geometries.buffer_with_style_geoms),
            'buffer_with_style',
        )

    def _test_buffer(self, geometries, buffer_method_name):
        for bg in geometries:
            g = fromstr(bg.wkt)

            # The buffer we expect
            exp_buf = fromstr(bg.buffer_wkt)

            # Constructing our buffer
            buf_kwargs = {
                kwarg_name: getattr(bg, kwarg_name)
                for kwarg_name in ('width', 'quadsegs', 'end_cap_style', 'join_style', 'mitre_limit')
                if hasattr(bg, kwarg_name)
            }
            buf = getattr(g, buffer_method_name)(**buf_kwargs)
            self.assertEqual(exp_buf.num_coords, buf.num_coords)
            self.assertEqual(len(exp_buf), len(buf))

            # Now assuring that each point in the buffer is almost equal
            for j in range(len(exp_buf)):
                exp_ring = exp_buf[j]
                buf_ring = buf[j]
                self.assertEqual(len(exp_ring), len(buf_ring))
                for k in range(len(exp_ring)):
                    # Asserting the X, Y of each point are almost equal (due to floating point imprecision)
                    self.assertAlmostEqual(exp_ring[k][0], buf_ring[k][0], 9)
                    self.assertAlmostEqual(exp_ring[k][1], buf_ring[k][1], 9)

    def test_covers(self):
        poly = Polygon(((0, 0), (0, 10), (10, 10), (10, 0), (0, 0)))
        self.assertTrue(poly.covers(Point(5, 5)))
        self.assertFalse(poly.covers(Point(100, 100)))

    def test_closed(self):
        ls_closed = LineString((0, 0), (1, 1), (0, 0))
        ls_not_closed = LineString((0, 0), (1, 1))
        self.assertFalse(ls_not_closed.closed)
        self.assertTrue(ls_closed.closed)

    def test_srid(self):
        "Testing the SRID property and keyword."
        # Testing SRID keyword on Point
        pnt = Point(5, 23, srid=4326)
        self.assertEqual(4326, pnt.srid)
        pnt.srid = 3084
        self.assertEqual(3084, pnt.srid)
        with self.assertRaises(ctypes.ArgumentError):
            pnt.srid = '4326'

        # Testing SRID keyword on fromstr(), and on Polygon rings.
        poly = fromstr(self.geometries.polygons[1].wkt, srid=4269)
        self.assertEqual(4269, poly.srid)
        for ring in poly:
            self.assertEqual(4269, ring.srid)
        poly.srid = 4326
        self.assertEqual(4326, poly.shell.srid)

        # Testing SRID keyword on GeometryCollection
        gc = GeometryCollection(Point(5, 23), LineString((0, 0), (1.5, 1.5), (3, 3)), srid=32021)
        self.assertEqual(32021, gc.srid)
        for i in range(len(gc)):
            self.assertEqual(32021, gc[i].srid)

        # GEOS may get the SRID from HEXEWKB
        # 'POINT(5 23)' at SRID=4326 in hex form -- obtained from PostGIS
        # using `SELECT GeomFromText('POINT (5 23)', 4326);`.
        hex = '0101000020E610000000000000000014400000000000003740'
        p1 = fromstr(hex)
        self.assertEqual(4326, p1.srid)

        p2 = fromstr(p1.hex)
        self.assertIsNone(p2.srid)
        p3 = fromstr(p1.hex, srid=-1)  # -1 is intended.
        self.assertEqual(-1, p3.srid)

        # Testing that geometry SRID could be set to its own value
        pnt_wo_srid = Point(1, 1)
        pnt_wo_srid.srid = pnt_wo_srid.srid

        # Input geometries that have an SRID.
        self.assertEqual(GEOSGeometry(pnt.ewkt, srid=pnt.srid).srid, pnt.srid)
        self.assertEqual(GEOSGeometry(pnt.ewkb, srid=pnt.srid).srid, pnt.srid)
        with self.assertRaisesMessage(ValueError, 'Input geometry already has SRID: %d.' % pnt.srid):
            GEOSGeometry(pnt.ewkt, srid=1)
        with self.assertRaisesMessage(ValueError, 'Input geometry already has SRID: %d.' % pnt.srid):
            GEOSGeometry(pnt.ewkb, srid=1)

    def test_custom_srid(self):
        """Test with a null srid and a srid unknown to GDAL."""
        for srid in [None, 999999]:
            pnt = Point(111200, 220900, srid=srid)
            self.assertTrue(pnt.ewkt.startswith(("SRID=%s;" % srid if srid else '') + "POINT (111200"))
            self.assertIsInstance(pnt.ogr, gdal.OGRGeometry)
            self.assertIsNone(pnt.srs)

            # Test conversion from custom to a known srid
            c2w = gdal.CoordTransform(
                gdal.SpatialReference(
                    '+proj=mill +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +R_A +ellps=WGS84 '
                    '+datum=WGS84 +units=m +no_defs'
                ),
                gdal.SpatialReference(4326))
            new_pnt = pnt.transform(c2w, clone=True)
            self.assertEqual(new_pnt.srid, 4326)
            self.assertAlmostEqual(new_pnt.x, 1, 1)
            self.assertAlmostEqual(new_pnt.y, 2, 1)

    def test_mutable_geometries(self):
        "Testing the mutability of Polygons and Geometry Collections."
        # ### Testing the mutability of Polygons ###
        for p in self.geometries.polygons:
            poly = fromstr(p.wkt)

            # Should only be able to use __setitem__ with LinearRing geometries.
            with self.assertRaises(TypeError):
                poly.__setitem__(0, LineString((1, 1), (2, 2)))

            # Constructing the new shell by adding 500 to every point in the old shell.
            shell_tup = poly.shell.tuple
            new_coords = []
            for point in shell_tup:
                new_coords.append((point[0] + 500., point[1] + 500.))
            new_shell = LinearRing(*tuple(new_coords))

            # Assigning polygon's exterior ring w/the new shell
            poly.exterior_ring = new_shell
            str(new_shell)  # new shell is still accessible
            self.assertEqual(poly.exterior_ring, new_shell)
            self.assertEqual(poly[0], new_shell)

        # ### Testing the mutability of Geometry Collections
        for tg in self.geometries.multipoints:
            mp = fromstr(tg.wkt)
            for i in range(len(mp)):
                # Creating a random point.
                pnt = mp[i]
                new = Point(random.randint(21, 100), random.randint(21, 100))
                # Testing the assignment
                mp[i] = new
                str(new)  # what was used for the assignment is still accessible
                self.assertEqual(mp[i], new)
                self.assertEqual(mp[i].wkt, new.wkt)
                self.assertNotEqual(pnt, mp[i])

        # MultiPolygons involve much more memory management because each
        # Polygon w/in the collection has its own rings.
        for tg in self.geometries.multipolygons:
            mpoly = fromstr(tg.wkt)
            for i in range(len(mpoly)):
                poly = mpoly[i]
                old_poly = mpoly[i]
                # Offsetting the each ring in the polygon by 500.
                for j in range(len(poly)):
                    r = poly[j]
                    for k in range(len(r)):
                        r[k] = (r[k][0] + 500., r[k][1] + 500.)
                    poly[j] = r

                self.assertNotEqual(mpoly[i], poly)
                # Testing the assignment
                mpoly[i] = poly
                str(poly)  # Still accessible
                self.assertEqual(mpoly[i], poly)
                self.assertNotEqual(mpoly[i], old_poly)

        # Extreme (!!) __setitem__ -- no longer works, have to detect
        # in the first object that __setitem__ is called in the subsequent
        # objects -- maybe mpoly[0, 0, 0] = (3.14, 2.71)?
        # mpoly[0][0][0] = (3.14, 2.71)
        # self.assertEqual((3.14, 2.71), mpoly[0][0][0])
        # Doing it more slowly..
        # self.assertEqual((3.14, 2.71), mpoly[0].shell[0])
        # del mpoly

    def test_point_list_assignment(self):
        p = Point(0, 0)

        p[:] = (1, 2, 3)
        self.assertEqual(p, Point(1, 2, 3))

        p[:] = ()
        self.assertEqual(p.wkt, Point())

        p[:] = (1, 2)
        self.assertEqual(p.wkt, Point(1, 2))

        with self.assertRaises(ValueError):
            p[:] = (1,)
        with self.assertRaises(ValueError):
            p[:] = (1, 2, 3, 4, 5)

    def test_linestring_list_assignment(self):
        ls = LineString((0, 0), (1, 1))

        ls[:] = ()
        self.assertEqual(ls, LineString())

        ls[:] = ((0, 0), (1, 1), (2, 2))
        self.assertEqual(ls, LineString((0, 0), (1, 1), (2, 2)))

        with self.assertRaises(ValueError):
            ls[:] = (1,)

    def test_linearring_list_assignment(self):
        ls = LinearRing((0, 0), (0, 1), (1, 1), (0, 0))

        ls[:] = ()
        self.assertEqual(ls, LinearRing())

        ls[:] = ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))
        self.assertEqual(ls, LinearRing((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))

        with self.assertRaises(ValueError):
            ls[:] = ((0, 0), (1, 1), (2, 2))

    def test_polygon_list_assignment(self):
        pol = Polygon()

        pol[:] = (((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)),)
        self.assertEqual(pol, Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)),))

        pol[:] = ()
        self.assertEqual(pol, Polygon())

    def test_geometry_collection_list_assignment(self):
        p = Point()
        gc = GeometryCollection()

        gc[:] = [p]
        self.assertEqual(gc, GeometryCollection(p))

        gc[:] = ()
        self.assertEqual(gc, GeometryCollection())

    def test_threed(self):
        "Testing three-dimensional geometries."
        # Testing a 3D Point
        pnt = Point(2, 3, 8)
        self.assertEqual((2., 3., 8.), pnt.coords)
        with self.assertRaises(TypeError):
            pnt.tuple = (1., 2.)
        pnt.coords = (1., 2., 3.)
        self.assertEqual((1., 2., 3.), pnt.coords)

        # Testing a 3D LineString
        ls = LineString((2., 3., 8.), (50., 250., -117.))
        self.assertEqual(((2., 3., 8.), (50., 250., -117.)), ls.tuple)
        with self.assertRaises(TypeError):
            ls.__setitem__(0, (1., 2.))
        ls[0] = (1., 2., 3.)
        self.assertEqual((1., 2., 3.), ls[0])

    def test_distance(self):
        "Testing the distance() function."
        # Distance to self should be 0.
        pnt = Point(0, 0)
        self.assertEqual(0.0, pnt.distance(Point(0, 0)))

        # Distance should be 1
        self.assertEqual(1.0, pnt.distance(Point(0, 1)))

        # Distance should be ~ sqrt(2)
        self.assertAlmostEqual(1.41421356237, pnt.distance(Point(1, 1)), 11)

        # Distances are from the closest vertex in each geometry --
        #  should be 3 (distance from (2, 2) to (5, 2)).
        ls1 = LineString((0, 0), (1, 1), (2, 2))
        ls2 = LineString((5, 2), (6, 1), (7, 0))
        self.assertEqual(3, ls1.distance(ls2))

    def test_length(self):
        "Testing the length property."
        # Points have 0 length.
        pnt = Point(0, 0)
        self.assertEqual(0.0, pnt.length)

        # Should be ~ sqrt(2)
        ls = LineString((0, 0), (1, 1))
        self.assertAlmostEqual(1.41421356237, ls.length, 11)

        # Should be circumference of Polygon
        poly = Polygon(LinearRing((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        self.assertEqual(4.0, poly.length)

        # Should be sum of each element's length in collection.
        mpoly = MultiPolygon(poly.clone(), poly)
        self.assertEqual(8.0, mpoly.length)

    def test_emptyCollections(self):
        "Testing empty geometries and collections."
        geoms = [
            GeometryCollection([]),
            fromstr('GEOMETRYCOLLECTION EMPTY'),
            GeometryCollection(),
            fromstr('POINT EMPTY'),
            Point(),
            fromstr('LINESTRING EMPTY'),
            LineString(),
            fromstr('POLYGON EMPTY'),
            Polygon(),
            fromstr('MULTILINESTRING EMPTY'),
            MultiLineString(),
            fromstr('MULTIPOLYGON EMPTY'),
            MultiPolygon(()),
            MultiPolygon(),
        ]

        if numpy:
            geoms.append(LineString(numpy.array([])))

        for g in geoms:
            self.assertIs(g.empty, True)

            # Testing len() and num_geom.
            if isinstance(g, Polygon):
                self.assertEqual(1, len(g))  # Has one empty linear ring
                self.assertEqual(1, g.num_geom)
                self.assertEqual(0, len(g[0]))
            elif isinstance(g, (Point, LineString)):
                self.assertEqual(1, g.num_geom)
                self.assertEqual(0, len(g))
            else:
                self.assertEqual(0, g.num_geom)
                self.assertEqual(0, len(g))

            # Testing __getitem__ (doesn't work on Point or Polygon)
            if isinstance(g, Point):
                with self.assertRaises(IndexError):
                    g.x
            elif isinstance(g, Polygon):
                lr = g.shell
                self.assertEqual('LINEARRING EMPTY', lr.wkt)
                self.assertEqual(0, len(lr))
                self.assertIs(lr.empty, True)
                with self.assertRaises(IndexError):
                    lr.__getitem__(0)
            else:
                with self.assertRaises(IndexError):
                    g.__getitem__(0)

    def test_collection_dims(self):
        gc = GeometryCollection([])
        self.assertEqual(gc.dims, -1)

        gc = GeometryCollection(Point(0, 0))
        self.assertEqual(gc.dims, 0)

        gc = GeometryCollection(LineString((0, 0), (1, 1)), Point(0, 0))
        self.assertEqual(gc.dims, 1)

        gc = GeometryCollection(LineString((0, 0), (1, 1)), Polygon(((0, 0), (0, 1), (1, 1), (0, 0))), Point(0, 0))
        self.assertEqual(gc.dims, 2)

    def test_collections_of_collections(self):
        "Testing GeometryCollection handling of other collections."
        # Creating a GeometryCollection WKT string composed of other
        # collections and polygons.
        coll = [mp.wkt for mp in self.geometries.multipolygons if mp.valid]
        coll.extend(mls.wkt for mls in self.geometries.multilinestrings)
        coll.extend(p.wkt for p in self.geometries.polygons)
        coll.extend(mp.wkt for mp in self.geometries.multipoints)
        gc_wkt = 'GEOMETRYCOLLECTION(%s)' % ','.join(coll)

        # Should construct ok from WKT
        gc1 = GEOSGeometry(gc_wkt)

        # Should also construct ok from individual geometry arguments.
        gc2 = GeometryCollection(*tuple(g for g in gc1))

        # And, they should be equal.
        self.assertEqual(gc1, gc2)

    def test_gdal(self):
        "Testing `ogr` and `srs` properties."
        g1 = fromstr('POINT(5 23)')
        self.assertIsInstance(g1.ogr, gdal.OGRGeometry)
        self.assertIsNone(g1.srs)

        g1_3d = fromstr('POINT(5 23 8)')
        self.assertIsInstance(g1_3d.ogr, gdal.OGRGeometry)
        self.assertEqual(g1_3d.ogr.z, 8)

        g2 = fromstr('LINESTRING(0 0, 5 5, 23 23)', srid=4326)
        self.assertIsInstance(g2.ogr, gdal.OGRGeometry)
        self.assertIsInstance(g2.srs, gdal.SpatialReference)
        self.assertEqual(g2.hex, g2.ogr.hex)
        self.assertEqual('WGS 84', g2.srs.name)

    def test_copy(self):
        "Testing use with the Python `copy` module."
        import copy
        poly = GEOSGeometry('POLYGON((0 0, 0 23, 23 23, 23 0, 0 0), (5 5, 5 10, 10 10, 10 5, 5 5))')
        cpy1 = copy.copy(poly)
        cpy2 = copy.deepcopy(poly)
        self.assertNotEqual(poly._ptr, cpy1._ptr)
        self.assertNotEqual(poly._ptr, cpy2._ptr)

    def test_transform(self):
        "Testing `transform` method."
        orig = GEOSGeometry('POINT (-104.609 38.255)', 4326)
        trans = GEOSGeometry('POINT (992385.4472045 481455.4944650)', 2774)

        # Using a srid, a SpatialReference object, and a CoordTransform object
        # for transformations.
        t1, t2, t3 = orig.clone(), orig.clone(), orig.clone()
        t1.transform(trans.srid)
        t2.transform(gdal.SpatialReference('EPSG:2774'))
        ct = gdal.CoordTransform(gdal.SpatialReference('WGS84'), gdal.SpatialReference(2774))
        t3.transform(ct)

        # Testing use of the `clone` keyword.
        k1 = orig.clone()
        k2 = k1.transform(trans.srid, clone=True)
        self.assertEqual(k1, orig)
        self.assertNotEqual(k1, k2)

        prec = 3
        for p in (t1, t2, t3, k2):
            self.assertAlmostEqual(trans.x, p.x, prec)
            self.assertAlmostEqual(trans.y, p.y, prec)

    def test_transform_3d(self):
        p3d = GEOSGeometry('POINT (5 23 100)', 4326)
        p3d.transform(2774)
        self.assertAlmostEqual(p3d.z, 100, 3)

    def test_transform_noop(self):
        """ Testing `transform` method (SRID match) """
        # transform() should no-op if source & dest SRIDs match,
        # regardless of whether GDAL is available.
        g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
        gt = g.tuple
        g.transform(4326)
        self.assertEqual(g.tuple, gt)
        self.assertEqual(g.srid, 4326)

        g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
        g1 = g.transform(4326, clone=True)
        self.assertEqual(g1.tuple, g.tuple)
        self.assertEqual(g1.srid, 4326)
        self.assertIsNot(g1, g, "Clone didn't happen")

    def test_transform_nosrid(self):
        """ Testing `transform` method (no SRID or negative SRID) """

        g = GEOSGeometry('POINT (-104.609 38.255)', srid=None)
        with self.assertRaises(GEOSException):
            g.transform(2774)

        g = GEOSGeometry('POINT (-104.609 38.255)', srid=None)
        with self.assertRaises(GEOSException):
            g.transform(2774, clone=True)

        g = GEOSGeometry('POINT (-104.609 38.255)', srid=-1)
        with self.assertRaises(GEOSException):
            g.transform(2774)

        g = GEOSGeometry('POINT (-104.609 38.255)', srid=-1)
        with self.assertRaises(GEOSException):
            g.transform(2774, clone=True)

    def test_extent(self):
        "Testing `extent` method."
        # The xmin, ymin, xmax, ymax of the MultiPoint should be returned.
        mp = MultiPoint(Point(5, 23), Point(0, 0), Point(10, 50))
        self.assertEqual((0.0, 0.0, 10.0, 50.0), mp.extent)
        pnt = Point(5.23, 17.8)
        # Extent of points is just the point itself repeated.
        self.assertEqual((5.23, 17.8, 5.23, 17.8), pnt.extent)
        # Testing on the 'real world' Polygon.
        poly = fromstr(self.geometries.polygons[3].wkt)
        ring = poly.shell
        x, y = ring.x, ring.y
        xmin, ymin = min(x), min(y)
        xmax, ymax = max(x), max(y)
        self.assertEqual((xmin, ymin, xmax, ymax), poly.extent)

    def test_pickle(self):
        "Testing pickling and unpickling support."
        # Creating a list of test geometries for pickling,
        # and setting the SRID on some of them.
        def get_geoms(lst, srid=None):
            return [GEOSGeometry(tg.wkt, srid) for tg in lst]
        tgeoms = get_geoms(self.geometries.points)
        tgeoms.extend(get_geoms(self.geometries.multilinestrings, 4326))
        tgeoms.extend(get_geoms(self.geometries.polygons, 3084))
        tgeoms.extend(get_geoms(self.geometries.multipolygons, 3857))
        tgeoms.append(Point(srid=4326))
        tgeoms.append(Point())
        for geom in tgeoms:
            s1 = pickle.dumps(geom)
            g1 = pickle.loads(s1)
            self.assertEqual(geom, g1)
            self.assertEqual(geom.srid, g1.srid)

    def test_prepared(self):
        "Testing PreparedGeometry support."
        # Creating a simple multipolygon and getting a prepared version.
        mpoly = GEOSGeometry('MULTIPOLYGON(((0 0,0 5,5 5,5 0,0 0)),((5 5,5 10,10 10,10 5,5 5)))')
        prep = mpoly.prepared

        # A set of test points.
        pnts = [Point(5, 5), Point(7.5, 7.5), Point(2.5, 7.5)]
        for pnt in pnts:
            # Results should be the same (but faster)
            self.assertEqual(mpoly.contains(pnt), prep.contains(pnt))
            self.assertEqual(mpoly.intersects(pnt), prep.intersects(pnt))
            self.assertEqual(mpoly.covers(pnt), prep.covers(pnt))

        self.assertTrue(prep.crosses(fromstr('LINESTRING(1 1, 15 15)')))
        self.assertTrue(prep.disjoint(Point(-5, -5)))
        poly = Polygon(((-1, -1), (1, 1), (1, 0), (-1, -1)))
        self.assertTrue(prep.overlaps(poly))
        poly = Polygon(((-5, 0), (-5, 5), (0, 5), (-5, 0)))
        self.assertTrue(prep.touches(poly))
        poly = Polygon(((-1, -1), (-1, 11), (11, 11), (11, -1), (-1, -1)))
        self.assertTrue(prep.within(poly))

        # Original geometry deletion should not crash the prepared one (#21662)
        del mpoly
        self.assertTrue(prep.covers(Point(5, 5)))

    def test_line_merge(self):
        "Testing line merge support"
        ref_geoms = (fromstr('LINESTRING(1 1, 1 1, 3 3)'),
                     fromstr('MULTILINESTRING((1 1, 3 3), (3 3, 4 2))'),
                     )
        ref_merged = (fromstr('LINESTRING(1 1, 3 3)'),
                      fromstr('LINESTRING (1 1, 3 3, 4 2)'),
                      )
        for geom, merged in zip(ref_geoms, ref_merged):
            self.assertEqual(merged, geom.merged)

    def test_valid_reason(self):
        "Testing IsValidReason support"

        g = GEOSGeometry("POINT(0 0)")
        self.assertTrue(g.valid)
        self.assertIsInstance(g.valid_reason, str)
        self.assertEqual(g.valid_reason, "Valid Geometry")

        g = GEOSGeometry("LINESTRING(0 0, 0 0)")

        self.assertFalse(g.valid)
        self.assertIsInstance(g.valid_reason, str)
        self.assertTrue(g.valid_reason.startswith("Too few points in geometry component"))

    def test_linearref(self):
        "Testing linear referencing"

        ls = fromstr('LINESTRING(0 0, 0 10, 10 10, 10 0)')
        mls = fromstr('MULTILINESTRING((0 0, 0 10), (10 0, 10 10))')

        self.assertEqual(ls.project(Point(0, 20)), 10.0)
        self.assertEqual(ls.project(Point(7, 6)), 24)
        self.assertEqual(ls.project_normalized(Point(0, 20)), 1.0 / 3)

        self.assertEqual(ls.interpolate(10), Point(0, 10))
        self.assertEqual(ls.interpolate(24), Point(10, 6))
        self.assertEqual(ls.interpolate_normalized(1.0 / 3), Point(0, 10))

        self.assertEqual(mls.project(Point(0, 20)), 10)
        self.assertEqual(mls.project(Point(7, 6)), 16)

        self.assertEqual(mls.interpolate(9), Point(0, 9))
        self.assertEqual(mls.interpolate(17), Point(10, 7))

    def test_deconstructible(self):
        """
        Geometry classes should be deconstructible.
        """
        point = Point(4.337844, 50.827537, srid=4326)
        path, args, kwargs = point.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.point.Point')
        self.assertEqual(args, (4.337844, 50.827537))
        self.assertEqual(kwargs, {'srid': 4326})

        ls = LineString(((0, 0), (1, 1)))
        path, args, kwargs = ls.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.linestring.LineString')
        self.assertEqual(args, (((0, 0), (1, 1)),))
        self.assertEqual(kwargs, {})

        ls2 = LineString([Point(0, 0), Point(1, 1)], srid=4326)
        path, args, kwargs = ls2.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.linestring.LineString')
        self.assertEqual(args, ([Point(0, 0), Point(1, 1)],))
        self.assertEqual(kwargs, {'srid': 4326})

        ext_coords = ((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))
        int_coords = ((0.4, 0.4), (0.4, 0.6), (0.6, 0.6), (0.6, 0.4), (0.4, 0.4))
        poly = Polygon(ext_coords, int_coords)
        path, args, kwargs = poly.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.polygon.Polygon')
        self.assertEqual(args, (ext_coords, int_coords))
        self.assertEqual(kwargs, {})

        lr = LinearRing((0, 0), (0, 1), (1, 1), (0, 0))
        path, args, kwargs = lr.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.linestring.LinearRing')
        self.assertEqual(args, ((0, 0), (0, 1), (1, 1), (0, 0)))
        self.assertEqual(kwargs, {})

        mp = MultiPoint(Point(0, 0), Point(1, 1))
        path, args, kwargs = mp.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.collections.MultiPoint')
        self.assertEqual(args, (Point(0, 0), Point(1, 1)))
        self.assertEqual(kwargs, {})

        ls1 = LineString((0, 0), (1, 1))
        ls2 = LineString((2, 2), (3, 3))
        mls = MultiLineString(ls1, ls2)
        path, args, kwargs = mls.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.collections.MultiLineString')
        self.assertEqual(args, (ls1, ls2))
        self.assertEqual(kwargs, {})

        p1 = Polygon(((0, 0), (0, 1), (1, 1), (0, 0)))
        p2 = Polygon(((1, 1), (1, 2), (2, 2), (1, 1)))
        mp = MultiPolygon(p1, p2)
        path, args, kwargs = mp.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.collections.MultiPolygon')
        self.assertEqual(args, (p1, p2))
        self.assertEqual(kwargs, {})

        poly = Polygon(((0, 0), (0, 1), (1, 1), (0, 0)))
        gc = GeometryCollection(Point(0, 0), MultiPoint(Point(0, 0), Point(1, 1)), poly)
        path, args, kwargs = gc.deconstruct()
        self.assertEqual(path, 'django.contrib.gis.geos.collections.GeometryCollection')
        self.assertEqual(args, (Point(0, 0), MultiPoint(Point(0, 0), Point(1, 1)), poly))
        self.assertEqual(kwargs, {})

    def test_subclassing(self):
        """
        GEOSGeometry subclass may itself be subclassed without being forced-cast
        to the parent class during `__init__`.
        """
        class ExtendedPolygon(Polygon):
            def __init__(self, *args, data=0, **kwargs):
                super().__init__(*args, **kwargs)
                self._data = data

            def __str__(self):
                return "EXT_POLYGON - data: %d - %s" % (self._data, self.wkt)

        ext_poly = ExtendedPolygon(((0, 0), (0, 1), (1, 1), (0, 0)), data=3)
        self.assertEqual(type(ext_poly), ExtendedPolygon)
        # ExtendedPolygon.__str__ should be called (instead of Polygon.__str__).
        self.assertEqual(str(ext_poly), "EXT_POLYGON - data: 3 - POLYGON ((0 0, 0 1, 1 1, 0 0))")
        self.assertJSONEqual(
            ext_poly.json,
            '{"coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]], "type": "Polygon"}',
        )

    def test_geos_version_tuple(self):
        versions = (
            (b'3.0.0rc4-CAPI-1.3.3', (3, 0, 0)),
            (b'3.0.0-CAPI-1.4.1', (3, 0, 0)),
            (b'3.4.0dev-CAPI-1.8.0', (3, 4, 0)),
            (b'3.4.0dev-CAPI-1.8.0 r0', (3, 4, 0)),
            (b'3.6.2-CAPI-1.10.2 4d2925d6', (3, 6, 2)),
        )
        for version_string, version_tuple in versions:
            with self.subTest(version_string=version_string):
                with mock.patch('django.contrib.gis.geos.libgeos.geos_version', lambda: version_string):
                    self.assertEqual(geos_version_tuple(), version_tuple)

    def test_from_gml(self):
        self.assertEqual(
            GEOSGeometry('POINT(0 0)'),
            GEOSGeometry.from_gml(
                '<gml:Point gml:id="p21" srsName="http://www.opengis.net/def/crs/EPSG/0/4326">'
                '    <gml:pos srsDimension="2">0 0</gml:pos>'
                '</gml:Point>'
            ),
        )

    def test_from_ewkt(self):
        self.assertEqual(GEOSGeometry.from_ewkt('SRID=1;POINT(1 1)'), Point(1, 1, srid=1))
        self.assertEqual(GEOSGeometry.from_ewkt('POINT(1 1)'), Point(1, 1))

    def test_from_ewkt_empty_string(self):
        msg = 'Expected WKT but got an empty string.'
        with self.assertRaisesMessage(ValueError, msg):
            GEOSGeometry.from_ewkt('')
        with self.assertRaisesMessage(ValueError, msg):
            GEOSGeometry.from_ewkt('SRID=1;')

    def test_from_ewkt_invalid_srid(self):
        msg = 'EWKT has invalid SRID part.'
        with self.assertRaisesMessage(ValueError, msg):
            GEOSGeometry.from_ewkt('SRUD=1;POINT(1 1)')
        with self.assertRaisesMessage(ValueError, msg):
            GEOSGeometry.from_ewkt('SRID=WGS84;POINT(1 1)')

    def test_fromstr_scientific_wkt(self):
        self.assertEqual(GEOSGeometry('POINT(1.0e-1 1.0e+1)'), Point(.1, 10))

    def test_normalize(self):
        g = MultiPoint(Point(0, 0), Point(2, 2), Point(1, 1))
        self.assertIsNone(g.normalize())
        self.assertTrue(g.equals_exact(MultiPoint(Point(2, 2), Point(1, 1), Point(0, 0))))

    def test_empty_point(self):
        p = Point(srid=4326)
        self.assertEqual(p.ogr.ewkt, p.ewkt)

        self.assertEqual(p.transform(2774, clone=True), Point(srid=2774))
        p.transform(2774)
        self.assertEqual(p, Point(srid=2774))

    def test_linestring_iter(self):
        ls = LineString((0, 0), (1, 1))
        it = iter(ls)
        # Step into CoordSeq iterator.
        next(it)
        ls[:] = []
        with self.assertRaises(IndexError):
            next(it)
