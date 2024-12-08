from unittest import mock, skipUnless

from django.db import connection
from django.db.backends.oracle.client import DatabaseClient
from django.test import SimpleTestCase


@skipUnless(connection.vendor == "oracle", "Requires oracledb to be installed")
class OracleDbshellTests(SimpleTestCase):
    def settings_to_cmd_args_env(self, settings_dict, parameters=None, rlwrap=False):
        if parameters is None:
            parameters = []
        with mock.patch(
            "shutil.which", return_value="/usr/bin/rlwrap" if rlwrap else None
        ):
            return DatabaseClient.settings_to_cmd_args_env(settings_dict, parameters)

    def test_without_rlwrap(self):
        expected_args = [
            "sqlplus",
            "-L",
            connection.client.connect_string(connection.settings_dict),
        ]
        self.assertEqual(
            self.settings_to_cmd_args_env(connection.settings_dict, rlwrap=False),
            (expected_args, None),
        )

    def test_with_rlwrap(self):
        expected_args = [
            "/usr/bin/rlwrap",
            "sqlplus",
            "-L",
            connection.client.connect_string(connection.settings_dict),
        ]
        self.assertEqual(
            self.settings_to_cmd_args_env(connection.settings_dict, rlwrap=True),
            (expected_args, None),
        )

    def test_parameters(self):
        expected_args = [
            "sqlplus",
            "-L",
            connection.client.connect_string(connection.settings_dict),
            "-HELP",
        ]
        self.assertEqual(
            self.settings_to_cmd_args_env(
                connection.settings_dict,
                parameters=["-HELP"],
            ),
            (expected_args, None),
        )
