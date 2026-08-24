import struct

from django.contrib.gis.geos import GEOSGeometry, WKTReader
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.prototypes.io import MAX_GEOM_COLLECTIONS
from django.test import SimpleTestCase


class GEOSLimitTest(SimpleTestCase):
    def _generate_geometry_collection_payloads(self, depth):
        def point(endian="<", type_code=1, dims=2, srid=None):
            marker = b"\x01" if endian == "<" else b"\x00"
            head = marker + struct.pack(f"{endian}I", type_code)
            if srid is not None:
                head += struct.pack(f"{endian}I", srid)
            return head + struct.pack(f"{endian}{'d' * dims}", *((0.0,) * dims))

        def layer(endian="<", type_code=7, srid=None):
            marker = b"\x01" if endian == "<" else b"\x00"
            head = marker + struct.pack(f"{endian}I", type_code)
            if srid is not None:
                head += struct.pack(f"{endian}I", srid)
            return head + struct.pack(f"{endian}I", 1)

        def wkb(coll=7, child=1, dims=2, srid=None):
            return layer(type_code=coll, srid=srid) * depth + point(
                type_code=child, dims=dims, srid=srid
            )

        # (label, collection type code, child type code, child dims, srid, ...
        # check_geos).
        variants = [
            ("ISO WKB Z", 1007, 1001, 3, None, True),
            ("ISO WKB M", 2007, 2001, 3, None, True),
            ("ISO WKB ZM", 3007, 3001, 4, None, True),
            ("EWKB Z", 0x80000007, 0x80000001, 3, None, True),
            ("EWKB M", 0x40000007, 0x40000001, 3, None, True),
            ("EWKB ZM", 0xC0000007, 0xC0000001, 4, None, True),
            ("EWKB SRID", 0x20000007, 0x20000001, 2, 4326, True),
            ("EWKB Z and SRID", 0xA0000007, 0xA0000001, 3, 4326, True),
            ("EWKB ZM and SRID", 0xE0000007, 0xE0000001, 4, 4326, True),
            # Undoc'd high-bit combinations accepted by some GEOS versions.
            # These only verify that Django's limiter recognizes the normalized
            # GeometryCollection type before GEOS parses the payload.
            ("EWKB BBOX", 0x10000007, 0x10000001, 2, None, False),
            ("EWKB BBOX and Z", 0x90000007, 0x90000001, 3, None, False),
            ("EWKB BBOX and M", 0x50000007, 0x50000001, 3, None, False),
            ("EWKB BBOX and ZM", 0xD0000007, 0xD0000001, 4, None, False),
            ("EWKB BBOX and SRID", 0x30000007, 0x30000001, 2, 4326, False),
            ("EWKB BBOX, Z, and SRID", 0xB0000007, 0xB0000001, 3, 4326, False),
            ("EWKB BBOX, M, and SRID", 0x70000007, 0x70000001, 3, 4326, False),
            ("EWKB BBOX, ZM, and SRID", 0xF0000007, 0xF0000001, 4, 4326, False),
            ("EWKB unknown high flag", 0x01000007, 0x01000001, 2, None, False),
        ]
        binary = [
            (layer() * depth + point(), "little-endian WKB", True),
            (layer(endian=">") * depth + point(endian=">"), "big-endian WKB", True),
            (
                b"".join(layer(endian="<" if i % 2 == 0 else ">") for i in range(depth))
                + point(endian=">"),
                "mixed-endian WKB",
                True,
            ),
        ]
        binary += [(wkb(c, ch, d, s), label, cg) for label, c, ch, d, s, cg in variants]

        payloads = []
        for data, label, check_geos in binary:
            payloads += [
                (data.hex().upper(), f"{label}, uppercase hex string", check_geos),
                (data.hex().encode("ascii"), f"{label}, lower hex bytes", check_geos),
                (memoryview(data), f"{label}, memoryview", check_geos),
            ]
        wkt = "GEOMETRYCOLLECTION(" * depth + "POINT(0 0)" + ")" * depth
        payloads += [(wkt, "WKT", True), (wkt.encode("ascii"), "WKT bytes", True)]
        return payloads

    def test_geometry_collection_limit_exceeded(self):
        msg = "contains too many possible GeometryCollections."
        payloads = self._generate_geometry_collection_payloads(depth=6)
        for payload, label, check_geos in payloads:
            with self.subTest(payload=label):
                with self.assertRaisesMessage(ValueError, msg):
                    GEOSGeometry(payload, max_geom_collections=5)
                # Valid cases.
                if check_geos:
                    GEOSGeometry(payload, max_geom_collections=6)
                    GEOSGeometry(payload, max_geom_collections=None)

    def test_wkt_geometry_collection_flat(self):
        def wkt_payload_no_nesting(num_points):
            # Many parentheses, but only one collection level.
            return (
                "GEOMETRYCOLLECTION("
                + ",".join("POINT(0 0)" for _ in range(num_points))
                + ")"
            )

        GEOSGeometry(wkt_payload_no_nesting(num_points=5), max_geom_collections=1)

    def test_wkt_mixed_case_and_inner_whitespace_is_limited(self):
        two_collections = (
            "GEOMETRYCOLLECTION   ( "
            "geometrycollection ( "
            "POINT (0 0), POINT(1 1)"
            ") )"
        )
        msg = "WKT contains too many possible GeometryCollections."
        with self.assertRaisesMessage(ValueError, msg):
            GEOSGeometry(two_collections, max_geom_collections=1)
        GEOSGeometry(two_collections, max_geom_collections=2)

    def test_from_ewkt_leading_whitespace_is_limited(self):
        # from_ewkt() hands the part after the SRID to the low-level reader,
        # so leading whitespace never passes through wkt_regex.
        wkt = " " + "GEOMETRYCOLLECTION(" * 200 + "POINT(0 0)" + ")" * 200
        msg = "WKT contains too many possible GeometryCollections."
        for value in wkt, wkt.encode():
            with self.subTest(value=value):
                with self.assertRaisesMessage(ValueError, msg):
                    GEOSGeometry.from_ewkt(value)

    def test_wkt_dimension_marker_whitespace_is_limited(self):
        def two_collections(separator):
            collection = f"GEOMETRYCOLLECTION{separator}ZM"
            return f"{collection}({collection}(POINT ZM (0 0 0 0)))"

        msg = "WKT contains too many possible GeometryCollections."
        # GEOS accepts any amount of whitespace before the dimension marker.
        for separator in "", " ", "   ":
            with self.subTest(separator=separator):
                value = two_collections(separator)
                with self.assertRaisesMessage(ValueError, msg):
                    GEOSGeometry(value, max_geom_collections=1)
                GEOSGeometry(value, max_geom_collections=2)

    def test_wkt_reader_whitespace_is_limited(self):
        # WKTReader.read() takes str and bytes directly, so the whitespace
        # GEOS tolerates but wkt_regex rejects reaches the limiter.
        reader = WKTReader()
        msg = "WKT contains too many possible GeometryCollections."
        for prefix in "", " ", "\t\n ":
            for separator in "", " ", "   ", "\t", "\n", " \t\n ":
                collection = f"GEOMETRYCOLLECTION{separator}ZM"
                point = "POINT ZM (0 0 0 0)"
                depth = MAX_GEOM_COLLECTIONS + 1
                over = prefix + f"{collection}(" * depth + point + ")" * depth
                with self.subTest(prefix=prefix, separator=separator):
                    for value in over, over.encode():
                        with self.assertRaisesMessage(ValueError, msg):
                            reader.read(value)
                    under = f"{prefix}{collection}({point})"
                    self.assertEqual(reader.read(under).geom_type, "GeometryCollection")

    def test_non_collection_wkt_root_fast_path(self):
        def make_geom(depth):
            return "GEOMETRYCOLLECTION(" * depth + "POINT(0 0)" + ")" * depth

        invalid_wkt = "POLYGON(" + make_geom(6) + ")"
        # Instead of raising a ValueError, a fast path skips the limit and
        # depends on GEOS to reject collections found anywhere but the root.
        with self.assertRaises(GEOSException):
            GEOSGeometry(invalid_wkt, max_geom_collections=5)

    def test_malformed_multi_wkb_child_is_limited(self):
        def make_invalid_geom(depth):
            point = b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", 0.0, 0.0)
            collection = b"\x01" + struct.pack("<I", 7) + struct.pack("<I", 1)
            multipolygon = b"\x01" + struct.pack("<I", 6) + struct.pack("<I", 1)
            return (multipolygon + collection * depth + point).hex().upper()

        msg = "WKB contains too many possible GeometryCollections."
        # Depending on a GEOSException here would be unsafe, because the WKB
        # grammar still allows recursion below the root.
        with self.assertRaisesMessage(ValueError, msg):
            GEOSGeometry(make_invalid_geom(6), max_geom_collections=5)
