import json
from collections import UserList, defaultdict
from datetime import datetime
from decimal import Decimal

from django.test import SimpleTestCase
from django.utils.json import normalize_json


class JSONNormalizeTestCase(SimpleTestCase):
    def test_converts_json_types(self):
        for test_case, expected in [
            (None, "null"),
            (True, "true"),
            (False, "false"),
            (2, "2"),
            (3.0, "3.0"),
            (1e23 + 1, "1e+23"),
            ("1", '"1"'),
            (b"hello", '"hello"'),
            ([], "[]"),
            (UserList([1, 2]), "[1, 2]"),
            ({}, "{}"),
            ({1: "a"}, '{"1": "a"}'),
            ({"foo": (1, 2, 3)}, '{"foo": [1, 2, 3]}'),
            (defaultdict(list), "{}"),
            (float("nan"), "NaN"),
            (float("inf"), "Infinity"),
            (float("-inf"), "-Infinity"),
        ]:
            with self.subTest(test_case):
                normalized = normalize_json(test_case)
                # Ensure that the normalized result is serializable.
                self.assertEqual(json.dumps(normalized), expected)

    def test_bytes_decode_error(self):
        with self.assertRaisesMessage(ValueError, "Unsupported value"):
            normalize_json(b"\xff")

    def test_encode_error(self):
        for test_case in [self, any, object(), datetime.now(), set(), Decimal("3.42")]:
            with (
                self.subTest(test_case),
                self.assertRaisesMessage(TypeError, "Unsupported type"),
            ):
                normalize_json(test_case)
