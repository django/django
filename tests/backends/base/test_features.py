from django.db import connection
from django.test import SimpleTestCase


class TestDatabaseFeatures(SimpleTestCase):
    databases = {"default"}

    def test_nonexistent_feature(self):
        self.assertFalse(hasattr(connection.features, "nonexistent"))

    def test_supports_transactions(self):
        self.assertIsInstance(connection.features.supports_transactions, bool)

    def test_supports_json_field(self):
        self.assertIsInstance(connection.features.supports_json_field, bool)

    def test_supports_foreign_keys(self):
        self.assertIsInstance(connection.features.supports_foreign_keys, bool)

    def test_can_return_columns_from_insert(self):
        self.assertIsInstance(connection.features.can_return_columns_from_insert, bool)

    def test_has_bulk_insert(self):
        self.assertIsInstance(connection.features.has_bulk_insert, bool)
