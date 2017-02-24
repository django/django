import binascii
from unittest import skipUnless

from django.contrib.gis.geos import (
    HAS_GEOS, GEOSGeometry, Point, Polygon, WKBReader, WKBWriter, WKTReader,
    WKTWriter,
)
from django.test import SimpleTestCase


@skipUnless(HAS_GEOS, "Geos is required.")
class GEOSIOTest(SimpleTestCase):

    def test01_wktreader(self):
        # Creating a WKTReader instance
        wkt_r = WKTReader()
        wkt = 'POINT (5 23)'

        # read() should return a GEOSGeometry
        ref = GEOSGeometry(wkt)
        g1 = wkt_r.read(wkt.encode())
        g2 = wkt_r.read(wkt)

        for geom in (g1, g2):
            self.assertEqual(ref, geom)

        # Should only accept string objects.
        with self.assertRaises(TypeError):
            wkt_r.read(1)
        with self.assertRaises(TypeError):
            wkt_r.read(memoryview(b'foo'))

    def test02_wktwriter(self):
        # Creating a WKTWriter instance, testing its ptr property.
        wkt_w = WKTWriter()
        with self.assertRaises(TypeError):
            wkt_w.ptr = WKTReader.ptr_type()

        ref = GEOSGeometry('POINT (5 23)')
        ref_wkt = 'POINT (5.0000000000000000 23.0000000000000000)'
        self.assertEqual(ref_wkt, wkt_w.write(ref).decode())

    def test_wktwriter_constructor_arguments(self):
        wkt_w = WKTWriter(dim=3, trim=True, precision=3)
        ref = GEOSGeometry('POINT (5.34562 23 1.5)')
        ref_wkt = 'POINT Z (5.35 23 1.5)'
        self.assertEqual(ref_wkt, wkt_w.write(ref).decode())

    def test03_wkbreader(self):
        # Creating a WKBReader instance
        wkb_r = WKBReader()

        hex = b'000000000140140000000000004037000000000000'
        wkb = memoryview(binascii.a2b_hex(hex))
        ref = GEOSGeometry(hex)

        # read() should return a GEOSGeometry on either a hex string or
        # a WKB buffer.
        g1 = wkb_r.read(wkb)
        g2 = wkb_r.read(hex)
        for geom in (g1, g2):
            self.assertEqual(ref, geom)

        bad_input = (1, 5.23, None, False)
        for bad_wkb in bad_input:
            with self.assertRaises(TypeError):
                wkb_r.read(bad_wkb)

    def test04_wkbwriter(self):
        wkb_w = WKBWriter()

        # Representations of 'POINT (5 23)' in hex -- one normal and
        # the other with the byte order changed.
        g = GEOSGeometry('POINT (5 23)')
        hex1 = b'010100000000000000000014400000000000003740'
        wkb1 = memoryview(binascii.a2b_hex(hex1))
        hex2 = b'000000000140140000000000004037000000000000'
        wkb2 = memoryview(binascii.a2b_hex(hex2))

        self.assertEqual(hex1, wkb_w.write_hex(g))
        self.assertEqual(wkb1, wkb_w.write(g))

        # Ensuring bad byteorders are not accepted.
        for bad_byteorder in (-1, 2, 523, 'foo', None):
            # Equivalent of `wkb_w.byteorder = bad_byteorder`
            with self.assertRaises(ValueError):
                wkb_w._set_byteorder(bad_byteorder)

        # Setting the byteorder to 0 (for Big Endian)
        wkb_w.byteorder = 0
        self.assertEqual(hex2, wkb_w.write_hex(g))
        self.assertEqual(wkb2, wkb_w.write(g))

        # Back to Little Endian
        wkb_w.byteorder = 1

        # Now, trying out the 3D and SRID flags.
        g = GEOSGeometry('POINT (5 23 17)')
        g.srid = 4326

        hex3d = b'0101000080000000000000144000000000000037400000000000003140'
        wkb3d = memoryview(binascii.a2b_hex(hex3d))
        hex3d_srid = b'01010000A0E6100000000000000000144000000000000037400000000000003140'
        wkb3d_srid = memoryview(binascii.a2b_hex(hex3d_srid))

        # Ensuring bad output dimensions are not accepted
        for bad_outdim in (-1, 0, 1, 4, 423, 'foo', None):
            with self.assertRaisesMessage(ValueError, 'WKB output dimension must be 2 or 3'):
                wkb_w.outdim = bad_outdim

        # Now setting the output dimensions to be 3
        wkb_w.outdim = 3

        self.assertEqual(hex3d, wkb_w.write_hex(g))
        self.assertEqual(wkb3d, wkb_w.write(g))

        # Telling the WKBWriter to include the srid in the representation.
        wkb_w.srid = True
        self.assertEqual(hex3d_srid, wkb_w.write_hex(g))
        self.assertEqual(wkb3d_srid, wkb_w.write(g))

    def test_wkt_writer_trim(self):
        wkt_w = WKTWriter()
        self.assertFalse(wkt_w.trim)
        self.assertEqual(wkt_w.write(Point(1, 1)), b'POINT (1.0000000000000000 1.0000000000000000)')

        wkt_w.trim = True
        self.assertTrue(wkt_w.trim)
        self.assertEqual(wkt_w.write(Point(1, 1)), b'POINT (1 1)')
        self.assertEqual(wkt_w.write(Point(1.1, 1)), b'POINT (1.1 1)')
        self.assertEqual(wkt_w.write(Point(1. / 3, 1)), b'POINT (0.3333333333333333 1)')

        wkt_w.trim = False
        self.assertFalse(wkt_w.trim)
        self.assertEqual(wkt_w.write(Point(1, 1)), b'POINT (1.0000000000000000 1.0000000000000000)')

    def test_wkt_writer_precision(self):
        wkt_w = WKTWriter()
        self.assertIsNone(wkt_w.precision)
        self.assertEqual(wkt_w.write(Point(1. / 3, 2. / 3)), b'POINT (0.3333333333333333 0.6666666666666666)')

        wkt_w.precision = 1
        self.assertEqual(wkt_w.precision, 1)
        self.assertEqual(wkt_w.write(Point(1. / 3, 2. / 3)), b'POINT (0.3 0.7)')

        wkt_w.precision = 0
        self.assertEqual(wkt_w.precision, 0)
        self.assertEqual(wkt_w.write(Point(1. / 3, 2. / 3)), b'POINT (0 1)')

        wkt_w.precision = None
        self.assertIsNone(wkt_w.precision)
        self.assertEqual(wkt_w.write(Point(1. / 3, 2. / 3)), b'POINT (0.3333333333333333 0.6666666666666666)')

        with self.assertRaisesMessage(AttributeError, 'WKT output rounding precision must be '):
            wkt_w.precision = 'potato'

    def test_empty_point_wkb(self):
        p = Point(srid=4326)
        wkb_w = WKBWriter()

        wkb_w.srid = False
        with self.assertRaisesMessage(ValueError, 'Empty point is not representable in WKB.'):
            wkb_w.write(p)
        with self.assertRaisesMessage(ValueError, 'Empty point is not representable in WKB.'):
            wkb_w.write_hex(p)

        wkb_w.srid = True
        for byteorder, hex in enumerate([
            b'0020000001000010E67FF80000000000007FF8000000000000',
            b'0101000020E6100000000000000000F87F000000000000F87F',
        ]):
            wkb_w.byteorder = byteorder
            self.assertEqual(wkb_w.write_hex(p), hex)
            self.assertEqual(GEOSGeometry(wkb_w.write_hex(p)), p)
            self.assertEqual(wkb_w.write(p), memoryview(binascii.a2b_hex(hex)))
            self.assertEqual(GEOSGeometry(wkb_w.write(p)), p)

    def test_empty_polygon_wkb(self):
        p = Polygon(srid=4326)
        p_no_srid = Polygon()
        wkb_w = WKBWriter()
        wkb_w.srid = True
        for byteorder, hexes in enumerate([
            (b'000000000300000000', b'0020000003000010E600000000'),
            (b'010300000000000000', b'0103000020E610000000000000'),
        ]):
            wkb_w.byteorder = byteorder
            for srid, hex in enumerate(hexes):
                wkb_w.srid = srid
                self.assertEqual(wkb_w.write_hex(p), hex)
                self.assertEqual(GEOSGeometry(wkb_w.write_hex(p)), p if srid else p_no_srid)
                self.assertEqual(wkb_w.write(p), memoryview(binascii.a2b_hex(hex)))
                self.assertEqual(GEOSGeometry(wkb_w.write(p)), p if srid else p_no_srid)
