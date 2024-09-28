import subprocess
from pathlib import Path
from unittest import mock, skipUnless

from django.core.management import CommandError, call_command
from django.db import connection
from django.db.backends.sqlite3.client import DatabaseClient
from django.test import SimpleTestCase


class SqliteDbshellCommandTestCase(SimpleTestCase):
    def settings_to_cmd_args_env(self, settings_dict, parameters=None):
        if parameters is None:
            parameters = []
        return DatabaseClient.settings_to_cmd_args_env(settings_dict, parameters)

    def test_path_name(self):
        self.assertEqual(
            self.settings_to_cmd_args_env({"NAME": Path("test.db.sqlite3")}),
            (["sqlite3", Path("test.db.sqlite3")], None),
        )

    def test_parameters(self):
        self.assertEqual(
            self.settings_to_cmd_args_env({"NAME": "test.db.sqlite3"}, ["-help"]),
            (["sqlite3", "test.db.sqlite3", "-help"], None),
        )

    @skipUnless(connection.vendor == "sqlite", "SQLite test")
    def test_non_zero_exit_status_when_path_to_db_is_path(self):
        sqlite_with_path = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path("test.db.sqlite3"),
        }
        cmd_args = self.settings_to_cmd_args_env(sqlite_with_path)[0]

        msg = '"sqlite3 test.db.sqlite3" returned non-zero exit status 1.'
        with (
            mock.patch(
                "django.db.backends.sqlite3.client.DatabaseClient.runshell",
                side_effect=subprocess.CalledProcessError(returncode=1, cmd=cmd_args),
            ),
            self.assertRaisesMessage(CommandError, msg),
        ):
            call_command("dbshell")
