import os
import subprocess
import sys

from . import PostgreSQLSimpleTestCase


class PostgresIntegrationTests(PostgreSQLSimpleTestCase):
    def test_check(self):
        result = subprocess.run(
            [sys.executable, '-m', 'django', 'check', '--settings', 'integration_settings'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(__file__),
        )
        stderr = '\n'.join([e.decode() for e in result.stderr.splitlines()])
        self.assertEqual(result.returncode, 0, msg=stderr)
