import unittest
from django.contrib.gis.geos import GEOSGeometry, hex_to_wkt, wkt_to_hex, centroid
from geos import geomToWKT, geomToHEX, geomFromWKT, geomFromHEX
from geometries import swig_geoms as geos_geoms

class GeosTest(unittest.TestCase):

    def test001_hex_to_wkt(self):
        "Testing HEX to WKT conversion."
        for g in geos_geoms:
            wkt1 = geomToWKT(geomFromWKT(g.wkt))
            wkt2 = hex_to_wkt(GEOSGeometry(g.wkt, 'wkt').hex)
            self.assertEqual(wkt1, wkt2)

    def test002_wkt_to_hex(self):
        "Testing WKT to HEX conversion."
        for g in geos_geoms:
            self.assertEqual(geomToHEX(geomFromWKT(g.wkt)), wkt_to_hex(g.wkt))

    def test003_centroid(self):
        "Testing the centroid property."
        for g in geos_geoms:
            wkt1 = (centroid(g.wkt, geom_type='wkt')).wkt
            wkt2 = geomToWKT((geomFromWKT(g.wkt)).getCentroid())
            self.assertEqual(wkt1, wkt2)

    def test004_area(self):
        "Testing the area property."
        for g in geos_geoms:
            g1 = geomFromWKT(g.wkt)
            g2 = GEOSGeometry(g.wkt, 'wkt')
            self.assertEqual(g1.area(), g2.area)

    def test005_geom_type(self):
        "Testing the geom_type property."
        for g in geos_geoms:
            g1 = geomFromWKT(g.wkt)
            g2 = GEOSGeometry(g.wkt, 'wkt')
            self.assertEqual(g1.geomType(), g2.geom_type)

    def test005_geom_id(self):
        "Testing the geom_typeid property."
        for g in geos_geoms:
            g1 = geomFromWKT(g.wkt)
            g2 = GEOSGeometry(g.wkt, 'wkt')
            self.assertEqual(g1.typeId(), g2.geom_typeid)

    def test006_ngeom(self):
        "Testing the num_geom property."
        for g in geos_geoms:
            g1 = geomFromWKT(g.wkt)
            g2 = GEOSGeometry(g.wkt, 'wkt')
            self.assertEqual(g1.getNumGeometries(), g2.num_geom)

    def test007_ncoords(self):
        "Testing the num_coords property."
        for g in geos_geoms:
            g2 = GEOSGeometry(g.wkt, 'wkt')
            self.assertEqual(g.ncoords, g2.num_coords)

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(GeosTest))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())
