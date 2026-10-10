import struct

from django.contrib.gis.geos import GEOSGeometry, WKTReader
from django.contrib.gis.geos.error import GEOSException
from django.contrib.gis.geos.prototypes.io import MAX_GEOM_COLLECTIONS
from django.test import SimpleTestCase


class GEOSLimitTest(SimpleTestCase):
    @staticmethod
    def _wkb_representations(data):
        return [
            (data.hex().upper(), "uppercase hex string"),
            (data.hex().encode("ascii"), "lower hex bytes"),
            (memoryview(data), "memoryview"),
        ]

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
                layer(endian=">", type_code=1007) * depth
                + point(endian=">", type_code=1001, dims=3),
                "big-endian ISO WKB Z",
                True,
            ),
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
                (payload, f"{label}, {representation}", check_geos)
                for payload, representation in self._wkb_representations(data)
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

    def test_invalid_wkb_byte_order(self):
        big_endian_layer = b"\x00" + struct.pack(">II", 7, 1)
        big_endian_point = b"\x00" + struct.pack(">I", 1) + struct.pack(">dd", 0.0, 0.0)
        big_endian = (big_endian_layer * 6 + big_endian_point).replace(
            b"\x00", b"\x02", 1
        )
        little_endian_layer = b"\x01" + struct.pack("<II", 7, 1)
        invalid_little_endian_layer = b"\x02" + struct.pack("<II", 7, 1)
        little_endian_point = (
            b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", 0.0, 0.0)
        )
        nested = (
            little_endian_layer + invalid_little_endian_layer * 6 + little_endian_point
        )
        for data, label in (
            (big_endian, "invalid root byte order"),
            (nested, "invalid nested byte order"),
        ):
            for payload, representation in self._wkb_representations(data):
                with (
                    self.subTest(payload=f"{label}, {representation}"),
                    self.assertRaisesMessage(GEOSException, "Invalid WKB input."),
                ):
                    GEOSGeometry(payload, max_geom_collections=5)

    def test_wkb_header_bytes_in_coordinates(self):
        possible_collection_header = b"\x01\x07\x00\x00\x00\x00\x00\x00"
        data = (
            b"\x01"
            + struct.pack("<II", 2, 2)
            + possible_collection_header
            + struct.pack("<d", 0.0)
            + possible_collection_header
            + struct.pack("<d", 1.0)
        )
        for payload, representation in self._wkb_representations(data):
            with self.subTest(payload=representation):
                geom = GEOSGeometry(payload, max_geom_collections=0)
                self.assertEqual(geom.geom_type, "LineString")

    def test_wkb_geometry_collection_breadth(self):
        empty_collection = b"\x01" + struct.pack("<II", 7, 0)
        num_geometries = MAX_GEOM_COLLECTIONS + 1
        data = (
            b"\x01"
            + struct.pack("<II", 7, num_geometries)
            + empty_collection * num_geometries
        )
        for payload, representation in self._wkb_representations(data):
            with self.subTest(payload=representation):
                GEOSGeometry(payload, max_geom_collections=2)
                with self.assertRaisesMessage(
                    ValueError, "contains too many possible GeometryCollections."
                ):
                    GEOSGeometry(payload, max_geom_collections=1)

    def test_wkb_impossible_child_count_is_rejected(self):
        data = b"\x01" + struct.pack("<II", 7, 0xFFFFFFFF)
        for payload, representation in self._wkb_representations(data):
            with (
                self.subTest(payload=representation),
                self.assertRaisesMessage(GEOSException, "Invalid WKB input."),
            ):
                GEOSGeometry(payload)

    def test_wkb_missing_child_header_is_rejected(self):
        collection = b"\x01" + struct.pack("<II", 7, 2)
        point = b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", 0.0, 0.0)
        data = collection + point
        for payload, representation in self._wkb_representations(data):
            with (
                self.subTest(payload=representation),
                self.assertRaisesMessage(GEOSException, "Invalid WKB input."),
            ):
                GEOSGeometry(payload)

    def test_wkt_geometry_collection_flat(self):
        def wkt_payload_no_nesting(num_points):
            # Many parentheses, but only one collection level.
            return (
                "GEOMETRYCOLLECTION("
                + ",".join("POINT(0 0)" for _ in range(num_points))
                + ")"
            )

        GEOSGeometry(wkt_payload_no_nesting(num_points=5), max_geom_collections=1)

    def test_wkt_geometry_collections_breadth(self):
        """A wide breadth of geometry collections is not counted as depth."""

        def wkt_payload_breadth(num_colls):
            return (
                "GEOMETRYCOLLECTION("
                + ",".join("GEOMETRYCOLLECTION(POINT(0 0))" for _ in range(num_colls))
                + ")"
            )

        GEOSGeometry(wkt_payload_breadth(num_colls=5), max_geom_collections=2)

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

    def test_malformed_multi_wkb_child_is_rejected(self):
        def make_invalid_geom(depth):
            point = b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", 0.0, 0.0)
            collection = b"\x01" + struct.pack("<I", 7) + struct.pack("<I", 1)
            multipolygon = b"\x01" + struct.pack("<I", 6) + struct.pack("<I", 1)
            return (multipolygon + collection * depth + point).hex().upper()

        # Reject the invalid child type before GEOS recursively parses it.
        with self.assertRaisesMessage(GEOSException, "Invalid WKB input."):
            GEOSGeometry(make_invalid_geom(6), max_geom_collections=5)

    def test_malformed_recursive_multi_wkb_is_rejected(self):
        point = b"\x01" + struct.pack("<I", 1) + struct.pack("<dd", 0.0, 0.0)
        multipoint = b"\x01" + struct.pack("<II", 4, 1)
        data = multipoint * 6 + point
        for payload, representation in self._wkb_representations(data):
            with (
                self.subTest(payload=representation),
                self.assertRaisesMessage(GEOSException, "Invalid WKB input."),
            ):
                GEOSGeometry(payload, max_geom_collections=5)
