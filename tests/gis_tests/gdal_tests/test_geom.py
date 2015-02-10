import json
import unittest
from binascii import b2a_hex
from unittest import skipUnless

from django.contrib.gis.gdal import HAS_GDAL
from django.utils.six.moves import range

from ..test_data import TestDataMixin

try:
    from django.utils.six.moves import cPickle as pickle
except ImportError:
    import pickle


if HAS_GDAL:
    from django.contrib.gis.gdal import (OGRGeometry, OGRGeomType,
        GDALException, OGRIndexError, SpatialReference, CoordTransform,
        GDAL_VERSION)


@skipUnless(HAS_GDAL, "GDAL is required")
class OGRGeomTest(unittest.TestCase, TestDataMixin):
    "This tests the OGR Geometry."

    def test00a_geomtype(self):
        "Testing OGRGeomType object."

        # OGRGeomType should initialize on all these inputs.
        OGRGeomType(1)
        OGRGeomType(7)
        OGRGeomType('point')
        OGRGeomType('GeometrycollectioN')
        OGRGeomType('LINearrING')
        OGRGeomType('Unknown')

        # Should throw TypeError on this input
        self.assertRaises(GDALException, OGRGeomType, 23)
        self.assertRaises(GDALException, OGRGeomType, 'fooD')
        self.assertRaises(GDALException, OGRGeomType, 9)

        # Equivalence can take strings, ints, and other OGRGeomTypes
        self.assertEqual(OGRGeomType(1), OGRGeomType(1))
        self.assertEqual(OGRGeomType(7), 'GeometryCollection')
        self.assertEqual(OGRGeomType('point'), 'POINT')
        self.assertNotEqual(OGRGeomType('point'), 2)
        self.assertEqual(OGRGeomType('unknown'), 0)
        self.assertEqual(OGRGeomType(6), 'MULtiPolyGON')
        self.assertEqual(OGRGeomType(1), OGRGeomType('point'))
        self.assertNotEqual(OGRGeomType('POINT'), OGRGeomType(6))

        # Testing the Django field name equivalent property.
        self.assertEqual('PointField', OGRGeomType('Point').django)
        self.assertEqual('GeometryField', OGRGeomType('Geometry').django)
        self.assertEqual('GeometryField', OGRGeomType('Unknown').django)
        self.assertIsNone(OGRGeomType('none').django)

        # 'Geometry' initialization implies an unknown geometry type.
        gt = OGRGeomType('Geometry')
        self.assertEqual(0, gt.num)
        self.assertEqual('Unknown', gt.name)

    def test00b_geomtype_25d(self):
        "Testing OGRGeomType object with 25D types."
        wkb25bit = OGRGeomType.wkb25bit
        self.assertEqual(OGRGeomType(wkb25bit + 1), 'Point25D')
        self.assertEqual(OGRGeomType('MultiLineString25D'), (5 + wkb25bit))
        self.assertEqual('GeometryCollectionField', OGRGeomType('GeometryCollection25D').django)

    def test01a_wkt(self):
        "Testing WKT output."
        for g in self.geometries.wkt_out:
            geom = OGRGeometry(g.wkt)
            self.assertEqual(g.wkt, geom.wkt)

    def test01a_ewkt(self):
        "Testing EWKT input/output."
        for ewkt_val in ('POINT (1 2 3)', 'LINEARRING (0 0,1 1,2 1,0 0)'):
            # First with ewkt output when no SRID in EWKT
            self.assertEqual(ewkt_val, OGRGeometry(ewkt_val).ewkt)
            # No test consumption with an SRID specified.
            ewkt_val = 'SRID=4326;%s' % ewkt_val
            geom = OGRGeometry(ewkt_val)
            self.assertEqual(ewkt_val, geom.ewkt)
            self.assertEqual(4326, geom.srs.srid)

    def test01b_gml(self):
        "Testing GML output."
        for g in self.geometries.wkt_out:
            geom = OGRGeometry(g.wkt)
            exp_gml = g.gml
            if GDAL_VERSION >= (1, 8):
                # In GDAL 1.8, the non-conformant GML tag  <gml:GeometryCollection> was
                # replaced with <gml:MultiGeometry>.
                exp_gml = exp_gml.replace('GeometryCollection', 'MultiGeometry')
            self.assertEqual(exp_gml, geom.gml)

    def test01c_hex(self):
        "Testing HEX input/output."
        for g in self.geometries.hex_wkt:
            geom1 = OGRGeometry(g.wkt)
            self.assertEqual(g.hex.encode(), geom1.hex)
            # Constructing w/HEX
            geom2 = OGRGeometry(g.hex)
            self.assertEqual(geom1, geom2)

    def test01d_wkb(self):
        "Testing WKB input/output."
        for g in self.geometries.hex_wkt:
            geom1 = OGRGeometry(g.wkt)
            wkb = geom1.wkb
            self.assertEqual(b2a_hex(wkb).upper(), g.hex.encode())
            # Constructing w/WKB.
            geom2 = OGRGeometry(wkb)
            self.assertEqual(geom1, geom2)

    def test01e_json(self):
        "Testing GeoJSON input/output."
        for g in self.geometries.json_geoms:
            geom = OGRGeometry(g.wkt)
            if not hasattr(g, 'not_equal'):
                # Loading jsons to prevent decimal differences
                self.assertEqual(json.loads(g.json), json.loads(geom.json))
                self.assertEqual(json.loads(g.json), json.loads(geom.geojson))
            self.assertEqual(OGRGeometry(g.wkt), OGRGeometry(geom.json))
        # Test input with some garbage content (but valid json) (#15529)
        geom = OGRGeometry('{"type": "Point", "coordinates": [ 100.0, 0.0 ], "other": "<test>"}')
        self.assertIsInstance(geom, OGRGeometry)

    def test02_points(self):
        "Testing Point objects."

        OGRGeometry('POINT(0 0)')
        for p in self.geometries.points:
            if not hasattr(p, 'z'):  # No 3D
                pnt = OGRGeometry(p.wkt)
                self.assertEqual(1, pnt.geom_type)
                self.assertEqual('POINT', pnt.geom_name)
                self.assertEqual(p.x, pnt.x)
                self.assertEqual(p.y, pnt.y)
                self.assertEqual((p.x, p.y), pnt.tuple)

    def test03_multipoints(self):
        "Testing MultiPoint objects."
        for mp in self.geometries.multipoints:
            mgeom1 = OGRGeometry(mp.wkt)  # First one from WKT
            self.assertEqual(4, mgeom1.geom_type)
            self.assertEqual('MULTIPOINT', mgeom1.geom_name)
            mgeom2 = OGRGeometry('MULTIPOINT')  # Creating empty multipoint
            mgeom3 = OGRGeometry('MULTIPOINT')
            for g in mgeom1:
                mgeom2.add(g)  # adding each point from the multipoints
                mgeom3.add(g.wkt)  # should take WKT as well
            self.assertEqual(mgeom1, mgeom2)  # they should equal
            self.assertEqual(mgeom1, mgeom3)
            self.assertEqual(mp.coords, mgeom2.coords)
            self.assertEqual(mp.n_p, mgeom2.point_count)

    def test04_linestring(self):
        "Testing LineString objects."
        prev = OGRGeometry('POINT(0 0)')
        for ls in self.geometries.linestrings:
            linestr = OGRGeometry(ls.wkt)
            self.assertEqual(2, linestr.geom_type)
            self.assertEqual('LINESTRING', linestr.geom_name)
            self.assertEqual(ls.n_p, linestr.point_count)
            self.assertEqual(ls.coords, linestr.tuple)
            self.assertEqual(linestr, OGRGeometry(ls.wkt))
            self.assertNotEqual(linestr, prev)
            self.assertRaises(OGRIndexError, linestr.__getitem__, len(linestr))
            prev = linestr

            # Testing the x, y properties.
            x = [tmpx for tmpx, tmpy in ls.coords]
            y = [tmpy for tmpx, tmpy in ls.coords]
            self.assertEqual(x, linestr.x)
            self.assertEqual(y, linestr.y)

    def test05_multilinestring(self):
        "Testing MultiLineString objects."
        prev = OGRGeometry('POINT(0 0)')
        for mls in self.geometries.multilinestrings:
            mlinestr = OGRGeometry(mls.wkt)
            self.assertEqual(5, mlinestr.geom_type)
            self.assertEqual('MULTILINESTRING', mlinestr.geom_name)
            self.assertEqual(mls.n_p, mlinestr.point_count)
            self.assertEqual(mls.coords, mlinestr.tuple)
            self.assertEqual(mlinestr, OGRGeometry(mls.wkt))
            self.assertNotEqual(mlinestr, prev)
            prev = mlinestr
            for ls in mlinestr:
                self.assertEqual(2, ls.geom_type)
                self.assertEqual('LINESTRING', ls.geom_name)
            self.assertRaises(OGRIndexError, mlinestr.__getitem__, len(mlinestr))

    def test06_linearring(self):
        "Testing LinearRing objects."
        prev = OGRGeometry('POINT(0 0)')
        for rr in self.geometries.linearrings:
            lr = OGRGeometry(rr.wkt)
            # self.assertEqual(101, lr.geom_type.num)
            self.assertEqual('LINEARRING', lr.geom_name)
            self.assertEqual(rr.n_p, len(lr))
            self.assertEqual(lr, OGRGeometry(rr.wkt))
            self.assertNotEqual(lr, prev)
            prev = lr

    def test07a_polygons(self):
        "Testing Polygon objects."

        # Testing `from_bbox` class method
        bbox = (-180, -90, 180, 90)
        p = OGRGeometry.from_bbox(bbox)
        self.assertEqual(bbox, p.extent)

        prev = OGRGeometry('POINT(0 0)')
        for p in self.geometries.polygons:
            poly = OGRGeometry(p.wkt)
            self.assertEqual(3, poly.geom_type)
            self.assertEqual('POLYGON', poly.geom_name)
            self.assertEqual(p.n_p, poly.point_count)
            self.assertEqual(p.n_i + 1, len(poly))

            # Testing area & centroid.
            self.assertAlmostEqual(p.area, poly.area, 9)
            x, y = poly.centroid.tuple
            self.assertAlmostEqual(p.centroid[0], x, 9)
            self.assertAlmostEqual(p.centroid[1], y, 9)

            # Testing equivalence
            self.assertEqual(poly, OGRGeometry(p.wkt))
            self.assertNotEqual(poly, prev)

            if p.ext_ring_cs:
                ring = poly[0]
                self.assertEqual(p.ext_ring_cs, ring.tuple)
                self.assertEqual(p.ext_ring_cs, poly[0].tuple)
                self.assertEqual(len(p.ext_ring_cs), ring.point_count)

            for r in poly:
                self.assertEqual('LINEARRING', r.geom_name)

    def test07b_closepolygons(self):
        "Testing closing Polygon objects."
        # Both rings in this geometry are not closed.
        poly = OGRGeometry('POLYGON((0 0, 5 0, 5 5, 0 5), (1 1, 2 1, 2 2, 2 1))')
        self.assertEqual(8, poly.point_count)
        with self.assertRaises(GDALException):
            poly.centroid

        poly.close_rings()
        self.assertEqual(10, poly.point_count)  # Two closing points should've been added
        self.assertEqual(OGRGeometry('POINT(2.5 2.5)'), poly.centroid)

    def test08_multipolygons(self):
        "Testing MultiPolygon objects."
        OGRGeometry('POINT(0 0)')
        for mp in self.geometries.multipolygons:
            mpoly = OGRGeometry(mp.wkt)
            self.assertEqual(6, mpoly.geom_type)
            self.assertEqual('MULTIPOLYGON', mpoly.geom_name)
            if mp.valid:
                self.assertEqual(mp.n_p, mpoly.point_count)
                self.assertEqual(mp.num_geom, len(mpoly))
                self.assertRaises(OGRIndexError, mpoly.__getitem__, len(mpoly))
                for p in mpoly:
                    self.assertEqual('POLYGON', p.geom_name)
                    self.assertEqual(3, p.geom_type)
            self.assertEqual(mpoly.wkt, OGRGeometry(mp.wkt).wkt)

    def test09a_srs(self):
        "Testing OGR Geometries with Spatial Reference objects."
        for mp in self.geometries.multipolygons:
            # Creating a geometry w/spatial reference
            sr = SpatialReference('WGS84')
            mpoly = OGRGeometry(mp.wkt, sr)
            self.assertEqual(sr.wkt, mpoly.srs.wkt)

            # Ensuring that SRS is propagated to clones.
            klone = mpoly.clone()
            self.assertEqual(sr.wkt, klone.srs.wkt)

            # Ensuring all children geometries (polygons and their rings) all
            # return the assigned spatial reference as well.
            for poly in mpoly:
                self.assertEqual(sr.wkt, poly.srs.wkt)
                for ring in poly:
                    self.assertEqual(sr.wkt, ring.srs.wkt)

            # Ensuring SRS propagate in topological ops.
            a = OGRGeometry(self.geometries.topology_geoms[0].wkt_a, sr)
            b = OGRGeometry(self.geometries.topology_geoms[0].wkt_b, sr)
            diff = a.difference(b)
            union = a.union(b)
            self.assertEqual(sr.wkt, diff.srs.wkt)
            self.assertEqual(sr.srid, union.srs.srid)

            # Instantiating w/an integer SRID
            mpoly = OGRGeometry(mp.wkt, 4326)
            self.assertEqual(4326, mpoly.srid)
            mpoly.srs = SpatialReference(4269)
            self.assertEqual(4269, mpoly.srid)
            self.assertEqual('NAD83', mpoly.srs.name)

            # Incrementing through the multipolygon after the spatial reference
            # has been re-assigned.
            for poly in mpoly:
                self.assertEqual(mpoly.srs.wkt, poly.srs.wkt)
                poly.srs = 32140
                for ring in poly:
                    # Changing each ring in the polygon
                    self.assertEqual(32140, ring.srs.srid)
                    self.assertEqual('NAD83 / Texas South Central', ring.srs.name)
                    ring.srs = str(SpatialReference(4326))  # back to WGS84
                    self.assertEqual(4326, ring.srs.srid)

                    # Using the `srid` property.
                    ring.srid = 4322
                    self.assertEqual('WGS 72', ring.srs.name)
                    self.assertEqual(4322, ring.srid)

    def test09b_srs_transform(self):
        "Testing transform()."
        orig = OGRGeometry('POINT (-104.609 38.255)', 4326)
        trans = OGRGeometry('POINT (992385.4472045 481455.4944650)', 2774)

        # Using an srid, a SpatialReference object, and a CoordTransform object
        # or transformations.
        t1, t2, t3 = orig.clone(), orig.clone(), orig.clone()
        t1.transform(trans.srid)
        t2.transform(SpatialReference('EPSG:2774'))
        ct = CoordTransform(SpatialReference('WGS84'), SpatialReference(2774))
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

    def test09c_transform_dim(self):
        "Testing coordinate dimension is the same on transformed geometries."
        ls_orig = OGRGeometry('LINESTRING(-104.609 38.255)', 4326)
        ls_trans = OGRGeometry('LINESTRING(992385.4472045 481455.4944650)', 2774)

        prec = 3
        ls_orig.transform(ls_trans.srs)
        # Making sure the coordinate dimension is still 2D.
        self.assertEqual(2, ls_orig.coord_dim)
        self.assertAlmostEqual(ls_trans.x[0], ls_orig.x[0], prec)
        self.assertAlmostEqual(ls_trans.y[0], ls_orig.y[0], prec)

    def test10_difference(self):
        "Testing difference()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            d1 = OGRGeometry(self.geometries.diff_geoms[i].wkt)
            d2 = a.difference(b)
            self.assertEqual(d1, d2)
            self.assertEqual(d1, a - b)  # __sub__ is difference operator
            a -= b  # testing __isub__
            self.assertEqual(d1, a)

    def test11_intersection(self):
        "Testing intersects() and intersection()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            i1 = OGRGeometry(self.geometries.intersect_geoms[i].wkt)
            self.assertTrue(a.intersects(b))
            i2 = a.intersection(b)
            self.assertEqual(i1, i2)
            self.assertEqual(i1, a & b)  # __and__ is intersection operator
            a &= b  # testing __iand__
            self.assertEqual(i1, a)

    def test12_symdifference(self):
        "Testing sym_difference()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            d1 = OGRGeometry(self.geometries.sdiff_geoms[i].wkt)
            d2 = a.sym_difference(b)
            self.assertEqual(d1, d2)
            self.assertEqual(d1, a ^ b)  # __xor__ is symmetric difference operator
            a ^= b  # testing __ixor__
            self.assertEqual(d1, a)

    def test13_union(self):
        "Testing union()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            u1 = OGRGeometry(self.geometries.union_geoms[i].wkt)
            u2 = a.union(b)
            self.assertEqual(u1, u2)
            self.assertEqual(u1, a | b)  # __or__ is union operator
            a |= b  # testing __ior__
            self.assertEqual(u1, a)

    def test14_add(self):
        "Testing GeometryCollection.add()."
        # Can't insert a Point into a MultiPolygon.
        mp = OGRGeometry('MultiPolygon')
        pnt = OGRGeometry('POINT(5 23)')
        self.assertRaises(GDALException, mp.add, pnt)

        # GeometryCollection.add may take an OGRGeometry (if another collection
        # of the same type all child geoms will be added individually) or WKT.
        for mp in self.geometries.multipolygons:
            mpoly = OGRGeometry(mp.wkt)
            mp1 = OGRGeometry('MultiPolygon')
            mp2 = OGRGeometry('MultiPolygon')
            mp3 = OGRGeometry('MultiPolygon')

            for poly in mpoly:
                mp1.add(poly)  # Adding a geometry at a time
                mp2.add(poly.wkt)  # Adding WKT
            mp3.add(mpoly)  # Adding a MultiPolygon's entire contents at once.
            for tmp in (mp1, mp2, mp3):
                self.assertEqual(mpoly, tmp)

    def test15_extent(self):
        "Testing `extent` property."
        # The xmin, ymin, xmax, ymax of the MultiPoint should be returned.
        mp = OGRGeometry('MULTIPOINT(5 23, 0 0, 10 50)')
        self.assertEqual((0.0, 0.0, 10.0, 50.0), mp.extent)
        # Testing on the 'real world' Polygon.
        poly = OGRGeometry(self.geometries.polygons[3].wkt)
        ring = poly.shell
        x, y = ring.x, ring.y
        xmin, ymin = min(x), min(y)
        xmax, ymax = max(x), max(y)
        self.assertEqual((xmin, ymin, xmax, ymax), poly.extent)

    def test16_25D(self):
        "Testing 2.5D geometries."
        pnt_25d = OGRGeometry('POINT(1 2 3)')
        self.assertEqual('Point25D', pnt_25d.geom_type.name)
        self.assertEqual(3.0, pnt_25d.z)
        self.assertEqual(3, pnt_25d.coord_dim)
        ls_25d = OGRGeometry('LINESTRING(1 1 1,2 2 2,3 3 3)')
        self.assertEqual('LineString25D', ls_25d.geom_type.name)
        self.assertEqual([1.0, 2.0, 3.0], ls_25d.z)
        self.assertEqual(3, ls_25d.coord_dim)

    def test17_pickle(self):
        "Testing pickle support."
        g1 = OGRGeometry('LINESTRING(1 1 1,2 2 2,3 3 3)', 'WGS84')
        g2 = pickle.loads(pickle.dumps(g1))
        self.assertEqual(g1, g2)
        self.assertEqual(4326, g2.srs.srid)
        self.assertEqual(g1.srs.wkt, g2.srs.wkt)

    def test18_ogrgeometry_transform_workaround(self):
        "Testing coordinate dimensions on geometries after transformation."
        # A bug in GDAL versions prior to 1.7 changes the coordinate
        # dimension of a geometry after it has been transformed.
        # This test ensures that the bug workarounds employed within
        # `OGRGeometry.transform` indeed work.
        wkt_2d = "MULTILINESTRING ((0 0,1 1,2 2))"
        wkt_3d = "MULTILINESTRING ((0 0 0,1 1 1,2 2 2))"
        srid = 4326

        # For both the 2D and 3D MultiLineString, ensure _both_ the dimension
        # of the collection and the component LineString have the expected
        # coordinate dimension after transform.
        geom = OGRGeometry(wkt_2d, srid)
        geom.transform(srid)
        self.assertEqual(2, geom.coord_dim)
        self.assertEqual(2, geom[0].coord_dim)
        self.assertEqual(wkt_2d, geom.wkt)

        geom = OGRGeometry(wkt_3d, srid)
        geom.transform(srid)
        self.assertEqual(3, geom.coord_dim)
        self.assertEqual(3, geom[0].coord_dim)
        self.assertEqual(wkt_3d, geom.wkt)

    def test19_equivalence_regression(self):
        "Testing equivalence methods with non-OGRGeometry instances."
        self.assertIsNotNone(OGRGeometry('POINT(0 0)'))
        self.assertNotEqual(OGRGeometry('LINESTRING(0 0, 1 1)'), 3)
