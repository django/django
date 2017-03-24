import os
import signal
from unittest import mock

from django.db.backends.postgresql.client import DatabaseClient
from django.test import SimpleTestCase


class PostgreSqlDbshellCommandTestCase(SimpleTestCase):

    def _run_it(self, dbinfo):
        """
        That function invokes the runshell command, while mocking
        subprocess.call. It returns a 2-tuple with:
        - The command line list
        - The content of the file pointed by environment PGPASSFILE, or None.
        """
        def _mock_subprocess_call(*args):
            self.subprocess_args = list(*args)
            if 'PGPASSFILE' in os.environ:
                with open(os.environ['PGPASSFILE'], 'r') as f:
                    self.pgpass = f.read().strip()  # ignore line endings
            else:
                self.pgpass = None
            return 0
        self.subprocess_args = None
        self.pgpass = None
        with mock.patch('subprocess.call', new=_mock_subprocess_call):
            DatabaseClient.runshell_db(dbinfo)
        return self.subprocess_args, self.pgpass

    def test_basic(self):
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': 'someuser',
                'password': 'somepassword',
                'host': 'somehost',
                'port': '444',
            }), (
                ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname'],
                'somehost:444:dbname:someuser:somepassword',
            )
        )

    def test_nopass(self):
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': 'someuser',
                'host': 'somehost',
                'port': '444',
            }), (
                ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname'],
                None,
            )
        )

    def test_column(self):
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': 'some:user',
                'password': 'some:password',
                'host': '::1',
                'port': '444',
            }), (
                ['psql', '-U', 'some:user', '-h', '::1', '-p', '444', 'dbname'],
                '\\:\\:1:444:dbname:some\\:user:some\\:password',
            )
        )

    def test_escape_characters(self):
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': 'some\\user',
                'password': 'some\\password',
                'host': 'somehost',
                'port': '444',
            }), (
                ['psql', '-U', 'some\\user', '-h', 'somehost', '-p', '444', 'dbname'],
                'somehost:444:dbname:some\\\\user:some\\\\password',
            )
        )

    def test_accent(self):
        username = 'rôle'
        password = 'sésame'
        pgpass_string = 'somehost:444:dbname:%s:%s' % (username, password)
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': username,
                'password': password,
                'host': 'somehost',
                'port': '444',
            }), (
                ['psql', '-U', username, '-h', 'somehost', '-p', '444', 'dbname'],
                pgpass_string,
            )
        )

    def test_sigint_handler(self):
        """SIGINT is ignored in Python and passed to psql to abort quries."""
        def _mock_subprocess_call(*args):
            handler = signal.getsignal(signal.SIGINT)
            self.assertEqual(handler, signal.SIG_IGN)

        sigint_handler = signal.getsignal(signal.SIGINT)
        # The default handler isn't SIG_IGN.
        self.assertNotEqual(sigint_handler, signal.SIG_IGN)
        with mock.patch('subprocess.check_call', new=_mock_subprocess_call):
            DatabaseClient.runshell_db({})
        # dbshell restores the orignal handler.
        self.assertEqual(sigint_handler, signal.getsignal(signal.SIGINT))
