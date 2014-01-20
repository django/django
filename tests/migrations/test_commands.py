# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import shutil

from django.apps import apps
from django.core.management import call_command, CommandError
from django.test import override_settings, override_system_checks
from django.utils import six
from django.utils._os import upath
from django.utils.encoding import force_text

from .models import UnicodeModel, UnserializableModel
from .test_base import MigrationTestBase


class MigrateTests(MigrationTestBase):
    """
    Tests running the migrate command.
    """

    # `auth` app is imported, but not installed in these tests (thanks to
    # MigrationTestBase), so we need to exclude checks registered by this app.

    @override_system_checks([])
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

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_migrate_list(self):
        """
        Tests --list output of migrate command
        """
        stdout = six.StringIO()
        call_command("migrate", list=True, stdout=stdout, verbosity=0)
        self.assertIn("migrations", stdout.getvalue().lower())
        self.assertIn("[ ] 0001_initial", stdout.getvalue().lower())
        self.assertIn("[ ] 0002_second", stdout.getvalue().lower())

        call_command("migrate", "migrations", "0001", verbosity=0)

        stdout = six.StringIO()
        # Giving the explicit app_label tests for selective `show_migration_list` in the command
        call_command("migrate", "migrations", list=True, stdout=stdout, verbosity=0)
        self.assertIn("migrations", stdout.getvalue().lower())
        self.assertIn("[x] 0001_initial", stdout.getvalue().lower())
        self.assertIn("[ ] 0002_second", stdout.getvalue().lower())
        # Cleanup by unmigrating everything
        call_command("migrate", "migrations", "zero", verbosity=0)

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_migrate_conflict_exit(self):
        """
        Makes sure that migrate exits if it detects a conflict.
        """
        with self.assertRaises(CommandError):
            call_command("migrate", "migrations")

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_conflict_exit(self):
        """
        Makes sure that makemigrations exits if it detects a conflict.
        """
        with self.assertRaises(CommandError):
            call_command("makemigrations")

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_merge_basic(self):
        """
        Makes sure that makemigrations doesn't error if you ask for
        merge mode with a conflict present. Doesn't test writing of the merge
        file, as that requires temp directories.
        """
        try:
            call_command("makemigrations", merge=True, verbosity=0)
        except CommandError:
            self.fail("Makemigrations errored in merge mode with conflicts")

    @override_system_checks([])
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

    # Because the `import_module` performed in `MigrationLoader` will cache
    # the migrations package, we can't reuse the same migration package
    # between tests. This is only a problem for testing, since `makemigrations`
    # is normally called in its own process.
    creation_counter = 0

    def setUp(self):
        MakeMigrationsTests.creation_counter += 1
        self._cwd = os.getcwd()
        self.test_dir = os.path.abspath(os.path.dirname(upath(__file__)))
        self.migration_dir = os.path.join(self.test_dir, 'migrations_%d' % self.creation_counter)
        self.migration_pkg = "migrations.migrations_%d" % self.creation_counter
        self._old_models = apps.app_configs['migrations'].models.copy()

    def tearDown(self):
        apps.app_configs['migrations'].models = self._old_models
        apps.all_models['migrations'] = self._old_models
        apps.clear_cache()

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

    # `auth` app is imported, but not installed in this test (thanks to
    # MigrationTestBase), so we need to exclude checks registered by this app.
    @override_system_checks([])
    def test_files_content(self):
        self.assertTableNotExists("migrations_unicodemodel")
        apps.register_model('migrations', UnicodeModel)
        with override_settings(MIGRATION_MODULES={"migrations": self.migration_pkg}):
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

        with codecs.open(initial_file, 'r', encoding='utf-8') as fp:
            content = fp.read()
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

    # `auth` app is imported, but not installed in this test (thanks to
    # MigrationTestBase), so we need to exclude checks registered by this app.
    @override_system_checks([])
    def test_failing_migration(self):
        #21280 - If a migration fails to serialize, it shouldn't generate an empty file.
        apps.register_model('migrations', UnserializableModel)

        with six.assertRaisesRegex(self, ValueError, r'Cannot serialize'):
            with override_settings(MIGRATION_MODULES={"migrations": self.migration_pkg}):
                    call_command("makemigrations", "migrations", verbosity=0)

        initial_file = os.path.join(self.migration_dir, "0001_initial.py")
        self.assertFalse(os.path.exists(initial_file))
