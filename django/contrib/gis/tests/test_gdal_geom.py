import unittest
from django.contrib.gis.gdal import OGRGeometry, OGRGeomType, OGRException
from geometries import *

class OGRGeomTest(unittest.TestCase):
    "This tests the OGR Geometry."

    def test00_geomtype(self):
        "Testing OGRGeomType object."

        # OGRGeomType should initialize on all these inputs.
        try:
            g = OGRGeomType(1)
            g = OGRGeomType(7)
            g = OGRGeomType('point')
            g = OGRGeomType('GeometrycollectioN')
            g = OGRGeomType('LINearrING')
        except:
            self.fail('Could not create an OGRGeomType object!')

        # Should throw TypeError on this input
        self.assertRaises(TypeError, OGRGeomType.__init__, 23)
        self.assertRaises(TypeError, OGRGeomType.__init__, 'fooD')
        self.assertRaises(TypeError, OGRGeomType.__init__, 9)

        # Equivalence can take strings, ints, and other OGRGeomTypes
        self.assertEqual(True, OGRGeomType(1) == OGRGeomType(1))
        self.assertEqual(True, OGRGeomType(7) == 'GeometryCollection')
        self.assertEqual(True, OGRGeomType('point') == 'POINT')
        self.assertEqual(False, OGRGeomType('point') == 2)
        self.assertEqual(True, OGRGeomType(6) == 'MULtiPolyGON')
        
    def test01_wkt(self):
        "Testing WKT output."
        for g in wkt_out:
            geom = OGRGeometry(g.wkt)

    def test02_points(self):
        "Testing Point objects."

        prev = OGRGeometry('POINT(0 0)')
        for p in points:
            if not hasattr(p, 'z'): # No 3D
                pnt = OGRGeometry(p.wkt)
                self.assertEqual(1, pnt.geom_type)
                self.assertEqual('POINT', pnt.geom_name)
                self.assertEqual(p.x, pnt.x)
                self.assertEqual(p.y, pnt.y)
                self.assertEqual((p.x, p.y), pnt.tuple)

    def test03_multipoints(self):
        "Testing MultiPoint objects."

        for mp in multipoints:
            mgeom1 = OGRGeometry(mp.wkt) # First one from WKT
            self.assertEqual(4, mgeom1.geom_type)
            self.assertEqual('MULTIPOINT', mgeom1.geom_name)
            mgeom2 = OGRGeometry('MULTIPOINT') # Creating empty multipoint
            mgeom3 = OGRGeometry('MULTIPOINT')
            for g in mgeom1:
                mgeom2.add(g) # adding each point from the multipoints
                mgeom3.add(g.wkt) # should take WKT as well
            self.assertEqual(mgeom1, mgeom2) # they should equal
            self.assertEqual(mgeom1, mgeom3)
            self.assertEqual(mp.points, mgeom2.tuple)
            self.assertEqual(mp.n_p, mgeom2.point_count)
                                                                            
    def test04_linestring(self):
        "Testing LineString objects."
        for ls in linestrings:
            linestr = OGRGeometry(ls.wkt)
            self.assertEqual(2, linestr.geom_type)
            self.assertEqual('LINESTRING', linestr.geom_name)
            self.assertEqual(ls.n_p, linestr.point_count)
            self.assertEqual(ls.tup, linestr.tuple)

    def test05_multilinestring(self):
        "Testing MultiLineString objects."
        for mls in multilinestrings:
            mlinestr = OGRGeometry(mls.wkt)
            self.assertEqual(5, mlinestr.geom_type)
            self.assertEqual('MULTILINESTRING', mlinestr.geom_name)
            self.assertEqual(mls.n_p, mlinestr.point_count)
            self.assertEqual(mls.tup, mlinestr.tuple)

    def test06_polygons(self):
        "Testing Polygon objects."
        for p in polygons:
            poly = OGRGeometry(p.wkt)
            self.assertEqual(3, poly.geom_type)
            self.assertEqual('POLYGON', poly.geom_name)
            self.assertEqual(p.n_p, poly.point_count)
            first = True
            for r in poly:
                if first and p.ext_ring_cs:
                    first = False
                    # Testing the equivilance of the exerior rings
                    #   since the first iteration will be the exterior ring.
                    self.assertEqual(len(p.ext_ring_cs), r.point_count)
                    self.assertEqual(p.ext_ring_cs, r.tuple)

    def test07_closepolygons(self):
        "Testing closing Polygon objects."

        # Both rings in this geometry are not closed.
        poly = OGRGeometry('POLYGON((0 0, 5 0, 5 5, 0 5), (1 1, 2 1, 2 2, 2 1))')
        self.assertEqual(8, poly.point_count)
        print "\nBEGIN - expecting IllegalArgumentException; safe to ignore.\n"
        try:
            c = poly.centroid
        except OGRException:
            # Should raise an OGR exception, rings are not closed
            pass
        else:
            self.fail('Should have raised an OGRException!')
        print "\nEND - expecting IllegalArgumentException; safe to ignore.\n"

        # Closing the rings
        poly.close_rings()
        self.assertEqual(10, poly.point_count) # Two closing points should've been added
        self.assertEqual(OGRGeometry('POINT(2.5 2.5)'), poly.centroid)

    def test08_multipolygons(self):
        "Testing MultiPolygon objects."
        for mp in multipolygons:
            mpoly = OGRGeometry(mp.wkt)
            self.assertEqual(6, mpoly.geom_type)
            self.assertEqual('MULTIPOLYGON', mpoly.geom_name)
            if mp.valid:
                self.assertEqual(mp.n_p, mpoly.point_count)
                self.assertEqual(mp.num_geom, len(mpoly))

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(OGRGeomTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
