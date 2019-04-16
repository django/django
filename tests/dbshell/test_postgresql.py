import os
import signal
import subprocess
from unittest import mock

from django.db.backends.postgresql.client import DatabaseClient
from django.test import SimpleTestCase


class PostgreSqlDbshellCommandTestCase(SimpleTestCase):

    def _run_it(self, dbinfo):
        """
        That function invokes the runshell command, while mocking
        subprocess.run(). It returns a 2-tuple with:
        - The command line list
        - The the value of the PGPASSWORD environment variable, or None.
        """
        def _mock_subprocess_run(*args, env=os.environ, **kwargs):
            self.subprocess_args = list(*args)
            self.environment = {
                key: env.get(key)
                for key in ('PGPASSWORD', 'PGSSLROOTCERT', 'PGSSLCERT', 'PGSSLKEY')
                if env.get(key)
            }
            self.pgpassword = env.get('PGPASSWORD')
            return subprocess.CompletedProcess(self.subprocess_args, 0)
        with mock.patch('subprocess.run', new=_mock_subprocess_run):
            DatabaseClient.runshell_db(dbinfo)
        return self.subprocess_args, self.environment

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
                {'PGPASSWORD': 'somepassword'},
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
                {},
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
                {'PGPASSWORD': 'some:password'},
            )
        )

    def test_accent(self):
        username = 'rôle'
        password = 'sésame'
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': username,
                'password': password,
                'host': 'somehost',
                'port': '444',
            }), (
                ['psql', '-U', username, '-h', 'somehost', '-p', '444', 'dbname'],
                {'PGPASSWORD': password},
            )
        )

    def test_ssl_connection(self):
        username = 'rôle'
        password = 'sésame'
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': username,
                'password': password,
                'host': 'somehost',
                'port': '444',
                'sslrootcert': '/path/to/rootcert',
                'sslcert': '/path/to/cert',
                'sslkey': '/path/to/key',
            }), (
                ['psql', '-U', username, '-h', 'somehost', '-p', '444', 'dbname'],
                {
                    'PGPASSWORD': password,
                    'PGSSLROOTCERT': '/path/to/rootcert',
                    'PGSSLCERT': '/path/to/cert',
                    'PGSSLKEY': '/path/to/key',
                }
            )
        )

    def test_sigint_handler(self):
        """SIGINT is ignored in Python and passed to psql to abort quries."""
        def _mock_subprocess_run(*args, **kwargs):
            handler = signal.getsignal(signal.SIGINT)
            self.assertEqual(handler, signal.SIG_IGN)

        sigint_handler = signal.getsignal(signal.SIGINT)
        # The default handler isn't SIG_IGN.
        self.assertNotEqual(sigint_handler, signal.SIG_IGN)
        with mock.patch('subprocess.run', new=_mock_subprocess_run):
            DatabaseClient.runshell_db({})
        # dbshell restores the original handler.
        self.assertEqual(sigint_handler, signal.getsignal(signal.SIGINT))
