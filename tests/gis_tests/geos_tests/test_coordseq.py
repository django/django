import math
from unittest import skipIf
from unittest.mock import patch

from django.contrib.gis.geos import GEOSGeometry, LineString
from django.contrib.gis.geos import prototypes as capi
from django.contrib.gis.geos.coordseq import GEOSCoordSeq
from django.contrib.gis.geos.libgeos import geos_version_tuple
from django.test import SimpleTestCase


class GEOSCoordSeqTest(SimpleTestCase):
    def test_getitem(self):
        coord_seq = LineString([(x, x) for x in range(2)]).coord_seq
        for i in (0, 1):
            with self.subTest(i):
                self.assertEqual(coord_seq[i], (i, i))
        for i in (-3, 10):
            msg = f"Invalid GEOS Geometry index: {i}"
            with self.subTest(i):
                with self.assertRaisesMessage(IndexError, msg):
                    coord_seq[i]

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_has_m(self):
        geom = GEOSGeometry("POINT ZM (1 2 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertIs(coord_seq.hasm, True)

        geom = GEOSGeometry("POINT Z (1 2 3)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertIs(coord_seq.hasm, False)

        geom = GEOSGeometry("POINT M (1 2 3)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertIs(coord_seq.hasm, True)

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_get_set_m(self):
        geom = GEOSGeometry("POINT ZM (1 2 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertEqual(coord_seq.tuple, (1, 2, 3, 4))
        self.assertEqual(coord_seq.getM(0), 4)
        coord_seq.setM(0, 10)
        self.assertEqual(coord_seq.tuple, (1, 2, 3, 10))
        self.assertEqual(coord_seq.getM(0), 10)

        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertEqual(coord_seq.tuple, (1, 2, 4))
        self.assertEqual(coord_seq.getM(0), 4)
        coord_seq.setM(0, 10)
        self.assertEqual(coord_seq.tuple, (1, 2, 10))
        self.assertEqual(coord_seq.getM(0), 10)
        self.assertIs(math.isnan(coord_seq.getZ(0)), True)

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_setitem(self):
        geom = GEOSGeometry("POINT ZM (1 2 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        coord_seq[0] = (10, 20, 30, 40)
        self.assertEqual(coord_seq.tuple, (10, 20, 30, 40))

        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        coord_seq[0] = (10, 20, 40)
        self.assertEqual(coord_seq.tuple, (10, 20, 40))
        self.assertEqual(coord_seq.getM(0), 40)
        self.assertIs(math.isnan(coord_seq.getZ(0)), True)

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_kml_m_dimension(self):
        geom = GEOSGeometry("POINT ZM (1 2 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertEqual(coord_seq.kml, "<coordinates>1.0,2.0,3.0</coordinates>")
        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertEqual(coord_seq.kml, "<coordinates>1.0,2.0,0</coordinates>")

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_clone_m_dimension(self):
        geom = GEOSGeometry("POINT ZM (1 2 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        clone = coord_seq.clone()
        self.assertEqual(clone.tuple, (1, 2, 3, 4))
        self.assertIs(clone.hasz, True)
        self.assertIs(clone.hasm, True)

        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        clone = coord_seq.clone()
        self.assertEqual(clone.tuple, (1, 2, 4))
        self.assertIs(clone.hasz, False)
        self.assertIs(clone.hasm, True)

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_dims(self):
        geom = GEOSGeometry("POINT ZM (1 2 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertEqual(coord_seq.dims, 4)

        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertEqual(coord_seq.dims, 3)

        geom = GEOSGeometry("POINT Z (1 2 3)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertEqual(coord_seq.dims, 3)

        geom = GEOSGeometry("POINT (1 2)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertEqual(coord_seq.dims, 2)

    def test_size(self):
        geom = GEOSGeometry("POINT (1 2)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertEqual(coord_seq.size, 1)

        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=False)
        self.assertEqual(coord_seq.size, 1)

    @skipIf(geos_version_tuple() <= (3, 13), "GEOS M support requires 3.14+")
    def test_iscounterclockwise(self):
        geom = GEOSGeometry("LINEARRING ZM (0 0 3 0, 1 0 0 2, 0 1 1 3, 0 0 3 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        self.assertEqual(
            coord_seq.tuple,
            (
                (0.0, 0.0, 3.0, 0.0),
                (1.0, 0.0, 0.0, 2.0),
                (0.0, 1.0, 1.0, 3.0),
                (0.0, 0.0, 3.0, 4.0),
            ),
        )
        self.assertIs(coord_seq.is_counterclockwise, True)

    def test_m_support_error(self):
        geom = GEOSGeometry("POINT M (1 2 4)")
        coord_seq = GEOSCoordSeq(capi.get_cs(geom.ptr), z=True)
        msg = "GEOSCoordSeq with an M dimension require GEOS 3.14+."

        # mock geos_version_tuple to be 3.13.0
        with patch(
            "django.contrib.gis.geos.coordseq.geos_version_tuple",
            return_value=(3, 13, 0),
        ):
            with self.assertRaisesMessage(NotImplementedError, msg):
                coord_seq.hasm
