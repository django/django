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
        subprocess.run(). It returns a tuple with:
        - The command line list
        - The value of the PGPASSWORD environment variable, or None.
        - A dict of SSL-related environment variables.
        """
        def _mock_subprocess_run(*args, env=os.environ, **kwargs):
            self.subprocess_args = list(*args)
            self.pgpassword = env.get('PGPASSWORD')
            self.ssl_env = {
                'PGSSLMODE': env.get('PGSSLMODE'),
                'PGSSLROOTCERT': env.get('PGSSLROOTCERT'),
                'PGSSLCERT': env.get('PGSSLCERT'),
                'PGSSLKEY': env.get('PGSSLKEY'),
            }
            return subprocess.CompletedProcess(self.subprocess_args, 0)
        with mock.patch('subprocess.run', new=_mock_subprocess_run):
            DatabaseClient.runshell_db(dbinfo)
        return self.subprocess_args, self.pgpassword, self.ssl_env

    def test_basic(self):
        args, password, ssl_env = self._run_it({
            'database': 'dbname',
            'user': 'someuser',
            'password': 'somepassword',
            'host': 'somehost',
            'port': '444',
        })
        self.assertEqual(
            args,
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname']
        )
        self.assertEqual(password, 'somepassword')
        self.assertEqual(ssl_env, {
            'PGSSLMODE': None,
            'PGSSLROOTCERT': None,
            'PGSSLCERT': None,
            'PGSSLKEY': None,
        })

    def test_nopass(self):
        args, password, ssl_env = self._run_it({
            'database': 'dbname',
            'user': 'someuser',
            'host': 'somehost',
            'port': '444',
        })
        self.assertEqual(
            args,
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname']
        )
        self.assertEqual(password, None)
        self.assertEqual(ssl_env, {
            'PGSSLMODE': None,
            'PGSSLROOTCERT': None,
            'PGSSLCERT': None,
            'PGSSLKEY': None,
        })

    def test_column(self):
        args, password, ssl_env = self._run_it({
            'database': 'dbname',
            'user': 'some:user',
            'password': 'some:password',
            'host': '::1',
            'port': '444',
        })
        self.assertEqual(
            args,
            ['psql', '-U', 'some:user', '-h', '::1', '-p', '444', 'dbname']
        )
        self.assertEqual(password, 'some:password')
        self.assertEqual(ssl_env, {
            'PGSSLMODE': None,
            'PGSSLROOTCERT': None,
            'PGSSLCERT': None,
            'PGSSLKEY': None,
        })

    def test_accent(self):
        username = 'rôle'
        password = 'sésame'
        args, passwd, ssl_env = self._run_it({
            'database': 'dbname',
            'user': username,
            'password': password,
            'host': 'somehost',
            'port': '444',
        })
        self.assertEqual(
            args,
            ['psql', '-U', username, '-h', 'somehost', '-p', '444', 'dbname']
        )
        self.assertEqual(passwd, password)
        self.assertEqual(ssl_env, {
            'PGSSLMODE': None,
            'PGSSLROOTCERT': None,
            'PGSSLCERT': None,
            'PGSSLKEY': None,
        })

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

    def test_ssl_certificate(self):
        """SSL certificates are passed via environment variables."""
        args, password, ssl_env = self._run_it({
            'database': 'dbname',
            'user': 'someuser',
            'password': 'somepassword',
            'host': 'somehost',
            'port': '444',
            'sslmode': 'verify-ca',
            'sslrootcert': '/path/to/ca.crt',
            'sslcert': '/path/to/client.crt',
            'sslkey': '/path/to/client.key',
        })
        self.assertEqual(
            args,
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname']
        )
        self.assertEqual(password, 'somepassword')
        self.assertEqual(ssl_env, {
            'PGSSLMODE': 'verify-ca',
            'PGSSLROOTCERT': '/path/to/ca.crt',
            'PGSSLCERT': '/path/to/client.crt',
            'PGSSLKEY': '/path/to/client.key',
        })

    def test_ssl_mode_only(self):
        """Only sslmode can be specified without other SSL options."""
        args, password, ssl_env = self._run_it({
            'database': 'dbname',
            'user': 'someuser',
            'host': 'somehost',
            'port': '444',
            'sslmode': 'require',
        })
        self.assertEqual(
            args,
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname']
        )
        self.assertEqual(password, None)
        self.assertEqual(ssl_env, {
            'PGSSLMODE': 'require',
            'PGSSLROOTCERT': None,
            'PGSSLCERT': None,
            'PGSSLKEY': None,
        })

    def test_ssl_partial_options(self):
        """Partial SSL options can be specified."""
        args, password, ssl_env = self._run_it({
            'database': 'dbname',
            'user': 'someuser',
            'host': 'somehost',
            'port': '444',
            'sslrootcert': '/path/to/ca.crt',
            'sslcert': '/path/to/client.crt',
        })
        self.assertEqual(
            args,
            ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444', 'dbname']
        )
        self.assertEqual(password, None)
        self.assertEqual(ssl_env, {
            'PGSSLMODE': None,
            'PGSSLROOTCERT': '/path/to/ca.crt',
            'PGSSLCERT': '/path/to/client.crt',
            'PGSSLKEY': None,
        })
