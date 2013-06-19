from __future__ import unicode_literals

import binascii
import unittest

from django.contrib.gis import memoryview
from django.utils.unittest import skipUnless

from ..import HAS_GEOS

if HAS_GEOS:
    from .. import GEOSGeometry, WKTReader, WKTWriter, WKBReader, WKBWriter, geos_version_info


@skipUnless(HAS_GEOS, "Geos is required.")
class GEOSIOTest(unittest.TestCase):

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

        # Should only accept six.string_types objects.
        self.assertRaises(TypeError, wkt_r.read, 1)
        self.assertRaises(TypeError, wkt_r.read, memoryview(b'foo'))

    def test02_wktwriter(self):
        # Creating a WKTWriter instance, testing its ptr property.
        wkt_w = WKTWriter()
        self.assertRaises(TypeError, wkt_w._set_ptr, WKTReader.ptr_type())

        ref = GEOSGeometry('POINT (5 23)')
        ref_wkt = 'POINT (5.0000000000000000 23.0000000000000000)'
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
            self.assertRaises(TypeError, wkb_r.read, bad_wkb)

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
            self.assertRaises(ValueError, wkb_w._set_byteorder, bad_byteorder)

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
            # Equivalent of `wkb_w.outdim = bad_outdim`
            self.assertRaises(ValueError, wkb_w._set_outdim, bad_outdim)

        # These tests will fail on 3.0.0 because of a bug that was fixed in 3.1:
        # http://trac.osgeo.org/geos/ticket/216
        if not geos_version_info()['version'].startswith('3.0.'):
            # Now setting the output dimensions to be 3
            wkb_w.outdim = 3

            self.assertEqual(hex3d, wkb_w.write_hex(g))
            self.assertEqual(wkb3d, wkb_w.write(g))

            # Telling the WKBWriter to include the srid in the representation.
            wkb_w.srid = True
            self.assertEqual(hex3d_srid, wkb_w.write_hex(g))
            self.assertEqual(wkb3d_srid, wkb_w.write(g))
