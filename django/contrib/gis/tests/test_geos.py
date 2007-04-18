import unittest
from copy import copy
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from geometries import *

class GeosTest2(unittest.TestCase):

    def test010_wkt(self):
        "Testing WKT output."
        for g in wkt_out:
            geom = GEOSGeometry(g.wkt)
            self.assertEqual(g.ewkt, geom.wkt)

    def test011_hex(self):
        "Testing HEX output."
        for g in hex_wkt:
            geom = GEOSGeometry(g.wkt)
            self.assertEqual(g.hex, geom.hex)

    def test02_points(self):
        "Testing Point objects."
        prev = GEOSGeometry('POINT(0 0)')

        for p in points:
            pnt = GEOSGeometry(p.wkt)
            self.assertEqual(pnt.geom_type, 'Point')
            self.assertEqual(pnt.geom_typeid, 0)
            self.assertEqual(p.x, pnt.x)
            self.assertEqual(p.y, pnt.y)
            self.assertEqual(True, pnt == GEOSGeometry(p.wkt))
            self.assertEqual(False, pnt == prev)
            prev = pnt

            self.assertAlmostEqual(p.x, pnt.tuple[0], 9)
            self.assertAlmostEqual(p.y, pnt.tuple[1], 9)
            if hasattr(p, 'z'):
                self.assertEqual(True, pnt.hasz)
                self.assertEqual(p.z, pnt.z)
                self.assertEqual(p.z, pnt.tuple[2], 9)
            else:
                self.assertEqual(False, pnt.hasz)
                self.assertEqual(None, pnt.z)

                
            self.assertEqual(p.centroid, pnt.centroid.tuple)

    def test02_multipoints(self):
        "Testing MultiPoint objects."
        for mp in multipoints:
            mpnt = GEOSGeometry(mp.wkt)
            self.assertEqual(mpnt.geom_type, 'MultiPoint')
            self.assertEqual(mpnt.geom_typeid, 4)

            self.assertAlmostEqual(mp.centroid[0], mpnt.centroid.tuple[0], 9)
            self.assertAlmostEqual(mp.centroid[1], mpnt.centroid.tuple[1], 9)

            self.assertEqual(mp.centroid, mpnt.centroid.tuple)
            self.assertEqual(mp.points, tuple(m.tuple for m in mpnt))
            for p in mpnt:
                self.assertEqual(p.geom_type, 'Point')
                self.assertEqual(p.geom_typeid, 0)
                self.assertEqual(p.empty, False)
                self.assertEqual(p.valid, True)
    
    def test03_polygons(self):
        "Testing Polygon objects."

        prev = GEOSGeometry('POINT(0 0)')

        for p in polygons:
            poly = GEOSGeometry(p.wkt)
            self.assertEqual(poly.geom_type, 'Polygon')
            self.assertEqual(poly.geom_typeid, 3)
            self.assertEqual(poly.empty, False)
            self.assertEqual(poly.ring, False)
            self.assertEqual(p.n_i, poly.num_interior_rings)

            # Testing the geometry equivalence
            self.assertEqual(True, poly == GEOSGeometry(p.wkt))
            self.assertEqual(False, poly == prev)
            prev = poly

            # Testing the exterior ring
            ring = poly.exterior_ring
            self.assertEqual(ring.geom_type, 'LinearRing')
            self.assertEqual(ring.geom_typeid, 2)
            if p.ext_ring_cs:
                self.assertEqual(p.ext_ring_cs, ring.tuple)

    def test03_multipolygons(self):
        "Testing MultiPolygon objects."

        prev = GEOSGeometry('POINT (0 0)')

        for mp in multipolygons:
            mpoly = GEOSGeometry(mp.wkt)
            self.assertEqual(mpoly.geom_type, 'MultiPolygon')
            self.assertEqual(mpoly.geom_typeid, 6)
            self.assertEqual(mp.valid, mpoly.valid)

            if mp.valid:
                self.assertEqual(mp.n_p, mpoly.num_geom)
                self.assertEqual(mp.n_p, len(mpoly))
                for p in mpoly:
                    self.assertEqual(p.geom_type, 'Polygon')
                    self.assertEqual(p.geom_typeid, 3)
                    self.assertEqual(p.valid, True)

    def test04_linestring(self):
        "Testing LineString objects."

        prev = GEOSGeometry('POINT(0 0)')

        for l in linestrings:
            ls = GEOSGeometry(l.wkt)
            self.assertEqual(ls.geom_type, 'LineString')
            self.assertEqual(ls.geom_typeid, 1)
            self.assertEqual(ls.empty, False)
            self.assertEqual(ls.ring, False)
            self.assertEqual(l.centroid, ls.centroid.tuple)
            self.assertEqual(True, ls == GEOSGeometry(l.wkt))
            self.assertEqual(False, ls == prev)
            prev = ls

    def test04_multilinestring(self):
        "Testing MultiLineString objects."

        prev = GEOSGeometry('POINT(0 0)')

        for l in multilinestrings:
            ml = GEOSGeometry(l.wkt)
            self.assertEqual(ml.geom_type, 'MultiLineString')
            self.assertEqual(ml.geom_typeid, 5)

            self.assertAlmostEqual(l.centroid[0], ml.centroid.x, 9)
            self.assertAlmostEqual(l.centroid[1], ml.centroid.y, 9)


            self.assertEqual(True, ml == GEOSGeometry(l.wkt))
            self.assertEqual(False, ml == prev)
            prev = ml

            for ls in ml:
                self.assertEqual(ls.geom_type, 'LineString')
                self.assertEqual(ls.geom_typeid, 1)
                self.assertEqual(ls.empty, False)

    #def test05_linearring(self):
    #    "Testing LinearRing objects."
    #    pass

    def test08_coord_seq(self):
        "Testing Coordinate Sequence objects."
        for p in polygons:
            if p.ext_ring_cs:
                poly = GEOSGeometry(p.wkt)
                cs = poly.exterior_ring.coord_seq

                self.assertEqual(p.ext_ring_cs, cs.tuple) # done in the Polygon test too.
                self.assertEqual(len(p.ext_ring_cs), len(cs)) # Making sure __len__ works

                # Checks __getitem__ and __setitem__
                for i in xrange(len(p.ext_ring_cs)):
                    c1 = p.ext_ring_cs[i]
                    c2 = cs[i]
                    self.assertEqual(c1, c2)
                    if len(c1) == 2: tset = (5, 23)
                    else: tset = (5, 23, 8)
                    cs[i] = tset
                    for j in range(len(tset)):
                        cs[i] = tset
                        self.assertEqual(tset, cs[i])

    def test09_relate_pattern(self):
        "Testing relate() and relate_pattern()."

        g = GEOSGeometry('POINT (0 0)')
        self.assertRaises(GEOSException, g.relate_pattern, 0, 'invalid pattern, yo')

        for i in xrange(len(relate_geoms)):
            g_tup = relate_geoms[i]
            a = GEOSGeometry(g_tup[0].wkt)
            b = GEOSGeometry(g_tup[1].wkt)
            pat = g_tup[2]
            result = g_tup[3]
            self.assertEqual(result, a.relate_pattern(b, pat))
            self.assertEqual(g_tup[2], a.relate(b))

    def test10_intersection(self):
        "Testing intersects() and intersection()."

        for i in xrange(len(topology_geoms)):
            g_tup = topology_geoms[i]
            a = GEOSGeometry(g_tup[0].wkt)
            b = GEOSGeometry(g_tup[1].wkt)
            i1 = GEOSGeometry(intersect_geoms[i].wkt) 

            self.assertEqual(True, a.intersects(b))
            i2 = a.intersection(b)
            self.assertEqual(i1, i2)

    def test11_union(self):
        "Testing union()."
        for i in xrange(len(topology_geoms)):
            g_tup = topology_geoms[i]
            a = GEOSGeometry(g_tup[0].wkt)
            b = GEOSGeometry(g_tup[1].wkt)
            u1 = GEOSGeometry(union_geoms[i].wkt)
            u2 = a.union(b)
            self.assertEqual(u1, u2)

    def test12_difference(self):
        "Testing difference()."
        for i in xrange(len(topology_geoms)):
            g_tup = topology_geoms[i]
            a = GEOSGeometry(g_tup[0].wkt)
            b = GEOSGeometry(g_tup[1].wkt)
            d1 = GEOSGeometry(diff_geoms[i].wkt)
            d2 = a.difference(b)
            self.assertEqual(d1, d2)


def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeosTest2))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
