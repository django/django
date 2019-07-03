import os
import subprocess
import sys

from . import PostgreSQLSimpleTestCase


class PostgresIntegrationTests(PostgreSQLSimpleTestCase):
    def test_check(self):
        test_environ = os.environ.copy()
        if 'DJANGO_SETTINGS_MODULE' in test_environ:
            del test_environ['DJANGO_SETTINGS_MODULE']
        test_environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '../../')
        result = subprocess.run(
            [sys.executable, '-m', 'django', 'check', '--settings', 'integration_settings'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(__file__),
            env=test_environ
        )
        stderr = '\n'.join([e.decode() for e in result.stderr.splitlines()])
        self.assertEqual(result.returncode, 0, msg=stderr)
