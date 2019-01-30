import os
import subprocess
import sys

from . import PostgreSQLSimpleTestCase


class PostgresIntegrationTests(PostgreSQLSimpleTestCase):
    def test_check(self):
        old_cwd = os.getcwd()
        self.addCleanup(lambda: os.chdir(old_cwd))
        os.chdir(os.path.dirname(__file__))
        result = subprocess.run(
            [sys.executable, '-m', 'django', 'check', '--settings', 'integration_settings'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        stderr = '\n'.join([e.decode() for e in result.stderr.splitlines()])
        self.assertEqual(result.returncode, 0, msg=stderr)
