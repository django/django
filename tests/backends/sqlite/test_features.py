import sqlite3
from unittest import mock, skipUnless

from django.db import OperationalError, connection
from django.test import TestCase


@skipUnless(connection.vendor == "sqlite", "SQLite tests.")
class FeaturesTests(TestCase):
    def test_supports_json_field_operational_error(self):
        if hasattr(connection.features, "supports_json_field"):
            del connection.features.supports_json_field
        msg = "unable to open database file"
        with mock.patch.object(
            connection,
            "cursor",
            side_effect=OperationalError(msg),
        ):
            with self.assertRaisesMessage(OperationalError, msg):
                connection.features.supports_json_field

    def test_max_query_params_respects_variable_limit(self):
        limit_name = sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER
        current_limit = connection.features.max_query_params
        new_limit = min(42, current_limit)
        try:
            connection.connection.setlimit(limit_name, new_limit)
            self.assertEqual(connection.features.max_query_params, new_limit)
        finally:
            connection.connection.setlimit(limit_name, current_limit)
        self.assertEqual(connection.features.max_query_params, current_limit)
