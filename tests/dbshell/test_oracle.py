import os
import signal
from unittest import mock

from django.db.backends.oracle.client import DatabaseClient
from django.test import SimpleTestCase


class MockConnection(object):

    def __init__(self, connect_string):
        self.connect_string = connect_string

    def _connect_string(self):
        return self.connect_string



class OracleDbshellCommandTestCase(SimpleTestCase):

    def _run_it(self, connectstring, have_rlwrap=False):
        """
        That function invokes the runshell command, while mocking
        subprocess.call. It returns a 2-tuple with:
        - The command line list
        - The content of the file pointed by environment PGPASSFILE, or None.
        """
        connection = MockConnection(connectstring)
        client = DatabaseClient(connection)

        def _mock_subprocess_call(*args):
            self.subprocess_args = list(*args)
            return 0
        def _mock_shutil_which(*args):
            return '/usr/bin/rlwrap' if have_rlwrap else None

        self.subprocess_args = None
        with mock.patch('subprocess.call', new=_mock_subprocess_call):
            with mock.patch('shutil.which', new=_mock_shutil_which):
                client.runshell()
        return self.subprocess_args

    def test_basic(self):
        connectstring = 'USER/PASSWORD@TNSNAME'

        expected_args = ['sqlplus', '-L', connectstring]
        actual_args = self._run_it(connectstring, have_rlwrap=False)

        self.assertEqual(
            actual_args,
            expected_args
        )

    def test_with_rlwrap(self):
        connectstring = 'USER/PASSWORD@TNSNAME'

        expected_args = [
            '/usr/bin/rlwrap',
            '--history',
            '2000',
            'sqlplus',
            '-L',
            connectstring]

        actual_args = self._run_it(connectstring, have_rlwrap=True)

        self.assertEqual(
            actual_args,
            expected_args
        )
