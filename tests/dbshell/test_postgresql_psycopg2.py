# -*- coding: utf8 -*-
from __future__ import unicode_literals

import locale
import os

from django.db.backends.postgresql.client import DatabaseClient
from django.test import SimpleTestCase, mock
from django.utils import six
from django.utils.encoding import force_bytes, force_str


class PostgreSqlDbshellCommandTestCase(SimpleTestCase):

    def _run_it(self, dbinfo):
        """
        That function invokes the runshell command, while mocking
        subprocess.call. It returns a 2-tuple with:
        - The command line list
        - The binary content of file pointed by environment PGPASSFILE, or
          None.
        """
        def _mock_subprocess_call(*args):
            self.subprocess_args = list(*args)
            if 'PGPASSFILE' in os.environ:
                with open(os.environ['PGPASSFILE'], 'rb') as f:
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
                b'somehost:444:dbname:someuser:somepassword',
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
                b'\\:\\:1:444:dbname:some\\:user:some\\:password',
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
                b'somehost:444:dbname:some\\\\user:some\\\\password',
            )
        )

    def test_accent(self):
        # The pgpass temporary file needs to be encoded using the system locale.
        encoding = locale.getpreferredencoding()
        username = 'rôle'
        password = 'sésame'
        try:
            username_str = force_str(username, encoding)
            password_str = force_str(password, encoding)
            pgpass_bytes = force_bytes(
                'somehost:444:dbname:%s:%s' % (username, password),
                encoding=encoding,
            )
        except UnicodeEncodeError:
            if six.PY2:
                self.skipTest("Your locale can't run this test.")
        self.assertEqual(
            self._run_it({
                'database': 'dbname',
                'user': username_str,
                'password': password_str,
                'host': 'somehost',
                'port': '444',
            }), (
                ['psql', '-U', username_str, '-h', 'somehost', '-p', '444', 'dbname'],
                pgpass_bytes,
            )
        )
