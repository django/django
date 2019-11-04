from unittest import mock, skipUnless

from django.db import connection
from django.db.backends.oracle.client import DatabaseClient
from django.test import SimpleTestCase


@skipUnless(connection.vendor == 'oracle', 'Oracle tests')
class OracleDbshellTests(SimpleTestCase):
    def _run_dbshell(self, rlwrap=False):
        """Run runshell command and capture its arguments."""
        def _mock_subprocess_call(*args):
            self.subprocess_args = tuple(*args)
            return 0

        client = DatabaseClient(connection)
        self.subprocess_args = None
        with mock.patch('subprocess.call', new=_mock_subprocess_call):
            with mock.patch('shutil.which', return_value='/usr/bin/rlwrap' if rlwrap else None):
                client.runshell()
        return self.subprocess_args

    def test_without_rlwrap(self):
        self.assertEqual(
            self._run_dbshell(rlwrap=False),
            ('sqlplus', '-L', connection._connect_string()),
        )

    def test_with_rlwrap(self):
        self.assertEqual(
            self._run_dbshell(rlwrap=True),
            ('/usr/bin/rlwrap', 'sqlplus', '-L', connection._connect_string()),
        )
