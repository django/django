import ctypes
import random
import unittest
from django.contrib.gis.geos import *
from django.contrib.gis.geos.base import gdal, numpy, GEOSBase
from django.contrib.gis.geos.libgeos import GEOS_PREPARE
from django.contrib.gis.geometry.test_data import TestDataMixin

class GEOSTest(unittest.TestCase, TestDataMixin):

    @property
    def null_srid(self):
        """
        Returns the proper null SRID depending on the GEOS version.
        See the comments in `test15_srid` for more details.
        """
        info = geos_version_info()
        if info['version'] == '3.0.0' and info['release_candidate']:
            return -1
        else:
            return None

    def test00_base(self):
        "Tests out the GEOSBase class."
        # Testing out GEOSBase class, which provides a `ptr` property
        # that abstracts out access to underlying C pointers.
        class FakeGeom1(GEOSBase):
            pass

        # This one only accepts pointers to floats
        c_float_p = ctypes.POINTER(ctypes.c_float)
        class FakeGeom2(GEOSBase):
            ptr_type = c_float_p

        # Default ptr_type is `c_void_p`.
        fg1 = FakeGeom1()
        # Default ptr_type is C float pointer
        fg2 = FakeGeom2()

        # These assignments are OK -- None is allowed because
        # it's equivalent to the NULL pointer.
        fg1.ptr = ctypes.c_void_p()
        fg1.ptr = None
        fg2.ptr = c_float_p(ctypes.c_float(5.23))
        fg2.ptr = None

        # Because pointers have been set to NULL, an exception should be
        # raised when we try to access it.  Raising an exception is
        # preferrable to a segmentation fault that commonly occurs when
        # a C method is given a NULL memory reference.
        for fg in (fg1, fg2):
            # Equivalent to `fg.ptr`
            self.assertRaises(GEOSException, fg._get_ptr)

        # Anything that is either not None or the acceptable pointer type will
        # result in a TypeError when trying to assign it to the `ptr` property.
        # Thus, memmory addresses (integers) and pointers of the incorrect type
        # (in `bad_ptrs`) will not be allowed.
        bad_ptrs = (5, ctypes.c_char_p('foobar'))
        for bad_ptr in bad_ptrs:
            # Equivalent to `fg.ptr = bad_ptr`
            self.assertRaises(TypeError, fg1._set_ptr, bad_ptr)
            self.assertRaises(TypeError, fg2._set_ptr, bad_ptr)

    def test01a_wkt(self):
        "Testing WKT output."
        for g in self.geometries.wkt_out:
            geom = fromstr(g.wkt)
            self.assertEqual(g.ewkt, geom.wkt)

    def test01b_hex(self):
        "Testing HEX output."
        for g in self.geometries.hex_wkt:
            geom = fromstr(g.wkt)
            self.assertEqual(g.hex, geom.hex)

    def test01b_hexewkb(self):
        "Testing (HEX)EWKB output."
        from binascii import a2b_hex

        # For testing HEX(EWKB).
        ogc_hex = '01010000000000000000000000000000000000F03F'
        # `SELECT ST_AsHEXEWKB(ST_GeomFromText('POINT(0 1)', 4326));`
        hexewkb_2d = '0101000020E61000000000000000000000000000000000F03F'
        # `SELECT ST_AsHEXEWKB(ST_GeomFromEWKT('SRID=4326;POINT(0 1 2)'));`
        hexewkb_3d = '01010000A0E61000000000000000000000000000000000F03F0000000000000040'

        pnt_2d = Point(0, 1, srid=4326)
        pnt_3d = Point(0, 1, 2, srid=4326)

        # OGC-compliant HEX will not have SRID nor Z value.
        self.assertEqual(ogc_hex, pnt_2d.hex)
        self.assertEqual(ogc_hex, pnt_3d.hex)

        # HEXEWKB should be appropriate for its dimension -- have to use an
        # a WKBWriter w/dimension set accordingly, else GEOS will insert
        # garbage into 3D coordinate if there is none.  Also, GEOS has a
        # a bug in versions prior to 3.1 that puts the X coordinate in
        # place of Z; an exception should be raised on those versions.
        self.assertEqual(hexewkb_2d, pnt_2d.hexewkb)
        if GEOS_PREPARE:
            self.assertEqual(hexewkb_3d, pnt_3d.hexewkb)
            self.assertEqual(True, GEOSGeometry(hexewkb_3d).hasz)
        else:
            try:
                hexewkb = pnt_3d.hexewkb
            except GEOSException:
                pass
            else:
                self.fail('Should have raised GEOSException.')

        # Same for EWKB.
        self.assertEqual(buffer(a2b_hex(hexewkb_2d)), pnt_2d.ewkb)
        if GEOS_PREPARE:
            self.assertEqual(buffer(a2b_hex(hexewkb_3d)), pnt_3d.ewkb)
        else:
            try:
                ewkb = pnt_3d.ewkb
            except GEOSException:
                pass
            else:
                self.fail('Should have raised GEOSException')

        # Redundant sanity check.
        self.assertEqual(4326, GEOSGeometry(hexewkb_2d).srid)

    def test01c_kml(self):
        "Testing KML output."
        for tg in self.geometries.wkt_out:
            geom = fromstr(tg.wkt)
            kml = getattr(tg, 'kml', False)
            if kml: self.assertEqual(kml, geom.kml)

    def test01d_errors(self):
        "Testing the Error handlers."
        # string-based
        print "\nBEGIN - expecting GEOS_ERROR; safe to ignore.\n"
        for err in self.geometries.errors:
            try:
                g = fromstr(err.wkt)
            except (GEOSException, ValueError):
                pass

        # Bad WKB
        self.assertRaises(GEOSException, GEOSGeometry, buffer('0'))

        print "\nEND - expecting GEOS_ERROR; safe to ignore.\n"

        class NotAGeometry(object):
            pass

        # Some other object
        self.assertRaises(TypeError, GEOSGeometry, NotAGeometry())
        # None
        self.assertRaises(TypeError, GEOSGeometry, None)

    def test01e_wkb(self):
        "Testing WKB output."
        from binascii import b2a_hex
        for g in self.geometries.hex_wkt:
            geom = fromstr(g.wkt)
            wkb = geom.wkb
            self.assertEqual(b2a_hex(wkb).upper(), g.hex)

    def test01f_create_hex(self):
        "Testing creation from HEX."
        for g in self.geometries.hex_wkt:
            geom_h = GEOSGeometry(g.hex)
            # we need to do this so decimal places get normalised
            geom_t = fromstr(g.wkt)
            self.assertEqual(geom_t.wkt, geom_h.wkt)

    def test01g_create_wkb(self):
        "Testing creation from WKB."
        from binascii import a2b_hex
        for g in self.geometries.hex_wkt:
            wkb = buffer(a2b_hex(g.hex))
            geom_h = GEOSGeometry(wkb)
            # we need to do this so decimal places get normalised
            geom_t = fromstr(g.wkt)
            self.assertEqual(geom_t.wkt, geom_h.wkt)

    def test01h_ewkt(self):
        "Testing EWKT."
        srids = (-1, 32140)
        for srid in srids:
            for p in self.geometries.polygons:
                ewkt = 'SRID=%d;%s' % (srid, p.wkt)
                poly = fromstr(ewkt)
                self.assertEqual(srid, poly.srid)
                self.assertEqual(srid, poly.shell.srid)
                self.assertEqual(srid, fromstr(poly.ewkt).srid) # Checking export

    def test01i_json(self):
        "Testing GeoJSON input/output (via GDAL)."
        if not gdal or not gdal.GEOJSON: return
        for g in self.geometries.json_geoms:
            geom = GEOSGeometry(g.wkt)
            if not hasattr(g, 'not_equal'):
                self.assertEqual(g.json, geom.json)
                self.assertEqual(g.json, geom.geojson)
            self.assertEqual(GEOSGeometry(g.wkt), GEOSGeometry(geom.json))

    def test01k_fromfile(self):
        "Testing the fromfile() factory."
        from StringIO import StringIO
        ref_pnt = GEOSGeometry('POINT(5 23)')

        wkt_f = StringIO()
        wkt_f.write(ref_pnt.wkt)
        wkb_f = StringIO()
        wkb_f.write(str(ref_pnt.wkb))

        # Other tests use `fromfile()` on string filenames so those
        # aren't tested here.
        for fh in (wkt_f, wkb_f):
            fh.seek(0)
            pnt = fromfile(fh)
            self.assertEqual(ref_pnt, pnt)

    def test01k_eq(self):
        "Testing equivalence."
        p = fromstr('POINT(5 23)')
        self.assertEqual(p, p.wkt)
        self.assertNotEqual(p, 'foo')
        ls = fromstr('LINESTRING(0 0, 1 1, 5 5)')
        self.assertEqual(ls, ls.wkt)
        self.assertNotEqual(p, 'bar')
        # Error shouldn't be raise on equivalence testing with
        # an invalid type.
        for g in (p, ls):
            self.assertNotEqual(g, None)
            self.assertNotEqual(g, {'foo' : 'bar'})
            self.assertNotEqual(g, False)

    def test02a_points(self):
        "Testing Point objects."
        prev = fromstr('POINT(0 0)')
        for p in self.geometries.points:
            # Creating the point from the WKT
            pnt = fromstr(p.wkt)
            self.assertEqual(pnt.geom_type, 'Point')
            self.assertEqual(pnt.geom_typeid, 0)
            self.assertEqual(p.x, pnt.x)
            self.assertEqual(p.y, pnt.y)
            self.assertEqual(True, pnt == fromstr(p.wkt))
            self.assertEqual(False, pnt == prev)

            # Making sure that the point's X, Y components are what we expect
            self.assertAlmostEqual(p.x, pnt.tuple[0], 9)
            self.assertAlmostEqual(p.y, pnt.tuple[1], 9)

            # Testing the third dimension, and getting the tuple arguments
            if hasattr(p, 'z'):
                self.assertEqual(True, pnt.hasz)
                self.assertEqual(p.z, pnt.z)
                self.assertEqual(p.z, pnt.tuple[2], 9)
                tup_args = (p.x, p.y, p.z)
                set_tup1 = (2.71, 3.14, 5.23)
                set_tup2 = (5.23, 2.71, 3.14)
            else:
                self.assertEqual(False, pnt.hasz)
                self.assertEqual(None, pnt.z)
                tup_args = (p.x, p.y)
                set_tup1 = (2.71, 3.14)
                set_tup2 = (3.14, 2.71)

            # Centroid operation on point should be point itself
            self.assertEqual(p.centroid, pnt.centroid.tuple)

            # Now testing the different constructors
            pnt2 = Point(tup_args)  # e.g., Point((1, 2))
            pnt3 = Point(*tup_args) # e.g., Point(1, 2)
            self.assertEqual(True, pnt == pnt2)
            self.assertEqual(True, pnt == pnt3)

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

            prev = pnt # setting the previous geometry

    def test02b_multipoints(self):
        "Testing MultiPoint objects."
        for mp in self.geometries.multipoints:
            mpnt = fromstr(mp.wkt)
            self.assertEqual(mpnt.geom_type, 'MultiPoint')
            self.assertEqual(mpnt.geom_typeid, 4)

            self.assertAlmostEqual(mp.centroid[0], mpnt.centroid.tuple[0], 9)
            self.assertAlmostEqual(mp.centroid[1], mpnt.centroid.tuple[1], 9)

            self.assertRaises(GEOSIndexError, mpnt.__getitem__, len(mpnt))
            self.assertEqual(mp.centroid, mpnt.centroid.tuple)
            self.assertEqual(mp.coords, tuple(m.tuple for m in mpnt))
            for p in mpnt:
                self.assertEqual(p.geom_type, 'Point')
                self.assertEqual(p.geom_typeid, 0)
                self.assertEqual(p.empty, False)
                self.assertEqual(p.valid, True)

    def test03a_linestring(self):
        "Testing LineString objects."
        prev = fromstr('POINT(0 0)')
        for l in self.geometries.linestrings:
            ls = fromstr(l.wkt)
            self.assertEqual(ls.geom_type, 'LineString')
            self.assertEqual(ls.geom_typeid, 1)
            self.assertEqual(ls.empty, False)
            self.assertEqual(ls.ring, False)
            if hasattr(l, 'centroid'):
                self.assertEqual(l.centroid, ls.centroid.tuple)
            if hasattr(l, 'tup'):
                self.assertEqual(l.tup, ls.tuple)

            self.assertEqual(True, ls == fromstr(l.wkt))
            self.assertEqual(False, ls == prev)
            self.assertRaises(GEOSIndexError, ls.__getitem__, len(ls))
            prev = ls

            # Creating a LineString from a tuple, list, and numpy array
            self.assertEqual(ls, LineString(ls.tuple))  # tuple
            self.assertEqual(ls, LineString(*ls.tuple)) # as individual arguments
            self.assertEqual(ls, LineString([list(tup) for tup in ls.tuple])) # as list
            self.assertEqual(ls.wkt, LineString(*tuple(Point(tup) for tup in ls.tuple)).wkt) # Point individual arguments
            if numpy: self.assertEqual(ls, LineString(numpy.array(ls.tuple))) # as numpy array

    def test03b_multilinestring(self):
        "Testing MultiLineString objects."
        prev = fromstr('POINT(0 0)')
        for l in self.geometries.multilinestrings:
            ml = fromstr(l.wkt)
            self.assertEqual(ml.geom_type, 'MultiLineString')
            self.assertEqual(ml.geom_typeid, 5)

            self.assertAlmostEqual(l.centroid[0], ml.centroid.x, 9)
            self.assertAlmostEqual(l.centroid[1], ml.centroid.y, 9)

            self.assertEqual(True, ml == fromstr(l.wkt))
            self.assertEqual(False, ml == prev)
            prev = ml

            for ls in ml:
                self.assertEqual(ls.geom_type, 'LineString')
                self.assertEqual(ls.geom_typeid, 1)
                self.assertEqual(ls.empty, False)

            self.assertRaises(GEOSIndexError, ml.__getitem__, len(ml))
            self.assertEqual(ml.wkt, MultiLineString(*tuple(s.clone() for s in ml)).wkt)
            self.assertEqual(ml, MultiLineString(*tuple(LineString(s.tuple) for s in ml)))

    def test04_linearring(self):
        "Testing LinearRing objects."
        for rr in self.geometries.linearrings:
            lr = fromstr(rr.wkt)
            self.assertEqual(lr.geom_type, 'LinearRing')
            self.assertEqual(lr.geom_typeid, 2)
            self.assertEqual(rr.n_p, len(lr))
            self.assertEqual(True, lr.valid)
            self.assertEqual(False, lr.empty)

            # Creating a LinearRing from a tuple, list, and numpy array
            self.assertEqual(lr, LinearRing(lr.tuple))
            self.assertEqual(lr, LinearRing(*lr.tuple))
            self.assertEqual(lr, LinearRing([list(tup) for tup in lr.tuple]))
            if numpy: self.assertEqual(lr, LinearRing(numpy.array(lr.tuple)))

    def test05a_polygons(self):
        "Testing Polygon objects."

        # Testing `from_bbox` class method
        bbox = (-180, -90, 180, 90)
        p = Polygon.from_bbox( bbox )
        self.assertEqual(bbox, p.extent)

        prev = fromstr('POINT(0 0)')
        for p in self.geometries.polygons:
            # Creating the Polygon, testing its properties.
            poly = fromstr(p.wkt)
            self.assertEqual(poly.geom_type, 'Polygon')
            self.assertEqual(poly.geom_typeid, 3)
            self.assertEqual(poly.empty, False)
            self.assertEqual(poly.ring, False)
            self.assertEqual(p.n_i, poly.num_interior_rings)
            self.assertEqual(p.n_i + 1, len(poly)) # Testing __len__
            self.assertEqual(p.n_p, poly.num_points)

            # Area & Centroid
            self.assertAlmostEqual(p.area, poly.area, 9)
            self.assertAlmostEqual(p.centroid[0], poly.centroid.tuple[0], 9)
            self.assertAlmostEqual(p.centroid[1], poly.centroid.tuple[1], 9)

            # Testing the geometry equivalence
            self.assertEqual(True, poly == fromstr(p.wkt))
            self.assertEqual(False, poly == prev) # Should not be equal to previous geometry
            self.assertEqual(True, poly != prev)

            # Testing the exterior ring
            ring = poly.exterior_ring
            self.assertEqual(ring.geom_type, 'LinearRing')
            self.assertEqual(ring.geom_typeid, 2)
            if p.ext_ring_cs:
                self.assertEqual(p.ext_ring_cs, ring.tuple)
                self.assertEqual(p.ext_ring_cs, poly[0].tuple) # Testing __getitem__

            # Testing __getitem__ and __setitem__ on invalid indices
            self.assertRaises(GEOSIndexError, poly.__getitem__, len(poly))
            self.assertRaises(GEOSIndexError, poly.__setitem__, len(poly), False)
            self.assertRaises(GEOSIndexError, poly.__getitem__, -1 * len(poly) - 1)

            # Testing __iter__
            for r in poly:
                self.assertEqual(r.geom_type, 'LinearRing')
                self.assertEqual(r.geom_typeid, 2)

            # Testing polygon construction.
            self.assertRaises(TypeError, Polygon.__init__, 0, [1, 2, 3])
            self.assertRaises(TypeError, Polygon.__init__, 'foo')

            # Polygon(shell, (hole1, ... holeN))
            rings = tuple(r for r in poly)
            self.assertEqual(poly, Polygon(rings[0], rings[1:]))

            # Polygon(shell_tuple, hole_tuple1, ... , hole_tupleN)
            ring_tuples = tuple(r.tuple for r in poly)
            self.assertEqual(poly, Polygon(*ring_tuples))

            # Constructing with tuples of LinearRings.
            self.assertEqual(poly.wkt, Polygon(*tuple(r for r in poly)).wkt)
            self.assertEqual(poly.wkt, Polygon(*tuple(LinearRing(r.tuple) for r in poly)).wkt)

    def test05b_multipolygons(self):
        "Testing MultiPolygon objects."
        print "\nBEGIN - expecting GEOS_NOTICE; safe to ignore.\n"
        prev = fromstr('POINT (0 0)')
        for mp in self.geometries.multipolygons:
            mpoly = fromstr(mp.wkt)
            self.assertEqual(mpoly.geom_type, 'MultiPolygon')
            self.assertEqual(mpoly.geom_typeid, 6)
            self.assertEqual(mp.valid, mpoly.valid)

            if mp.valid:
                self.assertEqual(mp.num_geom, mpoly.num_geom)
                self.assertEqual(mp.n_p, mpoly.num_coords)
                self.assertEqual(mp.num_geom, len(mpoly))
                self.assertRaises(GEOSIndexError, mpoly.__getitem__, len(mpoly))
                for p in mpoly:
                    self.assertEqual(p.geom_type, 'Polygon')
                    self.assertEqual(p.geom_typeid, 3)
                    self.assertEqual(p.valid, True)
                self.assertEqual(mpoly.wkt, MultiPolygon(*tuple(poly.clone() for poly in mpoly)).wkt)

        print "\nEND - expecting GEOS_NOTICE; safe to ignore.\n"

    def test06a_memory_hijinks(self):
        "Testing Geometry __del__() on rings and polygons."
        #### Memory issues with rings and polygons

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
        s1, s2 = str(ring1), str(ring2)

    def test08_coord_seq(self):
        "Testing Coordinate Sequence objects."
        for p in self.geometries.polygons:
            if p.ext_ring_cs:
                # Constructing the polygon and getting the coordinate sequence
                poly = fromstr(p.wkt)
                cs = poly.exterior_ring.coord_seq

                self.assertEqual(p.ext_ring_cs, cs.tuple) # done in the Polygon test too.
                self.assertEqual(len(p.ext_ring_cs), len(cs)) # Making sure __len__ works

                # Checks __getitem__ and __setitem__
                for i in xrange(len(p.ext_ring_cs)):
                    c1 = p.ext_ring_cs[i] # Expected value
                    c2 = cs[i] # Value from coordseq
                    self.assertEqual(c1, c2)

                    # Constructing the test value to set the coordinate sequence with
                    if len(c1) == 2: tset = (5, 23)
                    else: tset = (5, 23, 8)
                    cs[i] = tset

                    # Making sure every set point matches what we expect
                    for j in range(len(tset)):
                        cs[i] = tset
                        self.assertEqual(tset[j], cs[i][j])

    def test09_relate_pattern(self):
        "Testing relate() and relate_pattern()."
        g = fromstr('POINT (0 0)')
        self.assertRaises(GEOSException, g.relate_pattern, 0, 'invalid pattern, yo')
        for rg in self.geometries.relate_geoms:
            a = fromstr(rg.wkt_a)
            b = fromstr(rg.wkt_b)
            self.assertEqual(rg.result, a.relate_pattern(b, rg.pattern))
            self.assertEqual(rg.pattern, a.relate(b))

    def test10_intersection(self):
        "Testing intersects() and intersection()."
        for i in xrange(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            i1 = fromstr(self.geometries.intersect_geoms[i].wkt)
            self.assertEqual(True, a.intersects(b))
            i2 = a.intersection(b)
            self.assertEqual(i1, i2)
            self.assertEqual(i1, a & b) # __and__ is intersection operator
            a &= b # testing __iand__
            self.assertEqual(i1, a)

    def test11_union(self):
        "Testing union()."
        for i in xrange(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            u1 = fromstr(self.geometries.union_geoms[i].wkt)
            u2 = a.union(b)
            self.assertEqual(u1, u2)
            self.assertEqual(u1, a | b) # __or__ is union operator
            a |= b # testing __ior__
            self.assertEqual(u1, a)

    def test12_difference(self):
        "Testing difference()."
        for i in xrange(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            d1 = fromstr(self.geometries.diff_geoms[i].wkt)
            d2 = a.difference(b)
            self.assertEqual(d1, d2)
            self.assertEqual(d1, a - b) # __sub__ is difference operator
            a -= b # testing __isub__
            self.assertEqual(d1, a)

    def test13_symdifference(self):
        "Testing sym_difference()."
        for i in xrange(len(self.geometries.topology_geoms)):
            a = fromstr(self.geometries.topology_geoms[i].wkt_a)
            b = fromstr(self.geometries.topology_geoms[i].wkt_b)
            d1 = fromstr(self.geometries.sdiff_geoms[i].wkt)
            d2 = a.sym_difference(b)
            self.assertEqual(d1, d2)
            self.assertEqual(d1, a ^ b) # __xor__ is symmetric difference operator
            a ^= b # testing __ixor__
            self.assertEqual(d1, a)

    def test14_buffer(self):
        "Testing buffer()."
        for bg in self.geometries.buffer_geoms:
            g = fromstr(bg.wkt)

            # The buffer we expect
            exp_buf = fromstr(bg.buffer_wkt)
            quadsegs = bg.quadsegs
            width = bg.width

            # Can't use a floating-point for the number of quadsegs.
            self.assertRaises(ctypes.ArgumentError, g.buffer, width, float(quadsegs))

            # Constructing our buffer
            buf = g.buffer(width, quadsegs)
            self.assertEqual(exp_buf.num_coords, buf.num_coords)
            self.assertEqual(len(exp_buf), len(buf))

            # Now assuring that each point in the buffer is almost equal
            for j in xrange(len(exp_buf)):
                exp_ring = exp_buf[j]
                buf_ring = buf[j]
                self.assertEqual(len(exp_ring), len(buf_ring))
                for k in xrange(len(exp_ring)):
                    # Asserting the X, Y of each point are almost equal (due to floating point imprecision)
                    self.assertAlmostEqual(exp_ring[k][0], buf_ring[k][0], 9)
                    self.assertAlmostEqual(exp_ring[k][1], buf_ring[k][1], 9)

    def test15_srid(self):
        "Testing the SRID property and keyword."
        # Testing SRID keyword on Point
        pnt = Point(5, 23, srid=4326)
        self.assertEqual(4326, pnt.srid)
        pnt.srid = 3084
        self.assertEqual(3084, pnt.srid)
        self.assertRaises(ctypes.ArgumentError, pnt.set_srid, '4326')

        # Testing SRID keyword on fromstr(), and on Polygon rings.
        poly = fromstr(self.geometries.polygons[1].wkt, srid=4269)
        self.assertEqual(4269, poly.srid)
        for ring in poly: self.assertEqual(4269, ring.srid)
        poly.srid = 4326
        self.assertEqual(4326, poly.shell.srid)

        # Testing SRID keyword on GeometryCollection
        gc = GeometryCollection(Point(5, 23), LineString((0, 0), (1.5, 1.5), (3, 3)), srid=32021)
        self.assertEqual(32021, gc.srid)
        for i in range(len(gc)): self.assertEqual(32021, gc[i].srid)

        # GEOS may get the SRID from HEXEWKB
        # 'POINT(5 23)' at SRID=4326 in hex form -- obtained from PostGIS
        # using `SELECT GeomFromText('POINT (5 23)', 4326);`.
        hex = '0101000020E610000000000000000014400000000000003740'
        p1 = fromstr(hex)
        self.assertEqual(4326, p1.srid)

        # In GEOS 3.0.0rc1-4  when the EWKB and/or HEXEWKB is exported,
        # the SRID information is lost and set to -1 -- this is not a
        # problem on the 3.0.0 version (another reason to upgrade).
        exp_srid = self.null_srid

        p2 = fromstr(p1.hex)
        self.assertEqual(exp_srid, p2.srid)
        p3 = fromstr(p1.hex, srid=-1) # -1 is intended.
        self.assertEqual(-1, p3.srid)

    def test16_mutable_geometries(self):
        "Testing the mutability of Polygons and Geometry Collections."
        ### Testing the mutability of Polygons ###
        for p in self.geometries.polygons:
            poly = fromstr(p.wkt)

            # Should only be able to use __setitem__ with LinearRing geometries.
            self.assertRaises(TypeError, poly.__setitem__, 0, LineString((1, 1), (2, 2)))

            # Constructing the new shell by adding 500 to every point in the old shell.
            shell_tup = poly.shell.tuple
            new_coords = []
            for point in shell_tup: new_coords.append((point[0] + 500., point[1] + 500.))
            new_shell = LinearRing(*tuple(new_coords))

            # Assigning polygon's exterior ring w/the new shell
            poly.exterior_ring = new_shell
            s = str(new_shell) # new shell is still accessible
            self.assertEqual(poly.exterior_ring, new_shell)
            self.assertEqual(poly[0], new_shell)

        ### Testing the mutability of Geometry Collections
        for tg in self.geometries.multipoints:
            mp = fromstr(tg.wkt)
            for i in range(len(mp)):
                # Creating a random point.
                pnt = mp[i]
                new = Point(random.randint(1, 100), random.randint(1, 100))
                # Testing the assignment
                mp[i] = new
                s = str(new) # what was used for the assignment is still accessible
                self.assertEqual(mp[i], new)
                self.assertEqual(mp[i].wkt, new.wkt)
                self.assertNotEqual(pnt, mp[i])

        # MultiPolygons involve much more memory management because each
        # Polygon w/in the collection has its own rings.
        for tg in self.geometries.multipolygons:
            mpoly = fromstr(tg.wkt)
            for i in xrange(len(mpoly)):
                poly = mpoly[i]
                old_poly = mpoly[i]
                # Offsetting the each ring in the polygon by 500.
                for j in xrange(len(poly)):
                    r = poly[j]
                    for k in xrange(len(r)): r[k] = (r[k][0] + 500., r[k][1] + 500.)
                    poly[j] = r

                self.assertNotEqual(mpoly[i], poly)
                # Testing the assignment
                mpoly[i] = poly
                s = str(poly) # Still accessible
                self.assertEqual(mpoly[i], poly)
                self.assertNotEqual(mpoly[i], old_poly)

        # Extreme (!!) __setitem__ -- no longer works, have to detect
        # in the first object that __setitem__ is called in the subsequent
        # objects -- maybe mpoly[0, 0, 0] = (3.14, 2.71)?
        #mpoly[0][0][0] = (3.14, 2.71)
        #self.assertEqual((3.14, 2.71), mpoly[0][0][0])
        # Doing it more slowly..
        #self.assertEqual((3.14, 2.71), mpoly[0].shell[0])
        #del mpoly

    def test17_threed(self):
        "Testing three-dimensional geometries."
        # Testing a 3D Point
        pnt = Point(2, 3, 8)
        self.assertEqual((2.,3.,8.), pnt.coords)
        self.assertRaises(TypeError, pnt.set_coords, (1.,2.))
        pnt.coords = (1.,2.,3.)
        self.assertEqual((1.,2.,3.), pnt.coords)

        # Testing a 3D LineString
        ls = LineString((2., 3., 8.), (50., 250., -117.))
        self.assertEqual(((2.,3.,8.), (50.,250.,-117.)), ls.tuple)
        self.assertRaises(TypeError, ls.__setitem__, 0, (1.,2.))
        ls[0] = (1.,2.,3.)
        self.assertEqual((1.,2.,3.), ls[0])

    def test18_distance(self):
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

    def test19_length(self):
        "Testing the length property."
        # Points have 0 length.
        pnt = Point(0, 0)
        self.assertEqual(0.0, pnt.length)

        # Should be ~ sqrt(2)
        ls = LineString((0, 0), (1, 1))
        self.assertAlmostEqual(1.41421356237, ls.length, 11)

        # Should be circumfrence of Polygon
        poly = Polygon(LinearRing((0, 0), (0, 1), (1, 1), (1, 0), (0, 0)))
        self.assertEqual(4.0, poly.length)

        # Should be sum of each element's length in collection.
        mpoly = MultiPolygon(poly.clone(), poly)
        self.assertEqual(8.0, mpoly.length)

    def test20a_emptyCollections(self):
        "Testing empty geometries and collections."
        gc1 = GeometryCollection([])
        gc2 = fromstr('GEOMETRYCOLLECTION EMPTY')
        pnt = fromstr('POINT EMPTY')
        ls = fromstr('LINESTRING EMPTY')
        poly = fromstr('POLYGON EMPTY')
        mls = fromstr('MULTILINESTRING EMPTY')
        mpoly1 = fromstr('MULTIPOLYGON EMPTY')
        mpoly2 = MultiPolygon(())

        for g in [gc1, gc2, pnt, ls, poly, mls, mpoly1, mpoly2]:
            self.assertEqual(True, g.empty)

            # Testing len() and num_geom.
            if isinstance(g, Polygon):
                self.assertEqual(1, len(g)) # Has one empty linear ring
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
                self.assertRaises(GEOSIndexError, g.get_x)
            elif isinstance(g, Polygon):
                lr = g.shell
                self.assertEqual('LINEARRING EMPTY', lr.wkt)
                self.assertEqual(0, len(lr))
                self.assertEqual(True, lr.empty)
                self.assertRaises(GEOSIndexError, lr.__getitem__, 0)
            else:
                self.assertRaises(GEOSIndexError, g.__getitem__, 0)

    def test20b_collections_of_collections(self):
        "Testing GeometryCollection handling of other collections."
        # Creating a GeometryCollection WKT string composed of other
        # collections and polygons.
        coll = [mp.wkt for mp in self.geometries.multipolygons if mp.valid]
        coll.extend([mls.wkt for mls in self.geometries.multilinestrings])
        coll.extend([p.wkt for p in self.geometries.polygons])
        coll.extend([mp.wkt for mp in self.geometries.multipoints])
        gc_wkt = 'GEOMETRYCOLLECTION(%s)' % ','.join(coll)

        # Should construct ok from WKT
        gc1 = GEOSGeometry(gc_wkt)

        # Should also construct ok from individual geometry arguments.
        gc2 = GeometryCollection(*tuple(g for g in gc1))

        # And, they should be equal.
        self.assertEqual(gc1, gc2)

    def test21_test_gdal(self):
        "Testing `ogr` and `srs` properties."
        if not gdal.HAS_GDAL: return
        g1 = fromstr('POINT(5 23)')
        self.assertEqual(True, isinstance(g1.ogr, gdal.OGRGeometry))
        self.assertEqual(g1.srs, None)

        g2 = fromstr('LINESTRING(0 0, 5 5, 23 23)', srid=4326)
        self.assertEqual(True, isinstance(g2.ogr, gdal.OGRGeometry))
        self.assertEqual(True, isinstance(g2.srs, gdal.SpatialReference))
        self.assertEqual(g2.hex, g2.ogr.hex)
        self.assertEqual('WGS 84', g2.srs.name)

    def test22_copy(self):
        "Testing use with the Python `copy` module."
        import copy
        poly = GEOSGeometry('POLYGON((0 0, 0 23, 23 23, 23 0, 0 0), (5 5, 5 10, 10 10, 10 5, 5 5))')
        cpy1 = copy.copy(poly)
        cpy2 = copy.deepcopy(poly)
        self.assertNotEqual(poly._ptr, cpy1._ptr)
        self.assertNotEqual(poly._ptr, cpy2._ptr)

    def test23_transform(self):
        "Testing `transform` method."
        if not gdal.HAS_GDAL: return
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

    def test23_transform_noop(self):
        """ Testing `transform` method (SRID match) """
        # transform() should no-op if source & dest SRIDs match,
        # regardless of whether GDAL is available.
        if gdal.HAS_GDAL:
            g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
            gt = g.tuple
            g.transform(4326)
            self.assertEqual(g.tuple, gt)
            self.assertEqual(g.srid, 4326)

            g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
            g1 = g.transform(4326, clone=True)
            self.assertEqual(g1.tuple, g.tuple)
            self.assertEqual(g1.srid, 4326)
            self.assertTrue(g1 is not g, "Clone didn't happen")

        old_has_gdal = gdal.HAS_GDAL
        try:
            gdal.HAS_GDAL = False

            g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
            gt = g.tuple
            g.transform(4326)
            self.assertEqual(g.tuple, gt)
            self.assertEqual(g.srid, 4326)

            g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
            g1 = g.transform(4326, clone=True)
            self.assertEqual(g1.tuple, g.tuple)
            self.assertEqual(g1.srid, 4326)
            self.assertTrue(g1 is not g, "Clone didn't happen")
        finally:
            gdal.HAS_GDAL = old_has_gdal

    def test23_transform_nosrid(self):
        """ Testing `transform` method (no SRID) """
        # Raise a warning if SRID <0/None.
        import warnings
        print "\nBEGIN - expecting Warnings; safe to ignore.\n"

        # Test for do-nothing behavior.
        try:
            # Keeping line-noise down by only printing the relevant
            # warnings once.
            warnings.simplefilter('once', UserWarning)
            warnings.simplefilter('once', FutureWarning)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=None)
            g.transform(2774)
            self.assertEqual(g.tuple, (-104.609, 38.255))
            self.assertEqual(g.srid, None)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=None)
            g1 = g.transform(2774, clone=True)
            self.assertTrue(g1 is None)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=-1)
            g.transform(2774)
            self.assertEqual(g.tuple, (-104.609, 38.255))
            self.assertEqual(g.srid, -1)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=-1)
            g1 = g.transform(2774, clone=True)
            self.assertTrue(g1 is None)

        finally:
            warnings.simplefilter('default', UserWarning)
            warnings.simplefilter('default', FutureWarning)

        print "\nEND - expecting Warnings; safe to ignore.\n"


        # test warning is raised
        try:
            warnings.simplefilter('error', FutureWarning)
            warnings.simplefilter('ignore', UserWarning)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=None)
            self.assertRaises(FutureWarning, g.transform, 2774)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=None)
            self.assertRaises(FutureWarning, g.transform, 2774, clone=True)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=-1)
            self.assertRaises(FutureWarning, g.transform, 2774)

            g = GEOSGeometry('POINT (-104.609 38.255)', srid=-1)
            self.assertRaises(FutureWarning, g.transform, 2774, clone=True)
        finally:
            warnings.simplefilter('default', FutureWarning)
            warnings.simplefilter('default', UserWarning)


    def test23_transform_nogdal(self):
        """ Testing `transform` method (GDAL not available) """
        old_has_gdal = gdal.HAS_GDAL
        try:
            gdal.HAS_GDAL = False

            g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
            self.assertRaises(GEOSException, g.transform, 2774)

            g = GEOSGeometry('POINT (-104.609 38.255)', 4326)
            self.assertRaises(GEOSException, g.transform, 2774, clone=True)
        finally:
            gdal.HAS_GDAL = old_has_gdal

    def test24_extent(self):
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

    def test25_pickle(self):
        "Testing pickling and unpickling support."
        # Using both pickle and cPickle -- just 'cause.
        import pickle, cPickle

        # Creating a list of test geometries for pickling,
        # and setting the SRID on some of them.
        def get_geoms(lst, srid=None):
            return [GEOSGeometry(tg.wkt, srid) for tg in lst]
        tgeoms = get_geoms(self.geometries.points)
        tgeoms.extend(get_geoms(self.geometries.multilinestrings, 4326))
        tgeoms.extend(get_geoms(self.geometries.polygons, 3084))
        tgeoms.extend(get_geoms(self.geometries.multipolygons, 900913))

        # The SRID won't be exported in GEOS 3.0 release candidates.
        no_srid = self.null_srid == -1
        for geom in tgeoms:
            s1, s2 = cPickle.dumps(geom), pickle.dumps(geom)
            g1, g2 = cPickle.loads(s1), pickle.loads(s2)
            for tmpg in (g1, g2):
                self.assertEqual(geom, tmpg)
                if not no_srid: self.assertEqual(geom.srid, tmpg.srid)

    def test26_prepared(self):
        "Testing PreparedGeometry support."
        if not GEOS_PREPARE: return
        # Creating a simple multipolygon and getting a prepared version.
        mpoly = GEOSGeometry('MULTIPOLYGON(((0 0,0 5,5 5,5 0,0 0)),((5 5,5 10,10 10,10 5,5 5)))')
        prep = mpoly.prepared

        # A set of test points.
        pnts = [Point(5, 5), Point(7.5, 7.5), Point(2.5, 7.5)]
        covers = [True, True, False] # No `covers` op for regular GEOS geoms.
        for pnt, c in zip(pnts, covers):
            # Results should be the same (but faster)
            self.assertEqual(mpoly.contains(pnt), prep.contains(pnt))
            self.assertEqual(mpoly.intersects(pnt), prep.intersects(pnt))
            self.assertEqual(c, prep.covers(pnt))

    def test26_line_merge(self):
        "Testing line merge support"
        ref_geoms = (fromstr('LINESTRING(1 1, 1 1, 3 3)'),
                     fromstr('MULTILINESTRING((1 1, 3 3), (3 3, 4 2))'),
                     )
        ref_merged = (fromstr('LINESTRING(1 1, 3 3)'),
                      fromstr('LINESTRING (1 1, 3 3, 4 2)'),
                      )
        for geom, merged in zip(ref_geoms, ref_merged):
            self.assertEqual(merged, geom.merged)

    def test27_valid_reason(self):
        "Testing IsValidReason support"
        # Skipping tests if GEOS < v3.1.
        if not GEOS_PREPARE: return

        g = GEOSGeometry("POINT(0 0)")
        self.assertTrue(g.valid)
        self.assertTrue(isinstance(g.valid_reason, basestring))
        self.assertEqual(g.valid_reason, "Valid Geometry")

        print "\nBEGIN - expecting GEOS_NOTICE; safe to ignore.\n"

        g = GEOSGeometry("LINESTRING(0 0, 0 0)")

        self.assertTrue(not g.valid)
        self.assertTrue(isinstance(g.valid_reason, basestring))
        self.assertTrue(g.valid_reason.startswith("Too few points in geometry component"))

        print "\nEND - expecting GEOS_NOTICE; safe to ignore.\n"

    def test28_geos_version(self):
        "Testing the GEOS version regular expression."
        from django.contrib.gis.geos.libgeos import version_regex
        versions = [ ('3.0.0rc4-CAPI-1.3.3', '3.0.0'),
                     ('3.0.0-CAPI-1.4.1', '3.0.0'),
                     ('3.4.0dev-CAPI-1.8.0', '3.4.0') ]
        for v, expected in versions:
            m = version_regex.match(v)
            self.assertTrue(m)
            self.assertEqual(m.group('version'), expected)


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GEOSTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
