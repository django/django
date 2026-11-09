import subprocess
import traceback
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

    def test_runshell_error_password_does_not_leak(self):
        settings_dict = {**connection.settings_dict, "PASSWORD": "somepassword"}
        client = DatabaseClient(mock.Mock(settings_dict=settings_dict))

        def fail(args, **kwargs):
            self.assertIn(client.connect_string(settings_dict), args)
            raise subprocess.CalledProcessError(7, args)

        for wrapper in (None, "/usr/bin/rlwrap"):
            with self.subTest(wrapper=wrapper):
                with (
                    mock.patch("shutil.which", return_value=wrapper),
                    mock.patch("subprocess.run", side_effect=fail),
                    self.assertRaises(subprocess.CalledProcessError) as ctx,
                ):
                    try:
                        client.runshell([])
                    except subprocess.CalledProcessError as exc:
                        formatted_traceback = "".join(traceback.format_exception(exc))
                        raise
                self.assertEqual(ctx.exception.returncode, 7)
                for surface, output in (
                    ("cmd", str(ctx.exception.cmd)),
                    ("message", str(ctx.exception)),
                    ("traceback", formatted_traceback),
                ):
                    with self.subTest(surface=surface):
                        self.assertNotIn("somepassword", output)

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
