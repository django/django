import json
import pickle

from django.contrib.gis.gdal import (
    CoordTransform,
    GDALException,
    OGRGeometry,
    OGRGeomType,
    SpatialReference,
)
from django.template import Context
from django.template.engine import Engine
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango60Warning

from ..test_data import TestDataMixin


class OGRGeomTest(SimpleTestCase, TestDataMixin):
    "This tests the OGR Geometry."

    def test_geomtype(self):
        "Testing OGRGeomType object."

        # OGRGeomType should initialize on all these inputs.
        OGRGeomType(1)
        OGRGeomType(7)
        OGRGeomType("point")
        OGRGeomType("GeometrycollectioN")
        OGRGeomType("LINearrING")
        OGRGeomType("Unknown")

        # Should throw TypeError on this input
        with self.assertRaises(GDALException):
            OGRGeomType(23)
        with self.assertRaises(GDALException):
            OGRGeomType("fooD")
        with self.assertRaises(GDALException):
            OGRGeomType(4001)

        # Equivalence can take strings, ints, and other OGRGeomTypes
        self.assertEqual(OGRGeomType(1), OGRGeomType(1))
        self.assertEqual(OGRGeomType(7), "GeometryCollection")
        self.assertEqual(OGRGeomType("point"), "POINT")
        self.assertNotEqual(OGRGeomType("point"), 2)
        self.assertEqual(OGRGeomType("unknown"), 0)
        self.assertEqual(OGRGeomType(6), "MULtiPolyGON")
        self.assertEqual(OGRGeomType(1), OGRGeomType("point"))
        self.assertNotEqual(OGRGeomType("POINT"), OGRGeomType(6))

        # Testing the Django field name equivalent property.
        self.assertEqual("PointField", OGRGeomType("Point").django)
        self.assertEqual("GeometryField", OGRGeomType("Geometry").django)
        self.assertEqual("GeometryField", OGRGeomType("Unknown").django)
        self.assertIsNone(OGRGeomType("none").django)

        # 'Geometry' initialization implies an unknown geometry type.
        gt = OGRGeomType("Geometry")
        self.assertEqual(0, gt.num)
        self.assertEqual("Unknown", gt.name)

    def test_geom_type_repr(self):
        self.assertEqual(repr(OGRGeomType("point")), "<OGRGeomType: Point>")

    def test_geomtype_25d(self):
        "Testing OGRGeomType object with 25D types."
        wkb25bit = OGRGeomType.wkb25bit
        self.assertEqual(OGRGeomType(wkb25bit + 1), "Point25D")
        self.assertEqual(OGRGeomType("MultiLineString25D"), (5 + wkb25bit))
        self.assertEqual(
            "GeometryCollectionField", OGRGeomType("GeometryCollection25D").django
        )

    def test_wkt(self):
        "Testing WKT output."
        for g in self.geometries.wkt_out:
            geom = OGRGeometry(g.wkt)
            self.assertEqual(g.wkt, geom.wkt)

    def test_ewkt(self):
        "Testing EWKT input/output."
        for ewkt_val in ("POINT (1 2 3)", "LINEARRING (0 0,1 1,2 1,0 0)"):
            # First with ewkt output when no SRID in EWKT
            self.assertEqual(ewkt_val, OGRGeometry(ewkt_val).ewkt)
            # No test consumption with an SRID specified.
            ewkt_val = "SRID=4326;%s" % ewkt_val
            geom = OGRGeometry(ewkt_val)
            self.assertEqual(ewkt_val, geom.ewkt)
            self.assertEqual(4326, geom.srs.srid)

    def test_gml(self):
        "Testing GML output."
        for g in self.geometries.wkt_out:
            geom = OGRGeometry(g.wkt)
            exp_gml = g.gml
            self.assertEqual(exp_gml, geom.gml)

    def test_hex(self):
        "Testing HEX input/output."
        for g in self.geometries.hex_wkt:
            geom1 = OGRGeometry(g.wkt)
            self.assertEqual(g.hex.encode(), geom1.hex)
            # Constructing w/HEX
            geom2 = OGRGeometry(g.hex)
            self.assertEqual(geom1, geom2)

    def test_wkb(self):
        "Testing WKB input/output."
        for g in self.geometries.hex_wkt:
            geom1 = OGRGeometry(g.wkt)
            wkb = geom1.wkb
            self.assertEqual(wkb.hex().upper(), g.hex)
            # Constructing w/WKB.
            geom2 = OGRGeometry(wkb)
            self.assertEqual(geom1, geom2)

    def test_json(self):
        "Testing GeoJSON input/output."
        for g in self.geometries.json_geoms:
            geom = OGRGeometry(g.wkt)
            if not hasattr(g, "not_equal"):
                # Loading jsons to prevent decimal differences
                self.assertEqual(json.loads(g.json), json.loads(geom.json))
                self.assertEqual(json.loads(g.json), json.loads(geom.geojson))
            self.assertEqual(OGRGeometry(g.wkt), OGRGeometry(geom.json))
        # Test input with some garbage content (but valid json) (#15529)
        geom = OGRGeometry(
            '{"type": "Point", "coordinates": [ 100.0, 0.0 ], "other": "<test>"}'
        )
        self.assertIsInstance(geom, OGRGeometry)

    def test_points(self):
        "Testing Point objects."

        OGRGeometry("POINT(0 0)")
        for p in self.geometries.points:
            if not hasattr(p, "z"):  # No 3D
                pnt = OGRGeometry(p.wkt)
                self.assertEqual(1, pnt.geom_type)
                self.assertEqual("POINT", pnt.geom_name)
                self.assertEqual(p.x, pnt.x)
                self.assertEqual(p.y, pnt.y)
                self.assertEqual((p.x, p.y), pnt.tuple)

    def test_multipoints(self):
        "Testing MultiPoint objects."
        for mp in self.geometries.multipoints:
            mgeom1 = OGRGeometry(mp.wkt)  # First one from WKT
            self.assertEqual(4, mgeom1.geom_type)
            self.assertEqual("MULTIPOINT", mgeom1.geom_name)
            mgeom2 = OGRGeometry("MULTIPOINT")  # Creating empty multipoint
            mgeom3 = OGRGeometry("MULTIPOINT")
            for g in mgeom1:
                mgeom2.add(g)  # adding each point from the multipoints
                mgeom3.add(g.wkt)  # should take WKT as well
            self.assertEqual(mgeom1, mgeom2)  # they should equal
            self.assertEqual(mgeom1, mgeom3)
            self.assertEqual(mp.coords, mgeom2.coords)
            self.assertEqual(mp.n_p, mgeom2.point_count)

    def test_linestring(self):
        "Testing LineString objects."
        prev = OGRGeometry("POINT(0 0)")
        for ls in self.geometries.linestrings:
            linestr = OGRGeometry(ls.wkt)
            self.assertEqual(2, linestr.geom_type)
            self.assertEqual("LINESTRING", linestr.geom_name)
            self.assertEqual(ls.n_p, linestr.point_count)
            self.assertEqual(ls.coords, linestr.tuple)
            self.assertEqual(linestr, OGRGeometry(ls.wkt))
            self.assertNotEqual(linestr, prev)
            msg = "Index out of range when accessing points of a line string: %s."
            with self.assertRaisesMessage(IndexError, msg % len(linestr)):
                linestr.__getitem__(len(linestr))
            prev = linestr

            # Testing the x, y properties.
            x = [tmpx for tmpx, tmpy in ls.coords]
            y = [tmpy for tmpx, tmpy in ls.coords]
            self.assertEqual(x, linestr.x)
            self.assertEqual(y, linestr.y)

    def test_multilinestring(self):
        "Testing MultiLineString objects."
        prev = OGRGeometry("POINT(0 0)")
        for mls in self.geometries.multilinestrings:
            mlinestr = OGRGeometry(mls.wkt)
            self.assertEqual(5, mlinestr.geom_type)
            self.assertEqual("MULTILINESTRING", mlinestr.geom_name)
            self.assertEqual(mls.n_p, mlinestr.point_count)
            self.assertEqual(mls.coords, mlinestr.tuple)
            self.assertEqual(mlinestr, OGRGeometry(mls.wkt))
            self.assertNotEqual(mlinestr, prev)
            prev = mlinestr
            for ls in mlinestr:
                self.assertEqual(2, ls.geom_type)
                self.assertEqual("LINESTRING", ls.geom_name)
            msg = "Index out of range when accessing geometry in a collection: %s."
            with self.assertRaisesMessage(IndexError, msg % len(mlinestr)):
                mlinestr.__getitem__(len(mlinestr))

    def test_linearring(self):
        "Testing LinearRing objects."
        prev = OGRGeometry("POINT(0 0)")
        for rr in self.geometries.linearrings:
            lr = OGRGeometry(rr.wkt)
            # self.assertEqual(101, lr.geom_type.num)
            self.assertEqual("LINEARRING", lr.geom_name)
            self.assertEqual(rr.n_p, len(lr))
            self.assertEqual(lr, OGRGeometry(rr.wkt))
            self.assertNotEqual(lr, prev)
            prev = lr

    def test_polygons(self):
        "Testing Polygon objects."

        # Testing `from_bbox` class method
        bbox = (-180, -90, 180, 90)
        p = OGRGeometry.from_bbox(bbox)
        self.assertEqual(bbox, p.extent)

        prev = OGRGeometry("POINT(0 0)")
        for p in self.geometries.polygons:
            poly = OGRGeometry(p.wkt)
            self.assertEqual(3, poly.geom_type)
            self.assertEqual("POLYGON", poly.geom_name)
            self.assertEqual(p.n_p, poly.point_count)
            self.assertEqual(p.n_i + 1, len(poly))
            msg = "Index out of range when accessing rings of a polygon: %s."
            with self.assertRaisesMessage(IndexError, msg % len(poly)):
                poly.__getitem__(len(poly))

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
                self.assertEqual("LINEARRING", r.geom_name)

    def test_polygons_templates(self):
        # Accessing Polygon attributes in templates should work.
        engine = Engine()
        template = engine.from_string("{{ polygons.0.wkt }}")
        polygons = [OGRGeometry(p.wkt) for p in self.geometries.multipolygons[:2]]
        content = template.render(Context({"polygons": polygons}))
        self.assertIn("MULTIPOLYGON (((100", content)

    def test_closepolygons(self):
        "Testing closing Polygon objects."
        # Both rings in this geometry are not closed.
        poly = OGRGeometry("POLYGON((0 0, 5 0, 5 5, 0 5), (1 1, 2 1, 2 2, 2 1))")
        self.assertEqual(8, poly.point_count)
        with self.assertRaises(GDALException):
            poly.centroid

        poly.close_rings()
        self.assertEqual(
            10, poly.point_count
        )  # Two closing points should've been added
        self.assertEqual(OGRGeometry("POINT(2.5 2.5)"), poly.centroid)

    def test_multipolygons(self):
        "Testing MultiPolygon objects."
        OGRGeometry("POINT(0 0)")
        for mp in self.geometries.multipolygons:
            mpoly = OGRGeometry(mp.wkt)
            self.assertEqual(6, mpoly.geom_type)
            self.assertEqual("MULTIPOLYGON", mpoly.geom_name)
            if mp.valid:
                self.assertEqual(mp.n_p, mpoly.point_count)
                self.assertEqual(mp.num_geom, len(mpoly))
                msg = "Index out of range when accessing geometry in a collection: %s."
                with self.assertRaisesMessage(IndexError, msg % len(mpoly)):
                    mpoly.__getitem__(len(mpoly))
                for p in mpoly:
                    self.assertEqual("POLYGON", p.geom_name)
                    self.assertEqual(3, p.geom_type)
            self.assertEqual(mpoly.wkt, OGRGeometry(mp.wkt).wkt)

    def test_srs(self):
        "Testing OGR Geometries with Spatial Reference objects."
        for mp in self.geometries.multipolygons:
            # Creating a geometry w/spatial reference
            sr = SpatialReference("WGS84")
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
            self.assertEqual("NAD83", mpoly.srs.name)

            # Incrementing through the multipolygon after the spatial reference
            # has been re-assigned.
            for poly in mpoly:
                self.assertEqual(mpoly.srs.wkt, poly.srs.wkt)
                poly.srs = 32140
                for ring in poly:
                    # Changing each ring in the polygon
                    self.assertEqual(32140, ring.srs.srid)
                    self.assertEqual("NAD83 / Texas South Central", ring.srs.name)
                    ring.srs = str(SpatialReference(4326))  # back to WGS84
                    self.assertEqual(4326, ring.srs.srid)

                    # Using the `srid` property.
                    ring.srid = 4322
                    self.assertEqual("WGS 72", ring.srs.name)
                    self.assertEqual(4322, ring.srid)

            # srs/srid may be assigned their own values, even when srs is None.
            mpoly = OGRGeometry(mp.wkt, srs=None)
            mpoly.srs = mpoly.srs
            mpoly.srid = mpoly.srid

    def test_srs_transform(self):
        "Testing transform()."
        orig = OGRGeometry("POINT (-104.609 38.255)", 4326)
        trans = OGRGeometry("POINT (992385.4472045 481455.4944650)", 2774)

        # Using an srid, a SpatialReference object, and a CoordTransform object
        # or transformations.
        t1, t2, t3 = orig.clone(), orig.clone(), orig.clone()
        t1.transform(trans.srid)
        t2.transform(SpatialReference("EPSG:2774"))
        ct = CoordTransform(SpatialReference("WGS84"), SpatialReference(2774))
        t3.transform(ct)

        # Testing use of the `clone` keyword.
        k1 = orig.clone()
        k2 = k1.transform(trans.srid, clone=True)
        self.assertEqual(k1, orig)
        self.assertNotEqual(k1, k2)

        # Different PROJ versions use different transformations, all are
        # correct as having a 1 meter accuracy.
        prec = -1
        for p in (t1, t2, t3, k2):
            self.assertAlmostEqual(trans.x, p.x, prec)
            self.assertAlmostEqual(trans.y, p.y, prec)

    def test_transform_dim(self):
        "Testing coordinate dimension is the same on transformed geometries."
        ls_orig = OGRGeometry("LINESTRING(-104.609 38.255)", 4326)
        ls_trans = OGRGeometry("LINESTRING(992385.4472045 481455.4944650)", 2774)

        # Different PROJ versions use different transformations, all are
        # correct as having a 1 meter accuracy.
        prec = -1
        ls_orig.transform(ls_trans.srs)
        # Making sure the coordinate dimension is still 2D.
        self.assertEqual(2, ls_orig.coord_dim)
        self.assertAlmostEqual(ls_trans.x[0], ls_orig.x[0], prec)
        self.assertAlmostEqual(ls_trans.y[0], ls_orig.y[0], prec)

    def test_difference(self):
        "Testing difference()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            d1 = OGRGeometry(self.geometries.diff_geoms[i].wkt)
            d2 = a.difference(b)
            self.assertTrue(d1.geos.equals(d2.geos))
            self.assertTrue(
                d1.geos.equals((a - b).geos)
            )  # __sub__ is difference operator
            a -= b  # testing __isub__
            self.assertTrue(d1.geos.equals(a.geos))

    def test_intersection(self):
        "Testing intersects() and intersection()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            i1 = OGRGeometry(self.geometries.intersect_geoms[i].wkt)
            self.assertTrue(a.intersects(b))
            i2 = a.intersection(b)
            self.assertTrue(i1.geos.equals(i2.geos))
            self.assertTrue(
                i1.geos.equals((a & b).geos)
            )  # __and__ is intersection operator
            a &= b  # testing __iand__
            self.assertTrue(i1.geos.equals(a.geos))

    def test_symdifference(self):
        "Testing sym_difference()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            d1 = OGRGeometry(self.geometries.sdiff_geoms[i].wkt)
            d2 = a.sym_difference(b)
            self.assertTrue(d1.geos.equals(d2.geos))
            self.assertTrue(
                d1.geos.equals((a ^ b).geos)
            )  # __xor__ is symmetric difference operator
            a ^= b  # testing __ixor__
            self.assertTrue(d1.geos.equals(a.geos))

    def test_union(self):
        "Testing union()."
        for i in range(len(self.geometries.topology_geoms)):
            a = OGRGeometry(self.geometries.topology_geoms[i].wkt_a)
            b = OGRGeometry(self.geometries.topology_geoms[i].wkt_b)
            u1 = OGRGeometry(self.geometries.union_geoms[i].wkt)
            u2 = a.union(b)
            self.assertTrue(u1.geos.equals(u2.geos))
            self.assertTrue(u1.geos.equals((a | b).geos))  # __or__ is union operator
            a |= b  # testing __ior__
            self.assertTrue(u1.geos.equals(a.geos))

    def test_add(self):
        "Testing GeometryCollection.add()."
        # Can't insert a Point into a MultiPolygon.
        mp = OGRGeometry("MultiPolygon")
        pnt = OGRGeometry("POINT(5 23)")
        with self.assertRaises(GDALException):
            mp.add(pnt)

        # GeometryCollection.add may take an OGRGeometry (if another collection
        # of the same type all child geoms will be added individually) or WKT.
        for mp in self.geometries.multipolygons:
            mpoly = OGRGeometry(mp.wkt)
            mp1 = OGRGeometry("MultiPolygon")
            mp2 = OGRGeometry("MultiPolygon")
            mp3 = OGRGeometry("MultiPolygon")

            for poly in mpoly:
                mp1.add(poly)  # Adding a geometry at a time
                mp2.add(poly.wkt)  # Adding WKT
            mp3.add(mpoly)  # Adding a MultiPolygon's entire contents at once.
            for tmp in (mp1, mp2, mp3):
                self.assertEqual(mpoly, tmp)

    def test_extent(self):
        "Testing `extent` property."
        # The xmin, ymin, xmax, ymax of the MultiPoint should be returned.
        mp = OGRGeometry("MULTIPOINT(5 23, 0 0, 10 50)")
        self.assertEqual((0.0, 0.0, 10.0, 50.0), mp.extent)
        # Testing on the 'real world' Polygon.
        poly = OGRGeometry(self.geometries.polygons[3].wkt)
        ring = poly.shell
        x, y = ring.x, ring.y
        xmin, ymin = min(x), min(y)
        xmax, ymax = max(x), max(y)
        self.assertEqual((xmin, ymin, xmax, ymax), poly.extent)

    def test_25D(self):
        "Testing 2.5D geometries."
        pnt_25d = OGRGeometry("POINT(1 2 3)")
        self.assertEqual("Point25D", pnt_25d.geom_type.name)
        self.assertEqual(3.0, pnt_25d.z)
        self.assertEqual(3, pnt_25d.coord_dim)
        ls_25d = OGRGeometry("LINESTRING(1 1 1,2 2 2,3 3 3)")
        self.assertEqual("LineString25D", ls_25d.geom_type.name)
        self.assertEqual([1.0, 2.0, 3.0], ls_25d.z)
        self.assertEqual(3, ls_25d.coord_dim)

    def test_pickle(self):
        "Testing pickle support."
        g1 = OGRGeometry("LINESTRING(1 1 1,2 2 2,3 3 3)", "WGS84")
        g2 = pickle.loads(pickle.dumps(g1))
        self.assertEqual(g1, g2)
        self.assertEqual(4326, g2.srs.srid)
        self.assertEqual(g1.srs.wkt, g2.srs.wkt)

    def test_ogrgeometry_transform_workaround(self):
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

    # Testing binary predicates, `assertIs` is used to check that bool is returned.

    def test_equivalence_regression(self):
        "Testing equivalence methods with non-OGRGeometry instances."
        self.assertIsNotNone(OGRGeometry("POINT(0 0)"))
        self.assertNotEqual(OGRGeometry("LINESTRING(0 0, 1 1)"), 3)

    def test_contains(self):
        self.assertIs(
            OGRGeometry("POINT(0 0)").contains(OGRGeometry("POINT(0 0)")), True
        )
        self.assertIs(
            OGRGeometry("POINT(0 0)").contains(OGRGeometry("POINT(0 1)")), False
        )

    def test_crosses(self):
        self.assertIs(
            OGRGeometry("LINESTRING(0 0, 1 1)").crosses(
                OGRGeometry("LINESTRING(0 1, 1 0)")
            ),
            True,
        )
        self.assertIs(
            OGRGeometry("LINESTRING(0 0, 0 1)").crosses(
                OGRGeometry("LINESTRING(1 0, 1 1)")
            ),
            False,
        )

    def test_disjoint(self):
        self.assertIs(
            OGRGeometry("LINESTRING(0 0, 1 1)").disjoint(
                OGRGeometry("LINESTRING(0 1, 1 0)")
            ),
            False,
        )
        self.assertIs(
            OGRGeometry("LINESTRING(0 0, 0 1)").disjoint(
                OGRGeometry("LINESTRING(1 0, 1 1)")
            ),
            True,
        )

    def test_equals(self):
        self.assertIs(
            OGRGeometry("POINT(0 0)").contains(OGRGeometry("POINT(0 0)")), True
        )
        self.assertIs(
            OGRGeometry("POINT(0 0)").contains(OGRGeometry("POINT(0 1)")), False
        )

    def test_intersects(self):
        self.assertIs(
            OGRGeometry("LINESTRING(0 0, 1 1)").intersects(
                OGRGeometry("LINESTRING(0 1, 1 0)")
            ),
            True,
        )
        self.assertIs(
            OGRGeometry("LINESTRING(0 0, 0 1)").intersects(
                OGRGeometry("LINESTRING(1 0, 1 1)")
            ),
            False,
        )

    def test_overlaps(self):
        self.assertIs(
            OGRGeometry("POLYGON ((0 0, 0 2, 2 2, 2 0, 0 0))").overlaps(
                OGRGeometry("POLYGON ((1 1, 1 5, 5 5, 5 1, 1 1))")
            ),
            True,
        )
        self.assertIs(
            OGRGeometry("POINT(0 0)").overlaps(OGRGeometry("POINT(0 1)")), False
        )

    def test_touches(self):
        self.assertIs(
            OGRGeometry("POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))").touches(
                OGRGeometry("LINESTRING(0 2, 2 0)")
            ),
            True,
        )
        self.assertIs(
            OGRGeometry("POINT(0 0)").touches(OGRGeometry("POINT(0 1)")), False
        )

    def test_within(self):
        self.assertIs(
            OGRGeometry("POINT(0.5 0.5)").within(
                OGRGeometry("POLYGON ((0 0, 0 1, 1 1, 1 0, 0 0))")
            ),
            True,
        )
        self.assertIs(
            OGRGeometry("POINT(0 0)").within(OGRGeometry("POINT(0 1)")), False
        )

    def test_from_gml(self):
        self.assertEqual(
            OGRGeometry("POINT(0 0)"),
            OGRGeometry.from_gml(
                '<gml:Point gml:id="p21" '
                'srsName="http://www.opengis.net/def/crs/EPSG/0/4326">'
                '    <gml:pos srsDimension="2">0 0</gml:pos>'
                "</gml:Point>"
            ),
        )

    def test_empty(self):
        self.assertIs(OGRGeometry("POINT (0 0)").empty, False)
        self.assertIs(OGRGeometry("POINT EMPTY").empty, True)

    def test_empty_point_to_geos(self):
        p = OGRGeometry("POINT EMPTY", srs=4326)
        self.assertEqual(p.geos.ewkt, p.ewkt)

    def test_geometry_types(self):
        tests = [
            ("Point", 1, True),
            ("LineString", 2, True),
            ("Polygon", 3, True),
            ("MultiPoint", 4, True),
            ("Multilinestring", 5, True),
            ("MultiPolygon", 6, True),
            ("GeometryCollection", 7, True),
            ("CircularString", 8, False),
            ("CompoundCurve", 9, False),
            ("CurvePolygon", 10, False),
            ("MultiCurve", 11, False),
            ("MultiSurface", 12, False),
            # 13 (Curve) and 14 (Surface) are abstract types.
            ("PolyhedralSurface", 15, False),
            ("TIN", 16, False),
            ("Triangle", 17, False),
            ("Linearring", 2, True),
            # Types 1 - 7 with Z dimension have 2.5D enums.
            ("Point Z", -2147483647, True),  # 1001
            ("LineString Z", -2147483646, True),  # 1002
            ("Polygon Z", -2147483645, True),  # 1003
            ("MultiPoint Z", -2147483644, True),  # 1004
            ("Multilinestring Z", -2147483643, True),  # 1005
            ("MultiPolygon Z", -2147483642, True),  # 1006
            ("GeometryCollection Z", -2147483641, True),  # 1007
            ("CircularString Z", 1008, False),
            ("CompoundCurve Z", 1009, False),
            ("CurvePolygon Z", 1010, False),
            ("MultiCurve Z", 1011, False),
            ("MultiSurface Z", 1012, False),
            ("PolyhedralSurface Z", 1015, False),
            ("TIN Z", 1016, False),
            ("Triangle Z", 1017, False),
            ("Point M", 2001, True),
            ("LineString M", 2002, True),
            ("Polygon M", 2003, True),
            ("MultiPoint M", 2004, True),
            ("MultiLineString M", 2005, True),
            ("MultiPolygon M", 2006, True),
            ("GeometryCollection M", 2007, True),
            ("CircularString M", 2008, False),
            ("CompoundCurve M", 2009, False),
            ("CurvePolygon M", 2010, False),
            ("MultiCurve M", 2011, False),
            ("MultiSurface M", 2012, False),
            ("PolyhedralSurface M", 2015, False),
            ("TIN M", 2016, False),
            ("Triangle M", 2017, False),
            ("Point ZM", 3001, True),
            ("LineString ZM", 3002, True),
            ("Polygon ZM", 3003, True),
            ("MultiPoint ZM", 3004, True),
            ("MultiLineString ZM", 3005, True),
            ("MultiPolygon ZM", 3006, True),
            ("GeometryCollection ZM", 3007, True),
            ("CircularString ZM", 3008, False),
            ("CompoundCurve ZM", 3009, False),
            ("CurvePolygon ZM", 3010, False),
            ("MultiCurve ZM", 3011, False),
            ("MultiSurface ZM", 3012, False),
            ("PolyhedralSurface ZM", 3015, False),
            ("TIN ZM", 3016, False),
            ("Triangle ZM", 3017, False),
        ]

        for test in tests:
            geom_type, num, supported = test
            with self.subTest(geom_type=geom_type, num=num, supported=supported):
                if supported:
                    g = OGRGeometry(f"{geom_type} EMPTY")
                    self.assertEqual(g.geom_type.num, num)
                else:
                    type_ = geom_type.replace(" ", "")
                    msg = f"Unsupported geometry type: {type_}"
                    with self.assertRaisesMessage(TypeError, msg):
                        OGRGeometry(f"{geom_type} EMPTY")

    def test_is_3d_and_set_3d(self):
        geom = OGRGeometry("POINT (1 2)")
        self.assertIs(geom.is_3d, False)
        geom.set_3d(True)
        self.assertIs(geom.is_3d, True)
        self.assertEqual(geom.wkt, "POINT (1 2 0)")
        geom.set_3d(False)
        self.assertIs(geom.is_3d, False)
        self.assertEqual(geom.wkt, "POINT (1 2)")
        msg = "Input to 'set_3d' must be a boolean, got 'None'"
        with self.assertRaisesMessage(ValueError, msg):
            geom.set_3d(None)

    def test_wkt_and_wkb_output(self):
        tests = [
            # 2D
            ("POINT (1 2)", "0101000000000000000000f03f0000000000000040"),
            (
                "LINESTRING (30 10,10 30)",
                "0102000000020000000000000000003e400000000000002"
                "44000000000000024400000000000003e40",
            ),
            (
                "POLYGON ((30 10,40 40,20 40,30 10))",
                "010300000001000000040000000000000000003e400000000000002440000000000000"
                "44400000000000004440000000000000344000000000000044400000000000003e4000"
                "00000000002440",
            ),
            (
                "MULTIPOINT (10 40,40 30)",
                "0104000000020000000101000000000000000000244000000000000044400101000000"
                "00000000000044400000000000003e40",
            ),
            (
                "MULTILINESTRING ((10 10,20 20),(40 40,30 30,40 20))",
                "0105000000020000000102000000020000000000000000002440000000000000244000"
                "0000000000344000000000000034400102000000030000000000000000004440000000"
                "00000044400000000000003e400000000000003e400000000000004440000000000000"
                "3440",
            ),
            (
                "MULTIPOLYGON (((30 20,45 40,10 40,30 20)),((15 5,40 10,10 20,15 5)))",
                "010600000002000000010300000001000000040000000000000000003e400000000000"
                "0034400000000000804640000000000000444000000000000024400000000000004440"
                "0000000000003e40000000000000344001030000000100000004000000000000000000"
                "2e40000000000000144000000000000044400000000000002440000000000000244000"
                "000000000034400000000000002e400000000000001440",
            ),
            (
                "GEOMETRYCOLLECTION (POINT (40 10))",
                "010700000001000000010100000000000000000044400000000000002440",
            ),
            # 3D
            (
                "POINT (1 2 3)",
                "0101000080000000000000f03f00000000000000400000000000000840",
            ),
            (
                "LINESTRING (30 10 3,10 30 3)",
                "0102000080020000000000000000003e40000000000000244000000000000008400000"
                "0000000024400000000000003e400000000000000840",
            ),
            (
                "POLYGON ((30 10 3,40 40 3,30 10 3))",
                "010300008001000000030000000000000000003e400000000000002440000000000000"
                "08400000000000004440000000000000444000000000000008400000000000003e4000"
                "000000000024400000000000000840",
            ),
            (
                "MULTIPOINT (10 40 3,40 30 3)",
                "0104000080020000000101000080000000000000244000000000000044400000000000"
                "000840010100008000000000000044400000000000003e400000000000000840",
            ),
            (
                "MULTILINESTRING ((10 10 3,20 20 3))",
                "0105000080010000000102000080020000000000000000002440000000000000244000"
                "00000000000840000000000000344000000000000034400000000000000840",
            ),
            (
                "MULTIPOLYGON (((30 20 3,45 40 3,30 20 3)))",
                "010600008001000000010300008001000000030000000000000000003e400000000000"
                "0034400000000000000840000000000080464000000000000044400000000000000840"
                "0000000000003e4000000000000034400000000000000840",
            ),
            (
                "GEOMETRYCOLLECTION (POINT (40 10 3))",
                "0107000080010000000101000080000000000000444000000000000024400000000000"
                "000840",
            ),
        ]
        for geom, wkb in tests:
            with self.subTest(geom=geom):
                g = OGRGeometry(geom)
                self.assertEqual(g.wkt, geom)
                self.assertEqual(g.wkb.hex(), wkb)

    def test_measure_is_measure_and_set_measure(self):
        geom = OGRGeometry("POINT (1 2 3)")
        self.assertIs(geom.is_measured, False)
        geom.set_measured(True)
        self.assertIs(geom.is_measured, True)
        self.assertEqual(geom.wkt, "POINT ZM (1 2 3 0)")
        geom.set_measured(False)
        self.assertIs(geom.is_measured, False)
        self.assertEqual(geom.wkt, "POINT (1 2 3)")
        msg = "Input to 'set_measured' must be a boolean, got 'None'"
        with self.assertRaisesMessage(ValueError, msg):
            geom.set_measured(None)

    def test_point_m_coordinate(self):
        geom = OGRGeometry("POINT ZM (1 2 3 4)")
        self.assertEqual(geom.m, 4)
        geom = OGRGeometry("POINT (1 2 3 4)")
        self.assertEqual(geom.m, 4)
        geom = OGRGeometry("POINT M (1 2 3)")
        self.assertEqual(geom.m, 3)
        geom = OGRGeometry("POINT Z (1 2 3)")
        self.assertEqual(geom.m, None)

    def test_point_m_tuple(self):
        geom = OGRGeometry("POINT ZM (1 2 3 4)")
        self.assertEqual(geom.tuple, (geom.x, geom.y, geom.z, geom.m))
        geom = OGRGeometry("POINT M (1 2 3)")
        self.assertEqual(geom.tuple, (geom.x, geom.y, geom.m))
        geom = OGRGeometry("POINT Z (1 2 3)")
        self.assertEqual(geom.tuple, (geom.x, geom.y, geom.z))
        geom = OGRGeometry("POINT (1 2 3)")
        self.assertEqual(geom.tuple, (geom.x, geom.y, geom.z))

    def test_point_m_wkt_wkb(self):
        wkt = "POINT ZM (1 2 3 4)"
        geom = OGRGeometry(wkt)
        self.assertEqual(geom.wkt, wkt)
        self.assertEqual(
            geom.wkb.hex(),
            "01b90b0000000000000000f03f00000000000000"
            "4000000000000008400000000000001040",
        )
        wkt = "POINT M (1 2 3)"
        geom = OGRGeometry(wkt)
        self.assertEqual(geom.wkt, wkt)
        self.assertEqual(
            geom.wkb.hex(),
            "01d1070000000000000000f03f00000000000000400000000000000840",
        )

    def test_point_m_dimension_types(self):
        geom = OGRGeometry("POINT ZM (1 2 3 4)")
        self.assertEqual(geom.geom_type.name, "PointZM")
        self.assertEqual(geom.geom_type.num, 3001)
        geom = OGRGeometry("POINT M (1 2 3)")
        self.assertEqual(geom.geom_type.name, "PointM")
        self.assertEqual(geom.geom_type.num, 2001)

    def test_point_m_dimension_geos(self):
        """GEOSGeometry does not yet support the M dimension."""
        geom = OGRGeometry("POINT ZM (1 2 3 4)")
        self.assertEqual(geom.geos.wkt, "POINT Z (1 2 3)")
        geom = OGRGeometry("POINT M (1 2 3)")
        self.assertEqual(geom.geos.wkt, "POINT (1 2)")

    def test_centroid(self):
        point = OGRGeometry("POINT (1 2 3)")
        self.assertEqual(point.centroid.wkt, "POINT (1 2)")
        linestring = OGRGeometry("LINESTRING (0 0 0, 1 1 1, 2 2 2)")
        self.assertEqual(linestring.centroid.wkt, "POINT (1 1)")
        polygon = OGRGeometry("POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))")
        self.assertEqual(polygon.centroid.wkt, "POINT (5 5)")
        multipoint = OGRGeometry("MULTIPOINT (0 0,10 10)")
        self.assertEqual(multipoint.centroid.wkt, "POINT (5 5)")
        multilinestring = OGRGeometry(
            "MULTILINESTRING ((0 0,0 10,0 20),(10 0,10 10,10 20))"
        )
        self.assertEqual(multilinestring.centroid.wkt, "POINT (5 10)")
        multipolygon = OGRGeometry(
            "MULTIPOLYGON(((0 0, 10 0, 10 10, 0 10, 0 0)),"
            "((20 20, 20 30, 30 30, 30 20, 20 20)))"
        )
        self.assertEqual(multipolygon.centroid.wkt, "POINT (15 15)")
        geometrycollection = OGRGeometry(
            "GEOMETRYCOLLECTION (POINT (110 260),LINESTRING (110 0,110 60))"
        )
        self.assertEqual(geometrycollection.centroid.wkt, "POINT (110 30)")

    def test_linestring_m_dimension(self):
        geom = OGRGeometry("LINESTRING(0 1 2 10, 1 2 3 11, 2 3 4 12)")
        self.assertIs(geom.is_measured, True)
        self.assertEqual(geom.m, [10.0, 11.0, 12.0])
        self.assertEqual(geom[0], (0.0, 1.0, 2.0, 10.0))

        geom = OGRGeometry("LINESTRING M (0 1 10, 1 2 11)")
        self.assertIs(geom.is_measured, True)
        self.assertEqual(geom.m, [10.0, 11.0])
        self.assertEqual(geom[0], (0.0, 1.0, 10.0))

        geom.set_measured(False)
        self.assertIs(geom.is_measured, False)
        self.assertIs(geom.m, None)

    def test_polygon_m_dimension(self):
        geom = OGRGeometry("POLYGON Z ((0 0 0, 10 0 0, 10 10 0, 0 10 0, 0 0 0))")
        self.assertIs(geom.is_measured, False)
        self.assertEqual(
            geom.shell.wkt, "LINEARRING (0 0 0,10 0 0,10 10 0,0 10 0,0 0 0)"
        )

        geom = OGRGeometry("POLYGON M ((0 0 0, 10 0 0, 10 10 0, 0 10 0, 0 0 0))")
        self.assertIs(geom.is_measured, True)
        self.assertEqual(
            geom.shell.wkt, "LINEARRING M (0 0 0,10 0 0,10 10 0,0 10 0,0 0 0)"
        )

        geom = OGRGeometry(
            "POLYGON ZM ((0 0 0 1, 10 0 0 1, 10 10 0 1, 0 10 0 1, 0 0 0 1))"
        )
        self.assertIs(geom.is_measured, True)
        self.assertEqual(
            geom.shell.wkt,
            "LINEARRING ZM (0 0 0 1,10 0 0 1,10 10 0 1,0 10 0 1,0 0 0 1)",
        )

        geom.set_measured(False)
        self.assertEqual(geom.wkt, "POLYGON ((0 0 0,10 0 0,10 10 0,0 10 0,0 0 0))")
        self.assertEqual(
            geom.shell.wkt, "LINEARRING (0 0 0,10 0 0,10 10 0,0 10 0,0 0 0)"
        )

    def test_multi_geometries_m_dimension(self):
        tests = [
            "MULTIPOINT M ((10 40 10), (40 30 10), (20 20 10))",
            "MULTIPOINT ZM ((10 40 0 10), (40 30 1 10), (20 20 1 10))",
            "MULTILINESTRING M ((10 10 1, 20 20 2),(40 40 1, 30 30 2))",
            "MULTILINESTRING ZM ((10 10 0 1, 20 20 0 2),(40 40 1, 30 30 0 2))",
            (
                "MULTIPOLYGON ZM (((30 20 1 0, 45 40 1 0, 30 20 1 0)),"
                "((15 5 0 0, 40 10 0 0, 15 5 0 0)))"
            ),
            (
                "GEOMETRYCOLLECTION M (POINT M (40 10 0),"
                "LINESTRING M (10 10 0, 20 20 0, 10 40 0))"
            ),
            (
                "GEOMETRYCOLLECTION ZM (POINT ZM (40 10 0 1),"
                "LINESTRING ZM (10 10 1 0, 20 20 1 0, 10 40 1 0))"
            ),
        ]
        for geom_input in tests:
            with self.subTest(geom_input=geom_input):
                geom = OGRGeometry(geom_input)
                self.assertIs(geom.is_measured, True)


class DeprecationTests(SimpleTestCase):
    def test_coord_setter_deprecation(self):
        geom = OGRGeometry("POINT (1 2)")
        msg = "coord_dim setter is deprecated. Use set_3d() instead."
        with self.assertWarnsMessage(RemovedInDjango60Warning, msg) as ctx:
            geom.coord_dim = 3
        self.assertEqual(geom.coord_dim, 3)
        self.assertEqual(ctx.filename, __file__)
