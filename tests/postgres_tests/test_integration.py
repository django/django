import os
import subprocess
import sys
import unittest

from django.test import SimpleTestCase

try:
    import psycopg2
except ImportError:
    psycopg2 = None


@unittest.skipIf(psycopg2 is None, 'psycopg2 is required')
class PostgresIntegrationTest(SimpleTestCase):
    def test_management_command(self):
        manage_py = os.path.join(os.path.dirname(__file__), 'integration', 'manage.py')
        result = subprocess.run(
            [sys.executable, manage_py, 'check'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.assertEqual(result.returncode, 0)
