import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from django.db import ConnectionHandler


SETTINGS = """
SECRET_KEY = 'django_auth_tests_secret_key'

INSTALLED_APPS = [
    'django.contrib.auth.apps.BaseAuthConfig',
    'django.contrib.contenttypes',
]

MIGRATION_MODULES = {'auth': None}

DATABASES = %(databases)r
"""


class AppConfigTests(unittest.TestCase):
    def test_no_migrations(self):
        project_path = tempfile.mkdtemp()
        try:
            databases = {
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': os.path.join(project_path, 'db.sqlite3'),
                }
            }

            with open(os.path.join(project_path, 'no_migrations.py'), 'w') as fp:
                fp.write(SETTINGS % {'databases': databases})

            with open(os.devnull, 'wb') as devnull:
                cmd = [
                    sys.executable,
                    '-m', 'django',
                    'migrate',
                    '--settings', 'no_migrations',
                    '--pythonpath', project_path,
                ]
                returncode = subprocess.call(cmd, stdout=devnull, stderr=devnull)

            # Migrate command ran without errors.
            self.assertEqual(returncode, 0)

            # Auth tables weren't created.
            conns = ConnectionHandler(databases)
            try:
                self.assertEqual(
                    set(conns['default'].introspection.table_names()),
                    {'django_content_type', 'django_migrations'},
                )
            finally:
                conns.close_all()
        finally:
            shutil.rmtree(project_path)
