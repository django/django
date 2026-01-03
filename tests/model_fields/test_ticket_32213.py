from django.test import TestCase

from .models import NullableJSONModel


class Ticket32213Tests(TestCase):
    def test_json_key_transform_type_preservation_sqlite(self):
        """
        Regression test for Ticket #32213.
        Verify that SQLite KeyTransform preserves distinct types for:
        - Strings vs Numbers ("123" vs 123)
        - Strings vs Booleans ("true" vs True)
        - Strings vs Nulls ("null" vs None)
        """
        objects = [
            NullableJSONModel(value={"key": "123"}),
            NullableJSONModel(value={"key": 123}),
            NullableJSONModel(value={"key": "true"}),
            NullableJSONModel(value={"key": True}),
            NullableJSONModel(value={"key": "null"}),
            NullableJSONModel(value={"key": None}),
        ]
        NullableJSONModel.objects.bulk_create(objects)
        values = NullableJSONModel.objects.values_list("value__key", flat=True)
        results = list(values)

        self.assertIn("123", results)
        self.assertIn(123, results)
        self.assertIn("true", results)
        self.assertIn(True, results)
        self.assertIn("null", results)
        self.assertIn(None, results)

        self.assertEqual(results.count("123"), 1)
        self.assertEqual(results.count(123), 1)
        self.assertEqual(results.count("true"), 1)
        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count("null"), 1)
        self.assertEqual(results.count(None), 1)
