# -*- coding: utf8 -*-
import locale
import os

from django.db.backends.postgresql_psycopg2.client import DatabaseClient
from django.test import SimpleTestCase, mock
from django.utils.encoding import force_bytes, force_str


class PostgreSqlDbshellCommandTestCase(SimpleTestCase):

    def _run_it(self, dbinfo):
        '''
        That function invokes the runshell command, while mocking
        subprocess.call. It returns a 2-tuple with:
        - The command line list
        - The binary content of file pointed by environment PGPASSFILE, or
          None.
        '''
        def _mock_subprocess_call(*args):
            self.subprocess_args = list(*args)
            if 'PGPASSFILE' in os.environ:
                self.pgpass = open(os.environ['PGPASSFILE'], 'rb').read()
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
                'NAME': 'somedbname',
                'USER': 'someuser',
                'PASSWORD': 'somepassword',
                'HOST': 'somehost',
                'PORT': 444,
            }), (
                ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444',
                 'somedbname'],
                b'somehost:444:somedbname:someuser:somepassword\n'))

    def test_nopass(self):
        self.assertEqual(
            self._run_it({
                'NAME': 'somedbname',
                'USER': 'someuser',
                'HOST': 'somehost',
                'PORT': 444,
            }), (
                ['psql', '-U', 'someuser', '-h', 'somehost', '-p', '444',
                 'somedbname'],
                None))

    def test_column(self):
        self.assertEqual(
            self._run_it({
                'NAME': 'somedbname',
                'USER': 'some:user',
                'PASSWORD': 'some:password',
                'HOST': '::1',
                'PORT': 444,
            }), (
                ['psql', '-U', 'some:user', '-h', '::1', '-p', '444',
                 'somedbname'],
                b'\\:\\:1:444:somedbname:some\\:user:some\\:password\n'))

    def test_escape(self):
        self.assertEqual(
            self._run_it({
                'NAME': 'somedbname',
                'USER': 'some\\user',
                'PASSWORD': 'some\\password',
                'HOST': 'somehost',
                'PORT': 444,
            }), (
                ['psql', '-U', 'some\\user', '-h', 'somehost', '-p', '444',
                 'somedbname'],
                b'somehost:444:somedbname:some\\\\user:some\\\\password\n'))

    def test_accent(self):
        encoding = locale.getpreferredencoding()
        username = u'rôle'
        password = u'sésame'
        try:
            username_str = force_str(username, encoding)
            password_str = force_str(password, encoding)
            pgpass_bytes = force_bytes(
                u'somehost:444:somedbname:%s:%s\n' % (username, password),
                encoding=encoding)
        except UnicodeEncodeError:
            self.skipTest("Your locale can't run this test with python2.")
        self.assertEqual(
            self._run_it({
                'NAME': 'somedbname',
                'USER': username_str,
                'PASSWORD': password_str,
                'HOST': 'somehost',
                'PORT': 444,
            }), (
                ['psql', '-U', username_str, '-h', 'somehost', '-p', '444',
                 'somedbname'],
                pgpass_bytes))
