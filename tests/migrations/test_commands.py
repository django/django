# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import shutil

from django.apps import apps
from django.db import connection, models
from django.core.management import call_command, CommandError
from django.db.migrations import questioner
from django.test import override_settings, override_system_checks
from django.utils import six
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
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_sqlmigrate(self):
        """
        Makes sure that sqlmigrate does something.
        """
        # Make sure the output is wrapped in a transaction
        stdout = six.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=stdout)
        output = stdout.getvalue()
        self.assertIn(connection.ops.start_transaction_sql(), output)
        self.assertIn(connection.ops.end_transaction_sql(), output)

        # Test forwards. All the databases agree on CREATE TABLE, at least.
        stdout = six.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=stdout)
        self.assertIn("create table", stdout.getvalue().lower())

        # Cannot generate the reverse SQL unless we've applied the migration.
        call_command("migrate", "migrations", verbosity=0)

        # And backwards is a DROP TABLE
        stdout = six.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=stdout, backwards=True)
        self.assertIn("drop table", stdout.getvalue().lower())

        # Cleanup by unmigrating everything
        call_command("migrate", "migrations", "zero", verbosity=0)

    @override_system_checks([])
    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.migrated_app",
            "migrations.migrations_test_apps.migrated_unapplied_app",
            "migrations.migrations_test_apps.unmigrated_app"])
    def test_regression_22823_unmigrated_fk_to_migrated_model(self):
        """
        https://code.djangoproject.com/ticket/22823

        Assuming you have 3 apps, `A`, `B`, and `C`, such that:

        * `A` has migrations
        * `B` has a migration we want to apply
        * `C` has no migrations, but has an FK to `A`

        When we try to migrate "B", an exception occurs because the
        "B" was not included in the ProjectState that is used to detect
        soft-applied migrations.
        """
        stdout = six.StringIO()
        call_command("migrate", "migrated_unapplied_app", stdout=stdout)


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
        self.migration_dir = os.path.join(self.test_dir, 'migrations_%d' % self.creation_counter)
        self.migration_pkg = "migrations.migrations_%d" % self.creation_counter
        self._old_models = apps.app_configs['migrations'].models.copy()

    def tearDown(self):
        apps.app_configs['migrations'].models = self._old_models
        apps.all_models['migrations'] = self._old_models
        apps.clear_cache()

        _cwd = os.getcwd()
        os.chdir(self.test_dir)
        try:
            try:
                self._rmrf(self.migration_dir)
            except OSError:
                pass

            try:
                self._rmrf(os.path.join(self.test_dir,
                           "test_migrations_path_doesnt_exist"))
            except OSError:
                pass
        finally:
            os.chdir(_cwd)

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
            self.assertTrue('# -*- coding: utf-8 -*-' in content)
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

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_conflict_exit(self):
        """
        Makes sure that makemigrations exits if it detects a conflict.
        """
        with self.assertRaises(CommandError):
            call_command("makemigrations")

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_makemigrations_merge_no_conflict(self):
        """
        Makes sure that makemigrations exits if in merge mode with no conflicts.
        """
        stdout = six.StringIO()
        try:
            call_command("makemigrations", merge=True, stdout=stdout)
        except CommandError:
            self.fail("Makemigrations errored in merge mode with no conflicts")
        self.assertIn("No conflicts detected to merge.", stdout.getvalue())

    @override_system_checks([])
    def test_makemigrations_no_app_sys_exit(self):
        """
        Makes sure that makemigrations exits if a non-existent app is specified.
        """
        stderr = six.StringIO()
        with self.assertRaises(SystemExit):
            call_command("makemigrations", "this_app_does_not_exist", stderr=stderr)
        self.assertIn("'this_app_does_not_exist' could not be found.", stderr.getvalue())

    @override_system_checks([])
    def test_makemigrations_empty_no_app_specified(self):
        """
        Makes sure that makemigrations exits if no app is specified with 'empty' mode.
        """
        with override_settings(MIGRATION_MODULES={"migrations": self.migration_pkg}):
            self.assertRaises(CommandError, call_command, "makemigrations", empty=True)

    @override_system_checks([])
    def test_makemigrations_empty_migration(self):
        """
        Makes sure that makemigrations properly constructs an empty migration.
        """
        with override_settings(MIGRATION_MODULES={"migrations": self.migration_pkg}):
            try:
                call_command("makemigrations", "migrations", empty=True, verbosity=0)
            except CommandError:
                self.fail("Makemigrations errored in creating empty migration for a proper app.")

        initial_file = os.path.join(self.migration_dir, "0001_initial.py")

        # Check for existing 0001_initial.py file in migration folder
        self.assertTrue(os.path.exists(initial_file))

        with codecs.open(initial_file, 'r', encoding='utf-8') as fp:
            content = fp.read()
            self.assertTrue('# -*- coding: utf-8 -*-' in content)

            # Remove all whitespace to check for empty dependencies and operations
            content = content.replace(' ', '')
            self.assertIn('dependencies=[\n]', content)
            self.assertIn('operations=[\n]', content)

    @override_system_checks([])
    def test_makemigrations_no_changes_no_apps(self):
        """
        Makes sure that makemigrations exits when there are no changes and no apps are specified.
        """
        stdout = six.StringIO()
        call_command("makemigrations", stdout=stdout)
        self.assertIn("No changes detected", stdout.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_no_changes"})
    def test_makemigrations_no_changes(self):
        """
        Makes sure that makemigrations exits when there are no changes to an app.
        """
        stdout = six.StringIO()
        call_command("makemigrations", "migrations", stdout=stdout)
        self.assertIn("No changes detected in app 'migrations'", stdout.getvalue())

    @override_system_checks([])
    def test_makemigrations_migrations_announce(self):
        """
        Makes sure that makemigrations announces the migration at the default verbosity level.
        """
        stdout = six.StringIO()
        with override_settings(MIGRATION_MODULES={"migrations": self.migration_pkg}):
            call_command("makemigrations", "migrations", stdout=stdout)
        self.assertIn("Migrations for 'migrations'", stdout.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_no_ancestor"})
    def test_makemigrations_no_common_ancestor(self):
        """
        Makes sure that makemigrations fails to merge migrations with no common ancestor.
        """
        with self.assertRaises(ValueError) as context:
            call_command("makemigrations", "migrations", merge=True)
        exception_message = str(context.exception)
        self.assertIn("Could not find common ancestor of", exception_message)
        self.assertIn("0002_second", exception_message)
        self.assertIn("0002_conflicting_second", exception_message)

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_interactive_reject(self):
        """
        Makes sure that makemigrations enters and exits interactive mode properly.
        """
        # Monkeypatch interactive questioner to auto reject
        old_input = questioner.input
        questioner.input = lambda _: "N"
        try:
            call_command("makemigrations", "migrations", merge=True, interactive=True, verbosity=0)
            merge_file = os.path.join(self.test_dir, 'test_migrations_conflict', '0003_merge.py')
            self.assertFalse(os.path.exists(merge_file))
        except CommandError:
            self.fail("Makemigrations failed while running interactive questioner")
        finally:
            questioner.input = old_input

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_interactive_accept(self):
        """
        Makes sure that makemigrations enters interactive mode and merges properly.
        """
        # Monkeypatch interactive questioner to auto accept
        old_input = questioner.input
        questioner.input = lambda _: "y"
        stdout = six.StringIO()
        try:
            call_command("makemigrations", "migrations", merge=True, interactive=True, stdout=stdout)
            merge_file = os.path.join(self.test_dir, 'test_migrations_conflict', '0003_merge.py')
            self.assertTrue(os.path.exists(merge_file))
            os.remove(merge_file)
            self.assertFalse(os.path.exists(merge_file))
        except CommandError:
            self.fail("Makemigrations failed while running interactive questioner")
        finally:
            questioner.input = old_input
        self.assertIn("Created new merge migration", stdout.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_handle_merge(self):
        """
        Makes sure that makemigrations properly merges the conflicting migrations with --noinput.
        """
        stdout = six.StringIO()
        call_command("makemigrations", "migrations", merge=True, interactive=False, stdout=stdout)
        self.assertIn("Merging migrations", stdout.getvalue())
        self.assertIn("Branch 0002_second", stdout.getvalue())
        self.assertIn("Branch 0002_conflicting_second", stdout.getvalue())
        merge_file = os.path.join(self.test_dir, 'test_migrations_conflict', '0003_merge.py')
        self.assertTrue(os.path.exists(merge_file))
        os.remove(merge_file)
        self.assertFalse(os.path.exists(merge_file))
        self.assertIn("Created new merge migration", stdout.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigration_merge_dry_run(self):
        """
        Makes sure that makemigrations respects --dry-run option when fixing
        migration conflicts (#24427).
        """
        out = six.StringIO()
        call_command("makemigrations", "migrations", dry_run=True, merge=True, interactive=False, stdout=out)
        merge_file = os.path.join(self.test_dir, '0003_merge.py')
        self.assertFalse(os.path.exists(merge_file))
        output = force_text(out.getvalue())
        self.assertIn("Merging migrations", output)
        self.assertIn("Branch 0002_second", output)
        self.assertIn("Branch 0002_conflicting_second", output)
        self.assertNotIn("Created new merge migration", output)

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigration_merge_dry_run_verbosity_3(self):
        """
        Makes sure that `makemigrations --merge --dry-run` writes the merge
        migration file to stdout with `verbosity == 3` (#24427).
        """
        out = six.StringIO()
        call_command("makemigrations", "migrations", dry_run=True, merge=True, interactive=False,
                     stdout=out, verbosity=3)
        merge_file = os.path.join(self.test_dir, '0003_merge.py')
        self.assertFalse(os.path.exists(merge_file))
        output = force_text(out.getvalue())
        self.assertIn("Merging migrations", output)
        self.assertIn("Branch 0002_second", output)
        self.assertIn("Branch 0002_conflicting_second", output)
        self.assertNotIn("Created new merge migration", output)

        # Additional output caused by verbosity 3
        # The complete merge migration file that would be written
        self.assertIn("# -*- coding: utf-8 -*-", output)
        self.assertIn("class Migration(migrations.Migration):", output)
        self.assertIn("dependencies = [", output)
        self.assertIn("('migrations', '0002_second')", output)
        self.assertIn("('migrations', '0002_conflicting_second')", output)
        self.assertIn("operations = [", output)
        self.assertIn("]", output)

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_no_default"})
    def test_makemigrations_dry_run(self):
        """
        Ticket #22676 -- `makemigrations --dry-run` should not ask for defaults.
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)
            silly_date = models.DateField()  # Added field without a default

            class Meta:
                app_label = "migrations"

        stdout = six.StringIO()
        call_command("makemigrations", "migrations", dry_run=True, stdout=stdout)
        # Output the expected changes directly, without asking for defaults
        self.assertIn("Add field silly_date to sillymodel", stdout.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_no_default"})
    def test_makemigrations_dry_run_verbosity_3(self):
        """
        Ticket #22675 -- Allow `makemigrations --dry-run` to output the
        migrations file to stdout (with verbosity == 3).
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)
            silly_char = models.CharField(default="")

            class Meta:
                app_label = "migrations"

        stdout = six.StringIO()
        call_command("makemigrations", "migrations", dry_run=True, stdout=stdout, verbosity=3)

        # Normal --dry-run output
        self.assertIn("- Add field silly_char to sillymodel", stdout.getvalue())

        # Additional output caused by verbosity 3
        # The complete migrations file that would be written
        self.assertIn("# -*- coding: utf-8 -*-", stdout.getvalue())
        self.assertIn("class Migration(migrations.Migration):", stdout.getvalue())
        self.assertIn("dependencies = [", stdout.getvalue())
        self.assertIn("('migrations', '0001_initial'),", stdout.getvalue())
        self.assertIn("migrations.AddField(", stdout.getvalue())
        self.assertIn("model_name='sillymodel',", stdout.getvalue())
        self.assertIn("name='silly_char',", stdout.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_path_doesnt_exist.foo.bar"})
    def test_makemigrations_migrations_modules_path_not_exist(self):
        """
        Ticket #22682 -- Makemigrations fails when specifying custom location
        for migration files (using MIGRATION_MODULES) if the custom path
        doesn't already exist.
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)

            class Meta:
                app_label = "migrations"

        stdout = six.StringIO()
        call_command("makemigrations", "migrations", stdout=stdout)

        # Command output indicates the migration is created.
        self.assertIn(" - Create model SillyModel", stdout.getvalue())

        # Migrations file is actually created in the expected path.
        self.assertTrue(os.path.isfile(os.path.join(self.test_dir,
                       "test_migrations_path_doesnt_exist", "foo", "bar",
                       "0001_initial.py")))

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"})
    def test_makemigrations_interactive_by_default(self):
        """
        Makes sure that the user is prompted to merge by default if there are
        conflicts and merge is True. Answer negative to differentiate it from
        behavior when --noinput is specified.
        """
        # Monkeypatch interactive questioner to auto reject
        old_input = questioner.input
        questioner.input = lambda _: "N"
        stdout = six.StringIO()
        merge_file = os.path.join(self.test_dir, 'test_migrations_conflict', '0003_merge.py')
        try:
            call_command("makemigrations", "migrations", merge=True, stdout=stdout)
            # This will fail if interactive is False by default
            self.assertFalse(os.path.exists(merge_file))
        except CommandError:
            self.fail("Makemigrations failed while running interactive questioner")
        finally:
            questioner.input = old_input
            if os.path.exists(merge_file):
                os.remove(merge_file)
        self.assertNotIn("Created new merge migration", stdout.getvalue())

    @override_system_checks([])
    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_no_changes"},
        INSTALLED_APPS=[
            "migrations",
            "migrations.migrations_test_apps.unspecified_app_with_conflict"])
    def test_makemigrations_unspecified_app_with_conflict_no_merge(self):
        """
        Makes sure that makemigrations does not raise a CommandError when an
        unspecified app has conflicting migrations.
        """
        try:
            call_command("makemigrations", "migrations", merge=False, verbosity=0)
        except CommandError:
            self.fail("Makemigrations fails resolving conflicts in an unspecified app")

    @override_system_checks([])
    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.migrated_app",
            "migrations.migrations_test_apps.unspecified_app_with_conflict"])
    def test_makemigrations_unspecified_app_with_conflict_merge(self):
        """
        Makes sure that makemigrations does not create a merge for an
        unspecified app even if it has conflicting migrations.
        """
        # Monkeypatch interactive questioner to auto accept
        old_input = questioner.input
        questioner.input = lambda _: "y"
        stdout = six.StringIO()
        merge_file = os.path.join(self.test_dir,
                                  'migrations_test_apps',
                                  'unspecified_app_with_conflict',
                                  'migrations',
                                  '0003_merge.py')
        try:
            call_command("makemigrations", "migrated_app", merge=True, interactive=True, stdout=stdout)
            self.assertFalse(os.path.exists(merge_file))
            self.assertIn("No conflicts detected to merge.", stdout.getvalue())
        except CommandError:
            self.fail("Makemigrations fails resolving conflicts in an unspecified app")
        finally:
            questioner.input = old_input
            if os.path.exists(merge_file):
                os.remove(merge_file)


class SquashMigrationsTest(MigrationTestBase):
    """
    Tests running the squashmigrations command.
    """

    path = "test_migrations/0001_squashed_0002_second.py"
    path = os.path.join(MigrationTestBase.test_dir, path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_squashmigrations_squashes(self):
        """
        Tests that squashmigrations squashes migrations.
        """
        call_command("squashmigrations", "migrations", "0002", interactive=False, verbosity=0)
        self.assertTrue(os.path.exists(self.path))

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_squashmigrations_optimizes(self):
        """
        Tests that squashmigrations optimizes operations.
        """
        out = six.StringIO()
        call_command("squashmigrations", "migrations", "0002", interactive=False, verbosity=1, stdout=out)
        self.assertIn("Optimized from 7 operations to 5 operations.", out.getvalue())

    @override_system_checks([])
    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_ticket_23799_squashmigrations_no_optimize(self):
        """
        Makes sure that squashmigrations --no-optimize really doesn't optimize operations.
        """
        out = six.StringIO()
        call_command("squashmigrations", "migrations", "0002",
                     interactive=False, verbosity=1, no_optimize=True, stdout=out)
        self.assertIn("Skipping optimization", out.getvalue())
