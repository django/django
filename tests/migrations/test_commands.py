# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import shutil

from django.core.management import call_command
from django.db.models.loading import cache
from django.test.utils import override_settings
from django.utils import six
from django.utils._os import upath
from django.utils.encoding import force_text

from .models import UnicodeModel
from .test_base import MigrationTestBase


class MigrateTests(MigrationTestBase):
    """
    Tests running the migrate command.
    """

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_migrate(self):
        """
        Tests basic usage of the migrate command.
        """
        # Make sure no tables are created
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")
        # Run the migrations to 0001 only
        call_command("migrate", "migrations", "0001", verbosity=0)
        # Make sure the right tables exist
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")
        # Run migrations all the way
        call_command("migrate", verbosity=0)
        # Make sure the right tables exist
        self.assertTableExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableExists("migrations_book")
        # Unmigrate everything
        call_command("migrate", "migrations", "zero", verbosity=0)
        # Make sure it's all gone
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_sqlmigrate(self):
        """
        Makes sure that sqlmigrate does something.
        """
        # Test forwards. All the databases agree on CREATE TABLE, at least.
        stdout = six.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=stdout)
        self.assertIn("create table", stdout.getvalue().lower())
        # And backwards is a DROP TABLE
        stdout = six.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=stdout, backwards=True)
        self.assertIn("drop table", stdout.getvalue().lower())


class MakeMigrationsTests(MigrationTestBase):
    """
    Tests running the makemigrations command.
    """

    def setUp(self):
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(upath(__file__)))
        self.migration_dir = os.path.join(self.test_dir, 'migrations')

    def tearDown(self):
        os.chdir(self.test_dir)
        try:
            self._rmrf(self.migration_dir)
        except OSError:
            pass
        os.chdir(self._cwd)

    def _rmrf(self, dname):
        if os.path.commonprefix([self.test_dir, os.path.abspath(dname)]) != self.test_dir:
            return
        shutil.rmtree(dname)

    def test_files_content(self):
        self.assertTableNotExists("migrations_unicodemodel")
        cache.register_models('migrations', UnicodeModel)
        call_command("makemigrations", "migrations", verbosity=0)

        init_file = os.path.join(self.migration_dir, "__init__.py")

        # Check for existing __init__.py file in migrations folder
        self.assertTrue(os.path.exists(init_file))

        with open(init_file, 'r') as fp:
            content = force_text(fp.read())
            self.assertEqual(content, '')

        initial_file = os.path.join(self.migration_dir, "0001_initial.py")

        # Check for existing 0001_initial.py file in migration folder
        self.assertTrue(os.path.exists(initial_file))

        with open(initial_file, 'r') as fp:
            content = force_text(fp.read())
            self.assertTrue('# encoding: utf8' in content)
            self.assertTrue('migrations.CreateModel' in content)

            if six.PY3:
                self.assertTrue('úñí©óðé µóðéø' in content)  # Meta.verbose_name
                self.assertTrue('úñí©óðé µóðéøß' in content)  # Meta.verbose_name_plural
                self.assertTrue('ÚÑÍ¢ÓÐÉ' in content)  # title.verbose_name
                self.assertTrue('“Ðjáñgó”' in content)  # title.default
            else:
                self.assertTrue('\\xfa\\xf1\\xed\\xa9\\xf3\\xf0\\xe9 \\xb5\\xf3\\xf0\\xe9\\xf8' in content)  # Meta.verbose_name
                self.assertTrue('\\xfa\\xf1\\xed\\xa9\\xf3\\xf0\\xe9 \\xb5\\xf3\\xf0\\xe9\\xf8\\xdf' in content)  # Meta.verbose_name_plural
                self.assertTrue('\\xda\\xd1\\xcd\\xa2\\xd3\\xd0\\xc9' in content)  # title.verbose_name
                self.assertTrue('\\u201c\\xd0j\\xe1\\xf1g\\xf3\\u201d' in content)  # title.default
