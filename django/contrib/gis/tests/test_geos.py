import unittest
from django.contrib.gis.geos import GEOSGeometry, GEOSException, Point, LineString, LinearRing, HAS_NUMPY
from geometries import *

if HAS_NUMPY:
    from numpy import array

class GEOSTest(unittest.TestCase):

    def test01a_wkt(self):
        "Testing WKT output."
        for g in wkt_out:
            geom = GEOSGeometry(g.wkt)
            self.assertEqual(g.ewkt, geom.wkt)

    def test01b_hex(self):
        "Testing HEX output."
        for g in hex_wkt:
            geom = GEOSGeometry(g.wkt)
            self.assertEqual(g.hex, geom.hex)

    def test01c_errors(self):
        "Testing the Error handlers."
        print "\nBEGIN - expecting GEOS_ERROR; safe to ignore.\n"
        for err in errors:
            if err.hex:
                self.assertRaises(GEOSException, GEOSGeometry, err.wkt)
            else:
                self.assertRaises(GEOSException, GEOSGeometry, err.wkt)
        print "\nEND - expecting GEOS_ERROR; safe to ignore.\n"
                
    def test02a_points(self):
        "Testing Point objects."
        prev = GEOSGeometry('POINT(0 0)')
        for p in points:
            # Creating the point from the WKT
            pnt = GEOSGeometry(p.wkt)
            self.assertEqual(pnt.geom_type, 'Point')
            self.assertEqual(pnt.geom_typeid, 0)
            self.assertEqual(p.x, pnt.x)
            self.assertEqual(p.y, pnt.y)
            self.assertEqual(True, pnt == GEOSGeometry(p.wkt))
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
            else:
                self.assertEqual(False, pnt.hasz)
                self.assertEqual(None, pnt.z)
                tup_args = (p.x, p.y)

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
            prev = pnt # setting the previous geometry

    def test02b_multipoints(self):
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

    def test03a_linestring(self):
        "Testing LineString objects."
        prev = GEOSGeometry('POINT(0 0)')
        for l in linestrings:
            ls = GEOSGeometry(l.wkt)
            self.assertEqual(ls.geom_type, 'LineString')
            self.assertEqual(ls.geom_typeid, 1)
            self.assertEqual(ls.empty, False)
            self.assertEqual(ls.ring, False)
            if hasattr(l, 'centroid'):
                self.assertEqual(l.centroid, ls.centroid.tuple)
            if hasattr(l, 'tup'):
                self.assertEqual(l.tup, ls.tuple)
                
            self.assertEqual(True, ls == GEOSGeometry(l.wkt))
            self.assertEqual(False, ls == prev)

            prev = ls

            # Creating a LineString from a tuple, list, and numpy array
            ls2 = LineString(ls.tuple)
            self.assertEqual(ls, ls2)
            ls3 = LineString([list(tup) for tup in ls.tuple])
            self.assertEqual(ls, ls3)
            if HAS_NUMPY:
                ls4 = LineString(array(ls.tuple))
                self.assertEqual(ls, ls4)

    def test03b_multilinestring(self):
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

    def test04a_linearring(self):
        "Testing LinearRing objects."
        for rr in linearrings:
            lr = GEOSGeometry(rr.wkt)
            self.assertEqual(lr.geom_type, 'LinearRing')
            self.assertEqual(lr.geom_typeid, 2)
            self.assertEqual(rr.n_p, len(lr))
            self.assertEqual(True, lr.valid)
            self.assertEqual(False, lr.empty)

            # Creating a LinearRing from a tuple, list, and numpy array
            lr2 = LinearRing(lr.tuple)
            self.assertEqual(lr, lr2)
            lr3 = LinearRing([list(tup) for tup in lr.tuple])
            self.assertEqual(lr, lr3)
            if HAS_NUMPY:
                lr4 = LineString(array(lr.tuple))
                self.assertEqual(lr, lr4)
    
    def test05a_polygons(self):
        "Testing Polygon objects."
        prev = GEOSGeometry('POINT(0 0)')
        for p in polygons:
            # Creating the Polygon, testing its properties.
            poly = GEOSGeometry(p.wkt)
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
            self.assertEqual(True, poly == GEOSGeometry(p.wkt))
            self.assertEqual(False, poly == prev) # Should not be equal to previous geometry

            # Testing the exterior ring
            ring = poly.exterior_ring
            self.assertEqual(ring.geom_type, 'LinearRing')
            self.assertEqual(ring.geom_typeid, 2)
            if p.ext_ring_cs:
                self.assertEqual(p.ext_ring_cs, ring.tuple)
                self.assertEqual(p.ext_ring_cs, poly[0].tuple) # Testing __getitem__

            # Testing __iter__
            for r in poly:
                self.assertEqual(ring.geom_type, 'LinearRing')
                self.assertEqual(ring.geom_typeid, 2)

            # Setting the second point of the first ring (which should set the
            #  first point of the polygon).
            prev = poly.clone() # Using clone() to get a copy of the current polygon
            self.assertEqual(True, poly == prev) # They clone should be equal to the first
            newval = (poly[0][1][0] + 5.0, poly[0][1][1] + 5.0) # really testing __getitem__ ([ring][point][tuple])
            try:
                poly[0][1] = ('cannot assign with', 'string values')
            except TypeError:
                pass
            poly[0][1] = newval # setting the second point in the polygon with the newvalue (based on the old)
            self.assertEqual(newval, poly[0][1]) # The point in the polygon should be the
            self.assertEqual(False, poly == prev) # Even different from the clone we just made
            
    def test05b_multipolygons(self):
        "Testing MultiPolygon objects."
        print "\nBEGIN - expecting GEOS_NOTICE; safe to ignore.\n"
        prev = GEOSGeometry('POINT (0 0)')
        for mp in multipolygons:
            mpoly = GEOSGeometry(mp.wkt)
            self.assertEqual(mpoly.geom_type, 'MultiPolygon')
            self.assertEqual(mpoly.geom_typeid, 6)
            self.assertEqual(mp.valid, mpoly.valid)

            if mp.valid:
                self.assertEqual(mp.num_geom, mpoly.num_geom)
                self.assertEqual(mp.n_p, mpoly.num_coords)
                self.assertEqual(mp.num_geom, len(mpoly))
                for p in mpoly:
                    self.assertEqual(p.geom_type, 'Polygon')
                    self.assertEqual(p.geom_typeid, 3)
                    self.assertEqual(p.valid, True)
        print "\nEND - expecting GEOS_NOTICE; safe to ignore.\n"  

    def test06_memory_hijinks(self):
        "Testing Geometry __del__() in different scenarios"
        #### Memory issues with rings and polygons

        # These tests are needed to ensure sanity with writable geometries.

        # Getting a polygon with interior rings, and pulling out the interior rings
        poly = GEOSGeometry(polygons[1].wkt)
        ring1 = poly[0]
        ring2 = poly[1]

        # These deletes should be 'harmless' since they are done on child geometries
        del ring1 
        del ring2
        ring1 = poly[0]
        ring2 = poly[1]

        # Deleting the polygon
        del poly

        # Ensuring that trying to access the deleted memory (by getting the string
        #  representation of the ring of a deleted polygon) raises a GEOSException
        #  instead of something worse..
        self.assertRaises(GEOSException, str, ring1)
        self.assertRaises(GEOSException, str, ring2)

        #### Memory issues with geometries from Geometry Collections
        mp = GEOSGeometry('MULTIPOINT(85 715, 235 1400, 4620 1711)')
        
        # Getting the points
        pts = [p for p in mp]

        # More 'harmless' child geometry deletes
        for p in pts: del p

        # Cloning for comparisons
        clones = [p.clone() for p in pts]

        for i in xrange(len(clones)):
            # Testing equivalence before & after modification
            self.assertEqual(True, pts[i] == clones[i]) # before
            pts[i].x = 3.14159
            pts[i].y = 2.71828
            self.assertEqual(False, pts[i] == clones[i]) # after
            self.assertEqual(3.14159, mp[i].x) # parent x,y should be modified
            self.assertEqual(2.71828, mp[i].y)

        # Should raise GEOSException when trying to get geometries from the multipoint
        #  after it has been deleted.
        del mp
        for p in pts:
            self.assertRaises(GEOSException, str, p)
        
    def test08_coord_seq(self):
        "Testing Coordinate Sequence objects."
        for p in polygons:
            if p.ext_ring_cs:
                # Constructing the polygon and getting the coordinate sequence
                poly = GEOSGeometry(p.wkt)
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

    def test13_buffer(self):
        "Testing buffer()."
        for i in xrange(len(buffer_geoms)):
            g_tup = buffer_geoms[i]
            g = GEOSGeometry(g_tup[0].wkt)

            # The buffer we expect
            exp_buf = GEOSGeometry(g_tup[1].wkt)

            # Can't use a floating-point for the number of quadsegs.
            self.assertRaises(TypeError, g.buffer, g_tup[2], float(g_tup[3]))

            # Constructing our buffer
            buf = g.buffer(g_tup[2], g_tup[3])
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

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GEOSTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
