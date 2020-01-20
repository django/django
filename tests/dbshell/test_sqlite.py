from pathlib import Path
from subprocess import CompletedProcess
from unittest import mock, skipUnless

from django.db import connection
from django.db.backends.sqlite3.client import DatabaseClient
from django.test import SimpleTestCase


@skipUnless(connection.vendor == 'sqlite', 'SQLite tests.')
class SqliteDbshellCommandTestCase(SimpleTestCase):
    def _run_dbshell(self):
        """Run runshell command and capture its arguments."""
        def _mock_subprocess_run(*args, **kwargs):
            self.subprocess_args = list(*args)
            return CompletedProcess(self.subprocess_args, 0)

        client = DatabaseClient(connection)
        with mock.patch('subprocess.run', new=_mock_subprocess_run):
            client.runshell()
        return self.subprocess_args

    def test_path_name(self):
        with mock.patch.dict(
            connection.settings_dict,
            {'NAME': Path('test.db.sqlite3')},
        ):
            self.assertEqual(
                self._run_dbshell(),
                ['sqlite3', 'test.db.sqlite3'],
            )
