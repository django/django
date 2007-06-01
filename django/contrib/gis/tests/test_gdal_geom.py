import unittest
from django.contrib.gis.gdal import OGRGeometry, OGRGeomType, OGRException
from geometries import *

class OGRGeomTest(unittest.TestCase):
    "This tests the OGR Geometry."

    def test00_geomtype(self):
        "Testing OGRGeomType object."

        # OGRGeomType should initialize on all these inputs.
        try:
            g = OGRGeomType(0)
            g = OGRGeomType(1)
            g = OGRGeomType(7)
            g = OGRGeomType('point')
            g = OGRGeomType('GeometrycollectioN')
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
                self.assertEqual(pnt.geom_type, 1)
                self.assertEqual(p.x, pnt.x)
                self.assertEqual(p.y, pnt.y)
                self.assertEqual((p.x, p.y), pnt.tuple)

    def test03_polygons(self):
        "Testing Polygon objects."
        for p in polygons:
            poly = OGRGeometry(p.wkt)
            first = True
            for r in poly:
                if first and p.ext_ring_cs:
                    first = False
                    # Testing the equivilance of the exerior rings
                    #   since the first iteration will be the exterior ring.
                    self.assertEqual(len(p.ext_ring_cs), r.point_count)
                    self.assertEqual(p.ext_ring_cs, r.tuple)

    def test04_multipoints(self):
        "Testing MultiPoint objects."

        for mp in multipoints:
            mgeom1 = OGRGeometry(mp.wkt) # First one from WKT
            mgeom2 = OGRGeometry('MULTIPOINT') # Creating empty multipoint
            for g in mgeom1:
                mgeom2.add(g) # adding each point from the multipoint
            self.assertEqual(mgeom1, mgeom2) # they should equal
    
def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(OGRGeomTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
