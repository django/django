from unittest import mock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase


class DbshellCommandTestCase(SimpleTestCase):
    def test_command_missing(self):
        msg = (
            "You appear not to have the %r program installed or on your path."
            % connection.client.executable_name
        )
        with self.assertRaisesMessage(CommandError, msg):
            with mock.patch("subprocess.run", side_effect=FileNotFoundError):
                call_command("dbshell")

    @mock.patch("django.db.backends.base.client.subprocess.run")
    def test_sigint_ignored_during_runshell(self, mock_run):
        import signal

        from django.db.backends.base.client import BaseDatabaseClient

        original_handler = signal.getsignal(signal.SIGINT)

        def mock_run_side_effect(*args, **kwargs):
            self.assertEqual(signal.getsignal(signal.SIGINT), signal.SIG_IGN)

        mock_run.side_effect = mock_run_side_effect

        client = BaseDatabaseClient(connection)
        # Mock settings_to_cmd_args_env to return dummy args
        with mock.patch.object(
            client, "settings_to_cmd_args_env", return_value=(["mock_db_client"], None)
        ):
            client.runshell([])

        self.assertEqual(signal.getsignal(signal.SIGINT), original_handler)
