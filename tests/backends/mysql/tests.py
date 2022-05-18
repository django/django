import unittest
from contextlib import contextmanager
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.db import NotSupportedError, connection
from django.test import TestCase, override_settings


@contextmanager
def get_connection():
    new_connection = connection.copy()
    yield new_connection
    new_connection.close()


@override_settings(DEBUG=True)
@unittest.skipUnless(connection.vendor == "mysql", "MySQL tests")
class IsolationLevelTests(TestCase):

    read_committed = "read committed"
    repeatable_read = "repeatable read"
    isolation_values = {
        level: level.upper() for level in (read_committed, repeatable_read)
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        configured_isolation_level = (
            connection.isolation_level or cls.isolation_values[cls.repeatable_read]
        )
        cls.configured_isolation_level = configured_isolation_level.upper()
        cls.other_isolation_level = (
            cls.read_committed
            if configured_isolation_level != cls.isolation_values[cls.read_committed]
            else cls.repeatable_read
        )

    @staticmethod
    def get_isolation_level(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SHOW VARIABLES "
                "WHERE variable_name IN ('transaction_isolation', 'tx_isolation')"
            )
            return cursor.fetchone()[1].replace("-", " ")

    def test_auto_is_null_auto_config(self):
        query = "set sql_auto_is_null = 0"
        connection.init_connection_state()
        last_query = connection.queries[-1]["sql"].lower()
        if connection.features.is_sql_auto_is_null_enabled:
            self.assertIn(query, last_query)
        else:
            self.assertNotIn(query, last_query)

    def test_connect_isolation_level(self):
        self.assertEqual(
            self.get_isolation_level(connection), self.configured_isolation_level
        )

    def test_setting_isolation_level(self):
        with get_connection() as new_connection:
            new_connection.settings_dict["OPTIONS"][
                "isolation_level"
            ] = self.other_isolation_level
            self.assertEqual(
                self.get_isolation_level(new_connection),
                self.isolation_values[self.other_isolation_level],
            )

    def test_uppercase_isolation_level(self):
        # Upper case values are also accepted in 'isolation_level'.
        with get_connection() as new_connection:
            new_connection.settings_dict["OPTIONS"][
                "isolation_level"
            ] = self.other_isolation_level.upper()
            self.assertEqual(
                self.get_isolation_level(new_connection),
                self.isolation_values[self.other_isolation_level],
            )

    def test_default_isolation_level(self):
        # If not specified in settings, the default is read committed.
        with get_connection() as new_connection:
            new_connection.settings_dict["OPTIONS"].pop("isolation_level", None)
            self.assertEqual(
                self.get_isolation_level(new_connection),
                self.isolation_values[self.read_committed],
            )

    def test_isolation_level_validation(self):
        new_connection = connection.copy()
        new_connection.settings_dict["OPTIONS"]["isolation_level"] = "xxx"
        msg = (
            "Invalid transaction isolation level 'xxx' specified.\n"
            "Use one of 'read committed', 'read uncommitted', "
            "'repeatable read', 'serializable', or None."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            new_connection.cursor()


@unittest.skipUnless(connection.vendor == "mysql", "MySQL tests")
class Tests(TestCase):
    @mock.patch.object(connection, "get_database_version")
    def test_check_database_version_supported(self, mocked_get_database_version):
        if connection.mysql_is_mariadb:
            mocked_get_database_version.return_value = (10, 3)
            msg = "MariaDB 10.4 or later is required (found 10.3)."
        else:
            mocked_get_database_version.return_value = (5, 6)
            msg = "MySQL 5.7 or later is required (found 5.6)."

        with self.assertRaisesMessage(NotSupportedError, msg):
            connection.check_database_version_supported()
        self.assertTrue(mocked_get_database_version.called)
