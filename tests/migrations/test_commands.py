import datetime
import importlib
import io
import os
import shutil
import sys
from unittest import mock

from django.apps import apps
from django.core.management import CommandError, call_command
from django.db import (
    ConnectionHandler,
    DatabaseError,
    OperationalError,
    connection,
    connections,
    models,
)
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.backends.utils import truncate_name
from django.db.migrations.exceptions import InconsistentMigrationHistory
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase, override_settings, skipUnlessDBFeature
from django.test.utils import captured_stdout
from django.utils import timezone
from django.utils.version import get_docs_version

from .models import UnicodeModel, UnserializableModel
from .routers import TestRouter
from .test_base import MigrationTestBase

HAS_BLACK = shutil.which("black")


class MigrateTests(MigrationTestBase):
    """
    Tests running the migrate command.
    """

    databases = {"default", "other"}

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_migrate(self):
        """
        Tests basic usage of the migrate command.
        """
        # No tables are created
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")
        # Run the migrations to 0001 only
        stdout = io.StringIO()
        call_command(
            "migrate", "migrations", "0001", verbosity=2, stdout=stdout, no_color=True
        )
        stdout = stdout.getvalue()
        self.assertIn(
            "Target specific migration: 0001_initial, from migrations", stdout
        )
        self.assertIn("Applying migrations.0001_initial... OK", stdout)
        self.assertIn("Running pre-migrate handlers for application migrations", stdout)
        self.assertIn(
            "Running post-migrate handlers for application migrations", stdout
        )
        # The correct tables exist
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")
        # Run migrations all the way
        call_command("migrate", verbosity=0)
        # The correct tables exist
        self.assertTableExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableExists("migrations_book")
        # Unmigrate everything
        stdout = io.StringIO()
        call_command(
            "migrate", "migrations", "zero", verbosity=2, stdout=stdout, no_color=True
        )
        stdout = stdout.getvalue()
        self.assertIn("Unapply all migrations: migrations", stdout)
        self.assertIn("Unapplying migrations.0002_second... OK", stdout)
        self.assertIn("Running pre-migrate handlers for application migrations", stdout)
        self.assertIn(
            "Running post-migrate handlers for application migrations", stdout
        )
        # Tables are gone
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")

    @override_settings(
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "migrations.migrations_test_apps.migrated_app",
        ]
    )
    def test_migrate_with_system_checks(self):
        out = io.StringIO()
        call_command("migrate", skip_checks=False, no_color=True, stdout=out)
        self.assertIn("Apply all migrations: migrated_app", out.getvalue())

    @override_settings(
        INSTALLED_APPS=[
            "migrations",
            "migrations.migrations_test_apps.unmigrated_app_syncdb",
        ]
    )
    def test_app_without_migrations(self):
        msg = "App 'unmigrated_app_syncdb' does not have migrations."
        with self.assertRaisesMessage(CommandError, msg):
            call_command("migrate", app_label="unmigrated_app_syncdb")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_clashing_prefix"}
    )
    def test_ambiguous_prefix(self):
        msg = (
            "More than one migration matches 'a' in app 'migrations'. Please "
            "be more specific."
        )
        with self.assertRaisesMessage(CommandError, msg):
            call_command("migrate", app_label="migrations", migration_name="a")

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_unknown_prefix(self):
        msg = "Cannot find a migration matching 'nonexistent' from app 'migrations'."
        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                "migrate", app_label="migrations", migration_name="nonexistent"
            )

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_initial_false"}
    )
    def test_migrate_initial_false(self):
        """
        `Migration.initial = False` skips fake-initial detection.
        """
        # Make sure no tables are created
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        # Run the migrations to 0001 only
        call_command("migrate", "migrations", "0001", verbosity=0)
        # Fake rollback
        call_command("migrate", "migrations", "zero", fake=True, verbosity=0)
        # Make sure fake-initial detection does not run
        with self.assertRaises(DatabaseError):
            call_command(
                "migrate", "migrations", "0001", fake_initial=True, verbosity=0
            )

        call_command("migrate", "migrations", "0001", fake=True, verbosity=0)
        # Real rollback
        call_command("migrate", "migrations", "zero", verbosity=0)
        # Make sure it's all gone
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations"},
        DATABASE_ROUTERS=["migrations.routers.TestRouter"],
    )
    def test_migrate_fake_initial(self):
        """
        --fake-initial only works if all tables created in the initial
        migration of an app exists. Database routers must be obeyed when doing
        that check.
        """
        # Make sure no tables are created
        for db in self.databases:
            self.assertTableNotExists("migrations_author", using=db)
            self.assertTableNotExists("migrations_tribble", using=db)
        # Run the migrations to 0001 only
        call_command("migrate", "migrations", "0001", verbosity=0)
        call_command("migrate", "migrations", "0001", verbosity=0, database="other")
        # Make sure the right tables exist
        self.assertTableExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        # Also check the "other" database
        self.assertTableNotExists("migrations_author", using="other")
        self.assertTableExists("migrations_tribble", using="other")

        # Fake a roll-back
        call_command("migrate", "migrations", "zero", fake=True, verbosity=0)
        call_command(
            "migrate", "migrations", "zero", fake=True, verbosity=0, database="other"
        )
        # Make sure the tables still exist
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble", using="other")
        # Try to run initial migration
        with self.assertRaises(DatabaseError):
            call_command("migrate", "migrations", "0001", verbosity=0)
        # Run initial migration with an explicit --fake-initial
        out = io.StringIO()
        with mock.patch(
            "django.core.management.color.supports_color", lambda *args: False
        ):
            call_command(
                "migrate",
                "migrations",
                "0001",
                fake_initial=True,
                stdout=out,
                verbosity=1,
            )
            call_command(
                "migrate",
                "migrations",
                "0001",
                fake_initial=True,
                verbosity=0,
                database="other",
            )
        self.assertIn("migrations.0001_initial... faked", out.getvalue().lower())
        try:
            # Run migrations all the way.
            call_command("migrate", verbosity=0)
            call_command("migrate", verbosity=0, database="other")
            self.assertTableExists("migrations_author")
            self.assertTableNotExists("migrations_tribble")
            self.assertTableExists("migrations_book")
            self.assertTableNotExists("migrations_author", using="other")
            self.assertTableNotExists("migrations_tribble", using="other")
            self.assertTableNotExists("migrations_book", using="other")
            # Fake a roll-back.
            call_command("migrate", "migrations", "zero", fake=True, verbosity=0)
            call_command(
                "migrate",
                "migrations",
                "zero",
                fake=True,
                verbosity=0,
                database="other",
            )
            self.assertTableExists("migrations_author")
            self.assertTableNotExists("migrations_tribble")
            self.assertTableExists("migrations_book")
            # Run initial migration.
            with self.assertRaises(DatabaseError):
                call_command("migrate", "migrations", verbosity=0)
            # Run initial migration with an explicit --fake-initial.
            with self.assertRaises(DatabaseError):
                # Fails because "migrations_tribble" does not exist but needs
                # to in order to make --fake-initial work.
                call_command("migrate", "migrations", fake_initial=True, verbosity=0)
            # Fake an apply.
            call_command("migrate", "migrations", fake=True, verbosity=0)
            call_command(
                "migrate", "migrations", fake=True, verbosity=0, database="other"
            )
        finally:
            # Unmigrate everything.
            call_command("migrate", "migrations", "zero", verbosity=0)
            call_command("migrate", "migrations", "zero", verbosity=0, database="other")
        # Make sure it's all gone
        for db in self.databases:
            self.assertTableNotExists("migrations_author", using=db)
            self.assertTableNotExists("migrations_tribble", using=db)
            self.assertTableNotExists("migrations_book", using=db)

    @skipUnlessDBFeature("ignores_table_name_case")
    def test_migrate_fake_initial_case_insensitive(self):
        with override_settings(
            MIGRATION_MODULES={
                "migrations": "migrations.test_fake_initial_case_insensitive.initial",
            }
        ):
            call_command("migrate", "migrations", "0001", verbosity=0)
            call_command("migrate", "migrations", "zero", fake=True, verbosity=0)

        with override_settings(
            MIGRATION_MODULES={
                "migrations": (
                    "migrations.test_fake_initial_case_insensitive.fake_initial"
                ),
            }
        ):
            out = io.StringIO()
            call_command(
                "migrate",
                "migrations",
                "0001",
                fake_initial=True,
                stdout=out,
                verbosity=1,
                no_color=True,
            )
            self.assertIn(
                "migrations.0001_initial... faked",
                out.getvalue().lower(),
            )

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations_fake_split_initial"
        }
    )
    def test_migrate_fake_split_initial(self):
        """
        Split initial migrations can be faked with --fake-initial.
        """
        try:
            call_command("migrate", "migrations", "0002", verbosity=0)
            call_command("migrate", "migrations", "zero", fake=True, verbosity=0)
            out = io.StringIO()
            with mock.patch(
                "django.core.management.color.supports_color", lambda *args: False
            ):
                call_command(
                    "migrate",
                    "migrations",
                    "0002",
                    fake_initial=True,
                    stdout=out,
                    verbosity=1,
                )
            value = out.getvalue().lower()
            self.assertIn("migrations.0001_initial... faked", value)
            self.assertIn("migrations.0002_second... faked", value)
        finally:
            # Fake an apply.
            call_command("migrate", "migrations", fake=True, verbosity=0)
            # Unmigrate everything.
            call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_conflict"}
    )
    def test_migrate_conflict_exit(self):
        """
        migrate exits if it detects a conflict.
        """
        msg = (
            "Conflicting migrations detected; multiple leaf nodes in the "
            "migration graph: (0002_conflicting_second, 0002_second in "
            "migrations).\n"
            "To fix them run 'python manage.py makemigrations --merge'"
        )
        with self.assertRaisesMessage(CommandError, msg):
            call_command("migrate", "migrations")

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations",
        }
    )
    def test_migrate_check(self):
        with self.assertRaises(SystemExit):
            call_command("migrate", "migrations", "0001", check_unapplied=True)
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        self.assertTableNotExists("migrations_book")

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations_plan",
        }
    )
    def test_migrate_check_plan(self):
        out = io.StringIO()
        with self.assertRaises(SystemExit):
            call_command(
                "migrate",
                "migrations",
                "0001",
                check_unapplied=True,
                plan=True,
                stdout=out,
                no_color=True,
            )
        self.assertEqual(
            "Planned operations:\n"
            "migrations.0001_initial\n"
            "    Create model Salamander\n"
            "    Raw Python operation -> Grow salamander tail.\n",
            out.getvalue(),
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_showmigrations_list(self):
        """
        showmigrations --list  displays migrations and whether or not they're
        applied.
        """
        out = io.StringIO()
        with mock.patch(
            "django.core.management.color.supports_color", lambda *args: True
        ):
            call_command(
                "showmigrations", format="list", stdout=out, verbosity=0, no_color=False
            )
        self.assertEqual(
            "\x1b[1mmigrations\n\x1b[0m [ ] 0001_initial\n [ ] 0002_second\n",
            out.getvalue().lower(),
        )

        call_command("migrate", "migrations", "0001", verbosity=0)

        out = io.StringIO()
        # Giving the explicit app_label tests for selective `show_list` in the command
        call_command(
            "showmigrations",
            "migrations",
            format="list",
            stdout=out,
            verbosity=0,
            no_color=True,
        )
        self.assertEqual(
            "migrations\n [x] 0001_initial\n [ ] 0002_second\n", out.getvalue().lower()
        )
        out = io.StringIO()
        # Applied datetimes are displayed at verbosity 2+.
        call_command(
            "showmigrations", "migrations", stdout=out, verbosity=2, no_color=True
        )
        migration1 = MigrationRecorder(connection).migration_qs.get(
            app="migrations", name="0001_initial"
        )
        self.assertEqual(
            "migrations\n"
            " [x] 0001_initial (applied at %s)\n"
            " [ ] 0002_second\n" % migration1.applied.strftime("%Y-%m-%d %H:%M:%S"),
            out.getvalue().lower(),
        )
        # Cleanup by unmigrating everything
        call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_showmigrations_list_squashed(self):
        out = io.StringIO()
        call_command(
            "showmigrations", format="list", stdout=out, verbosity=2, no_color=True
        )
        self.assertEqual(
            "migrations\n [ ] 0001_squashed_0002 (2 squashed migrations)\n",
            out.getvalue().lower(),
        )
        out = io.StringIO()
        call_command(
            "migrate",
            "migrations",
            "0001_squashed_0002",
            stdout=out,
            verbosity=2,
            no_color=True,
        )
        try:
            self.assertIn(
                "operations to perform:\n"
                "  target specific migration: 0001_squashed_0002, from migrations\n"
                "running pre-migrate handlers for application migrations\n"
                "running migrations:\n"
                "  applying migrations.0001_squashed_0002... ok (",
                out.getvalue().lower(),
            )
            out = io.StringIO()
            call_command(
                "showmigrations", format="list", stdout=out, verbosity=2, no_color=True
            )
            self.assertEqual(
                "migrations\n [x] 0001_squashed_0002 (2 squashed migrations)\n",
                out.getvalue().lower(),
            )
        finally:
            # Unmigrate everything.
            call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_run_before"}
    )
    def test_showmigrations_plan(self):
        """
        Tests --plan output of showmigrations command
        """
        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out)
        self.assertEqual(
            "[ ]  migrations.0001_initial\n"
            "[ ]  migrations.0003_third\n"
            "[ ]  migrations.0002_second\n",
            out.getvalue().lower(),
        )

        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out, verbosity=2)
        self.assertEqual(
            "[ ]  migrations.0001_initial\n"
            "[ ]  migrations.0003_third ... (migrations.0001_initial)\n"
            "[ ]  migrations.0002_second ... (migrations.0001_initial, "
            "migrations.0003_third)\n",
            out.getvalue().lower(),
        )
        call_command("migrate", "migrations", "0003", verbosity=0)

        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out)
        self.assertEqual(
            "[x]  migrations.0001_initial\n"
            "[x]  migrations.0003_third\n"
            "[ ]  migrations.0002_second\n",
            out.getvalue().lower(),
        )

        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out, verbosity=2)
        self.assertEqual(
            "[x]  migrations.0001_initial\n"
            "[x]  migrations.0003_third ... (migrations.0001_initial)\n"
            "[ ]  migrations.0002_second ... (migrations.0001_initial, "
            "migrations.0003_third)\n",
            out.getvalue().lower(),
        )

        # Cleanup by unmigrating everything
        call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_plan"}
    )
    def test_migrate_plan(self):
        """Tests migrate --plan output."""
        out = io.StringIO()
        # Show the plan up to the third migration.
        call_command(
            "migrate", "migrations", "0003", plan=True, stdout=out, no_color=True
        )
        self.assertEqual(
            "Planned operations:\n"
            "migrations.0001_initial\n"
            "    Create model Salamander\n"
            "    Raw Python operation -> Grow salamander tail.\n"
            "migrations.0002_second\n"
            "    Create model Book\n"
            "    Raw SQL operation -> ['SELECT * FROM migrations_book']\n"
            "migrations.0003_third\n"
            "    Create model Author\n"
            "    Raw SQL operation -> ['SELECT * FROM migrations_author']\n",
            out.getvalue(),
        )
        try:
            # Migrate to the third migration.
            call_command("migrate", "migrations", "0003", verbosity=0)
            out = io.StringIO()
            # Show the plan for when there is nothing to apply.
            call_command(
                "migrate", "migrations", "0003", plan=True, stdout=out, no_color=True
            )
            self.assertEqual(
                "Planned operations:\n  No planned migration operations.\n",
                out.getvalue(),
            )
            out = io.StringIO()
            # Show the plan for reverse migration back to 0001.
            call_command(
                "migrate", "migrations", "0001", plan=True, stdout=out, no_color=True
            )
            self.assertEqual(
                "Planned operations:\n"
                "migrations.0003_third\n"
                "    Undo Create model Author\n"
                "    Raw SQL operation -> ['SELECT * FROM migrations_book']\n"
                "migrations.0002_second\n"
                "    Undo Create model Book\n"
                "    Raw SQL operation -> ['SELECT * FROM migrations_salamand…\n",
                out.getvalue(),
            )
            out = io.StringIO()
            # Show the migration plan to fourth, with truncated details.
            call_command(
                "migrate", "migrations", "0004", plan=True, stdout=out, no_color=True
            )
            self.assertEqual(
                "Planned operations:\n"
                "migrations.0004_fourth\n"
                "    Raw SQL operation -> SELECT * FROM migrations_author WHE…\n",
                out.getvalue(),
            )
            # Show the plan when an operation is irreversible.
            # Migrate to the fourth migration.
            call_command("migrate", "migrations", "0004", verbosity=0)
            out = io.StringIO()
            call_command(
                "migrate", "migrations", "0003", plan=True, stdout=out, no_color=True
            )
            self.assertEqual(
                "Planned operations:\n"
                "migrations.0004_fourth\n"
                "    Raw SQL operation -> IRREVERSIBLE\n",
                out.getvalue(),
            )
            out = io.StringIO()
            call_command(
                "migrate", "migrations", "0005", plan=True, stdout=out, no_color=True
            )
            # Operation is marked as irreversible only in the revert plan.
            self.assertEqual(
                "Planned operations:\n"
                "migrations.0005_fifth\n"
                "    Raw Python operation\n"
                "    Raw Python operation\n"
                "    Raw Python operation -> Feed salamander.\n",
                out.getvalue(),
            )
            call_command("migrate", "migrations", "0005", verbosity=0)
            out = io.StringIO()
            call_command(
                "migrate", "migrations", "0004", plan=True, stdout=out, no_color=True
            )
            self.assertEqual(
                "Planned operations:\n"
                "migrations.0005_fifth\n"
                "    Raw Python operation -> IRREVERSIBLE\n"
                "    Raw Python operation -> IRREVERSIBLE\n"
                "    Raw Python operation\n",
                out.getvalue(),
            )
        finally:
            # Cleanup by unmigrating everything: fake the irreversible, then
            # migrate all to zero.
            call_command("migrate", "migrations", "0003", fake=True, verbosity=0)
            call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_empty"}
    )
    def test_showmigrations_no_migrations(self):
        out = io.StringIO()
        call_command("showmigrations", stdout=out, no_color=True)
        self.assertEqual("migrations\n (no migrations)\n", out.getvalue().lower())

    @override_settings(
        INSTALLED_APPS=["migrations.migrations_test_apps.unmigrated_app"]
    )
    def test_showmigrations_unmigrated_app(self):
        out = io.StringIO()
        call_command("showmigrations", "unmigrated_app", stdout=out, no_color=True)
        try:
            self.assertEqual(
                "unmigrated_app\n (no migrations)\n", out.getvalue().lower()
            )
        finally:
            # unmigrated_app.SillyModel has a foreign key to
            # 'migrations.Tribble', but that model is only defined in a
            # migration, so the global app registry never sees it and the
            # reference is left dangling. Remove it to avoid problems in
            # subsequent tests.
            apps._pending_operations.pop(("migrations", "tribble"), None)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_empty"}
    )
    def test_showmigrations_plan_no_migrations(self):
        """
        Tests --plan output of showmigrations command without migrations
        """
        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out, no_color=True)
        self.assertEqual("(no migrations)\n", out.getvalue().lower())

        out = io.StringIO()
        call_command(
            "showmigrations", format="plan", stdout=out, verbosity=2, no_color=True
        )
        self.assertEqual("(no migrations)\n", out.getvalue().lower())

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed_complex"}
    )
    def test_showmigrations_plan_squashed(self):
        """
        Tests --plan output of showmigrations command with squashed migrations.
        """
        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out)
        self.assertEqual(
            "[ ]  migrations.1_auto\n"
            "[ ]  migrations.2_auto\n"
            "[ ]  migrations.3_squashed_5\n"
            "[ ]  migrations.6_auto\n"
            "[ ]  migrations.7_auto\n",
            out.getvalue().lower(),
        )

        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out, verbosity=2)
        self.assertEqual(
            "[ ]  migrations.1_auto\n"
            "[ ]  migrations.2_auto ... (migrations.1_auto)\n"
            "[ ]  migrations.3_squashed_5 ... (migrations.2_auto)\n"
            "[ ]  migrations.6_auto ... (migrations.3_squashed_5)\n"
            "[ ]  migrations.7_auto ... (migrations.6_auto)\n",
            out.getvalue().lower(),
        )

        call_command("migrate", "migrations", "3_squashed_5", verbosity=0)

        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out)
        self.assertEqual(
            "[x]  migrations.1_auto\n"
            "[x]  migrations.2_auto\n"
            "[x]  migrations.3_squashed_5\n"
            "[ ]  migrations.6_auto\n"
            "[ ]  migrations.7_auto\n",
            out.getvalue().lower(),
        )

        out = io.StringIO()
        call_command("showmigrations", format="plan", stdout=out, verbosity=2)
        self.assertEqual(
            "[x]  migrations.1_auto\n"
            "[x]  migrations.2_auto ... (migrations.1_auto)\n"
            "[x]  migrations.3_squashed_5 ... (migrations.2_auto)\n"
            "[ ]  migrations.6_auto ... (migrations.3_squashed_5)\n"
            "[ ]  migrations.7_auto ... (migrations.6_auto)\n",
            out.getvalue().lower(),
        )

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.mutate_state_b",
            "migrations.migrations_test_apps.alter_fk.author_app",
            "migrations.migrations_test_apps.alter_fk.book_app",
        ]
    )
    def test_showmigrations_plan_single_app_label(self):
        """
        `showmigrations --plan app_label` output with a single app_label.
        """
        # Single app with no dependencies on other apps.
        out = io.StringIO()
        call_command("showmigrations", "mutate_state_b", format="plan", stdout=out)
        self.assertEqual(
            "[ ]  mutate_state_b.0001_initial\n[ ]  mutate_state_b.0002_add_field\n",
            out.getvalue(),
        )
        # Single app with dependencies.
        out = io.StringIO()
        call_command("showmigrations", "author_app", format="plan", stdout=out)
        self.assertEqual(
            "[ ]  author_app.0001_initial\n"
            "[ ]  book_app.0001_initial\n"
            "[ ]  author_app.0002_alter_id\n",
            out.getvalue(),
        )
        # Some migrations already applied.
        call_command("migrate", "author_app", "0001", verbosity=0)
        out = io.StringIO()
        call_command("showmigrations", "author_app", format="plan", stdout=out)
        self.assertEqual(
            "[X]  author_app.0001_initial\n"
            "[ ]  book_app.0001_initial\n"
            "[ ]  author_app.0002_alter_id\n",
            out.getvalue(),
        )
        # Cleanup by unmigrating author_app.
        call_command("migrate", "author_app", "zero", verbosity=0)

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.mutate_state_b",
            "migrations.migrations_test_apps.alter_fk.author_app",
            "migrations.migrations_test_apps.alter_fk.book_app",
        ]
    )
    def test_showmigrations_plan_multiple_app_labels(self):
        """
        `showmigrations --plan app_label` output with multiple app_labels.
        """
        # Multiple apps: author_app depends on book_app; mutate_state_b doesn't
        # depend on other apps.
        out = io.StringIO()
        call_command(
            "showmigrations", "mutate_state_b", "author_app", format="plan", stdout=out
        )
        self.assertEqual(
            "[ ]  author_app.0001_initial\n"
            "[ ]  book_app.0001_initial\n"
            "[ ]  author_app.0002_alter_id\n"
            "[ ]  mutate_state_b.0001_initial\n"
            "[ ]  mutate_state_b.0002_add_field\n",
            out.getvalue(),
        )
        # Multiple apps: args order shouldn't matter (the same result is
        # expected as above).
        out = io.StringIO()
        call_command(
            "showmigrations", "author_app", "mutate_state_b", format="plan", stdout=out
        )
        self.assertEqual(
            "[ ]  author_app.0001_initial\n"
            "[ ]  book_app.0001_initial\n"
            "[ ]  author_app.0002_alter_id\n"
            "[ ]  mutate_state_b.0001_initial\n"
            "[ ]  mutate_state_b.0002_add_field\n",
            out.getvalue(),
        )

    @override_settings(
        INSTALLED_APPS=["migrations.migrations_test_apps.unmigrated_app"]
    )
    def test_showmigrations_plan_app_label_no_migrations(self):
        out = io.StringIO()
        call_command(
            "showmigrations", "unmigrated_app", format="plan", stdout=out, no_color=True
        )
        try:
            self.assertEqual("(no migrations)\n", out.getvalue())
        finally:
            # unmigrated_app.SillyModel has a foreign key to
            # 'migrations.Tribble', but that model is only defined in a
            # migration, so the global app registry never sees it and the
            # reference is left dangling. Remove it to avoid problems in
            # subsequent tests.
            apps._pending_operations.pop(("migrations", "tribble"), None)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_sqlmigrate_forwards(self):
        """
        sqlmigrate outputs forward looking SQL.
        """
        out = io.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=out)

        lines = out.getvalue().splitlines()

        if connection.features.can_rollback_ddl:
            self.assertEqual(lines[0], connection.ops.start_transaction_sql())
            self.assertEqual(lines[-1], connection.ops.end_transaction_sql())
            lines = lines[1:-1]

        self.assertEqual(
            lines[:3],
            [
                "--",
                "-- Create model Author",
                "--",
            ],
        )
        self.assertIn(
            "create table %s" % connection.ops.quote_name("migrations_author").lower(),
            lines[3].lower(),
        )
        pos = lines.index("--", 3)
        self.assertEqual(
            lines[pos : pos + 3],
            [
                "--",
                "-- Create model Tribble",
                "--",
            ],
        )
        self.assertIn(
            "create table %s" % connection.ops.quote_name("migrations_tribble").lower(),
            lines[pos + 3].lower(),
        )
        pos = lines.index("--", pos + 3)
        self.assertEqual(
            lines[pos : pos + 3],
            [
                "--",
                "-- Add field bool to tribble",
                "--",
            ],
        )
        pos = lines.index("--", pos + 3)
        self.assertEqual(
            lines[pos : pos + 3],
            [
                "--",
                "-- Alter unique_together for author (1 constraint(s))",
                "--",
            ],
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_sqlmigrate_backwards(self):
        """
        sqlmigrate outputs reverse looking SQL.
        """
        # Cannot generate the reverse SQL unless we've applied the migration.
        call_command("migrate", "migrations", verbosity=0)

        out = io.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=out, backwards=True)

        lines = out.getvalue().splitlines()
        try:
            if connection.features.can_rollback_ddl:
                self.assertEqual(lines[0], connection.ops.start_transaction_sql())
                self.assertEqual(lines[-1], connection.ops.end_transaction_sql())
                lines = lines[1:-1]

            self.assertEqual(
                lines[:3],
                [
                    "--",
                    "-- Alter unique_together for author (1 constraint(s))",
                    "--",
                ],
            )
            pos = lines.index("--", 3)
            self.assertEqual(
                lines[pos : pos + 3],
                [
                    "--",
                    "-- Add field bool to tribble",
                    "--",
                ],
            )
            pos = lines.index("--", pos + 3)
            self.assertEqual(
                lines[pos : pos + 3],
                [
                    "--",
                    "-- Create model Tribble",
                    "--",
                ],
            )
            next_pos = lines.index("--", pos + 3)
            drop_table_sql = (
                "drop table %s"
                % connection.ops.quote_name("migrations_tribble").lower()
            )
            for line in lines[pos + 3 : next_pos]:
                if drop_table_sql in line.lower():
                    break
            else:
                self.fail("DROP TABLE (tribble) not found.")
            pos = next_pos
            self.assertEqual(
                lines[pos : pos + 3],
                [
                    "--",
                    "-- Create model Author",
                    "--",
                ],
            )
            drop_table_sql = (
                "drop table %s" % connection.ops.quote_name("migrations_author").lower()
            )
            for line in lines[pos + 3 :]:
                if drop_table_sql in line.lower():
                    break
            else:
                self.fail("DROP TABLE (author) not found.")
        finally:
            # Unmigrate everything.
            call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_non_atomic"}
    )
    def test_sqlmigrate_for_non_atomic_migration(self):
        """
        Transaction wrappers aren't shown for non-atomic migrations.
        """
        out = io.StringIO()
        call_command("sqlmigrate", "migrations", "0001", stdout=out)
        output = out.getvalue().lower()
        queries = [q.strip() for q in output.splitlines()]
        if connection.ops.start_transaction_sql():
            self.assertNotIn(connection.ops.start_transaction_sql().lower(), queries)
        self.assertNotIn(connection.ops.end_transaction_sql().lower(), queries)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_sqlmigrate_for_non_transactional_databases(self):
        """
        Transaction wrappers aren't shown for databases that don't support
        transactional DDL.
        """
        out = io.StringIO()
        with mock.patch.object(connection.features, "can_rollback_ddl", False):
            call_command("sqlmigrate", "migrations", "0001", stdout=out)
        output = out.getvalue().lower()
        queries = [q.strip() for q in output.splitlines()]
        start_transaction_sql = connection.ops.start_transaction_sql()
        if start_transaction_sql:
            self.assertNotIn(start_transaction_sql.lower(), queries)
        self.assertNotIn(connection.ops.end_transaction_sql().lower(), queries)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_sqlmigrate_ambiguous_prefix_squashed_migrations(self):
        msg = (
            "More than one migration matches '0001' in app 'migrations'. "
            "Please be more specific."
        )
        with self.assertRaisesMessage(CommandError, msg):
            call_command("sqlmigrate", "migrations", "0001")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_sqlmigrate_squashed_migration(self):
        out = io.StringIO()
        call_command("sqlmigrate", "migrations", "0001_squashed_0002", stdout=out)
        output = out.getvalue().lower()
        self.assertIn("-- create model author", output)
        self.assertIn("-- create model book", output)
        self.assertNotIn("-- create model tribble", output)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_sqlmigrate_replaced_migration(self):
        out = io.StringIO()
        call_command("sqlmigrate", "migrations", "0001_initial", stdout=out)
        output = out.getvalue().lower()
        self.assertIn("-- create model author", output)
        self.assertIn("-- create model tribble", output)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_no_operations"}
    )
    def test_migrations_no_operations(self):
        err = io.StringIO()
        call_command("sqlmigrate", "migrations", "0001_initial", stderr=err)
        self.assertEqual(err.getvalue(), "No operations found.\n")

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.migrated_app",
            "migrations.migrations_test_apps.migrated_unapplied_app",
            "migrations.migrations_test_apps.unmigrated_app",
        ],
    )
    def test_regression_22823_unmigrated_fk_to_migrated_model(self):
        """
        Assuming you have 3 apps, `A`, `B`, and `C`, such that:

        * `A` has migrations
        * `B` has a migration we want to apply
        * `C` has no migrations, but has an FK to `A`

        When we try to migrate "B", an exception occurs because the
        "B" was not included in the ProjectState that is used to detect
        soft-applied migrations (#22823).
        """
        call_command("migrate", "migrated_unapplied_app", verbosity=0)

        # unmigrated_app.SillyModel has a foreign key to 'migrations.Tribble',
        # but that model is only defined in a migration, so the global app
        # registry never sees it and the reference is left dangling. Remove it
        # to avoid problems in subsequent tests.
        apps._pending_operations.pop(("migrations", "tribble"), None)

    @override_settings(
        INSTALLED_APPS=["migrations.migrations_test_apps.unmigrated_app_syncdb"]
    )
    def test_migrate_syncdb_deferred_sql_executed_with_schemaeditor(self):
        """
        For an app without migrations, editor.execute() is used for executing
        the syncdb deferred SQL.
        """
        stdout = io.StringIO()
        with mock.patch.object(BaseDatabaseSchemaEditor, "execute") as execute:
            call_command(
                "migrate", run_syncdb=True, verbosity=1, stdout=stdout, no_color=True
            )
            create_table_count = len(
                [call for call in execute.mock_calls if "CREATE TABLE" in str(call)]
            )
            self.assertEqual(create_table_count, 2)
            # There's at least one deferred SQL for creating the foreign key
            # index.
            self.assertGreater(len(execute.mock_calls), 2)
        stdout = stdout.getvalue()
        self.assertIn("Synchronize unmigrated apps: unmigrated_app_syncdb", stdout)
        self.assertIn("Creating tables...", stdout)
        table_name = truncate_name(
            "unmigrated_app_syncdb_classroom", connection.ops.max_name_length()
        )
        self.assertIn("Creating table %s" % table_name, stdout)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_migrate_syncdb_app_with_migrations(self):
        msg = "Can't use run_syncdb with app 'migrations' as it has migrations."
        with self.assertRaisesMessage(CommandError, msg):
            call_command("migrate", "migrations", run_syncdb=True, verbosity=0)

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.unmigrated_app_syncdb",
            "migrations.migrations_test_apps.unmigrated_app_simple",
        ]
    )
    def test_migrate_syncdb_app_label(self):
        """
        Running migrate --run-syncdb with an app_label only creates tables for
        the specified app.
        """
        stdout = io.StringIO()
        with mock.patch.object(BaseDatabaseSchemaEditor, "execute") as execute:
            call_command(
                "migrate", "unmigrated_app_syncdb", run_syncdb=True, stdout=stdout
            )
            create_table_count = len(
                [call for call in execute.mock_calls if "CREATE TABLE" in str(call)]
            )
            self.assertEqual(create_table_count, 2)
            self.assertGreater(len(execute.mock_calls), 2)
            self.assertIn(
                "Synchronize unmigrated app: unmigrated_app_syncdb", stdout.getvalue()
            )

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_migrate_record_replaced(self):
        """
        Running a single squashed migration should record all of the original
        replaced migrations as run.
        """
        recorder = MigrationRecorder(connection)
        out = io.StringIO()
        call_command("migrate", "migrations", verbosity=0)
        call_command("showmigrations", "migrations", stdout=out, no_color=True)
        self.assertEqual(
            "migrations\n [x] 0001_squashed_0002 (2 squashed migrations)\n",
            out.getvalue().lower(),
        )
        applied_migrations = recorder.applied_migrations()
        self.assertIn(("migrations", "0001_initial"), applied_migrations)
        self.assertIn(("migrations", "0002_second"), applied_migrations)
        self.assertIn(("migrations", "0001_squashed_0002"), applied_migrations)
        # Rollback changes
        call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_migrate_record_squashed(self):
        """
        Running migrate for a squashed migration should record as run
        if all of the replaced migrations have been run (#25231).
        """
        recorder = MigrationRecorder(connection)
        recorder.record_applied("migrations", "0001_initial")
        recorder.record_applied("migrations", "0002_second")
        out = io.StringIO()
        call_command("showmigrations", "migrations", stdout=out, no_color=True)
        self.assertEqual(
            "migrations\n"
            " [-] 0001_squashed_0002 (2 squashed migrations) "
            "run 'manage.py migrate' to finish recording.\n",
            out.getvalue().lower(),
        )

        out = io.StringIO()
        call_command("migrate", "migrations", verbosity=0)
        call_command("showmigrations", "migrations", stdout=out, no_color=True)
        self.assertEqual(
            "migrations\n [x] 0001_squashed_0002 (2 squashed migrations)\n",
            out.getvalue().lower(),
        )
        self.assertIn(
            ("migrations", "0001_squashed_0002"), recorder.applied_migrations()
        )
        # No changes were actually applied so there is nothing to rollback

    def test_migrate_partially_applied_squashed_migration(self):
        """
        Migrating to a squashed migration specified by name should succeed
        even if it is partially applied.
        """
        with self.temporary_migration_module(module="migrations.test_migrations"):
            recorder = MigrationRecorder(connection)
            try:
                call_command("migrate", "migrations", "0001_initial", verbosity=0)
                call_command(
                    "squashmigrations",
                    "migrations",
                    "0002",
                    interactive=False,
                    verbosity=0,
                )
                call_command(
                    "migrate",
                    "migrations",
                    "0001_squashed_0002_second",
                    verbosity=0,
                )
                applied_migrations = recorder.applied_migrations()
                self.assertIn(("migrations", "0002_second"), applied_migrations)
            finally:
                # Unmigrate everything.
                call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_migrate_backward_to_squashed_migration(self):
        try:
            call_command("migrate", "migrations", "0001_squashed_0002", verbosity=0)
            self.assertTableExists("migrations_author")
            self.assertTableExists("migrations_book")
            call_command("migrate", "migrations", "0001_initial", verbosity=0)
            self.assertTableExists("migrations_author")
            self.assertTableNotExists("migrations_book")
        finally:
            # Unmigrate everything.
            call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_migrate_inconsistent_history(self):
        """
        Running migrate with some migrations applied before their dependencies
        should not be allowed.
        """
        recorder = MigrationRecorder(connection)
        recorder.record_applied("migrations", "0002_second")
        msg = (
            "Migration migrations.0002_second is applied before its dependency "
            "migrations.0001_initial"
        )
        with self.assertRaisesMessage(InconsistentMigrationHistory, msg):
            call_command("migrate")
        applied_migrations = recorder.applied_migrations()
        self.assertNotIn(("migrations", "0001_initial"), applied_migrations)

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.migrated_unapplied_app",
            "migrations.migrations_test_apps.migrated_app",
        ]
    )
    def test_migrate_not_reflected_changes(self):
        class NewModel1(models.Model):
            class Meta:
                app_label = "migrated_app"

        class NewModel2(models.Model):
            class Meta:
                app_label = "migrated_unapplied_app"

        out = io.StringIO()
        try:
            call_command("migrate", verbosity=0)
            call_command("migrate", stdout=out, no_color=True)
            self.assertEqual(
                "operations to perform:\n"
                "  apply all migrations: migrated_app, migrated_unapplied_app\n"
                "running migrations:\n"
                "  no migrations to apply.\n"
                "  your models in app(s): 'migrated_app', "
                "'migrated_unapplied_app' have changes that are not yet "
                "reflected in a migration, and so won't be applied.\n"
                "  run 'manage.py makemigrations' to make new migrations, and "
                "then re-run 'manage.py migrate' to apply them.\n",
                out.getvalue().lower(),
            )
        finally:
            # Unmigrate everything.
            call_command("migrate", "migrated_app", "zero", verbosity=0)
            call_command("migrate", "migrated_unapplied_app", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations_squashed_no_replaces",
        }
    )
    def test_migrate_prune(self):
        """
        With prune=True, references to migration files deleted from the
        migrations module (such as after being squashed) are removed from the
        django_migrations table.
        """
        recorder = MigrationRecorder(connection)
        recorder.record_applied("migrations", "0001_initial")
        recorder.record_applied("migrations", "0002_second")
        recorder.record_applied("migrations", "0001_squashed_0002")
        out = io.StringIO()
        try:
            call_command("migrate", "migrations", prune=True, stdout=out, no_color=True)
            self.assertEqual(
                out.getvalue(),
                "Pruning migrations:\n"
                "  Pruning migrations.0001_initial OK\n"
                "  Pruning migrations.0002_second OK\n",
            )
            applied_migrations = [
                migration
                for migration in recorder.applied_migrations()
                if migration[0] == "migrations"
            ]
            self.assertEqual(applied_migrations, [("migrations", "0001_squashed_0002")])
        finally:
            recorder.record_unapplied("migrations", "0001_initial")
            recorder.record_unapplied("migrations", "0001_second")
            recorder.record_unapplied("migrations", "0001_squashed_0002")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_prune_deleted_squashed_migrations_in_replaces(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_squashed"
        ) as migration_dir:
            try:
                call_command("migrate", "migrations", verbosity=0)
                # Delete the replaced migrations.
                os.remove(os.path.join(migration_dir, "0001_initial.py"))
                os.remove(os.path.join(migration_dir, "0002_second.py"))
                # --prune cannot be used before removing the "replaces"
                # attribute.
                call_command(
                    "migrate",
                    "migrations",
                    prune=True,
                    stdout=out,
                    no_color=True,
                )
                self.assertEqual(
                    out.getvalue(),
                    "Pruning migrations:\n"
                    "  Cannot use --prune because the following squashed "
                    "migrations have their 'replaces' attributes and may not "
                    "be recorded as applied:\n"
                    "    migrations.0001_squashed_0002\n"
                    "  Re-run 'manage.py migrate' if they are not marked as "
                    "applied, and remove 'replaces' attributes in their "
                    "Migration classes.\n",
                )
            finally:
                # Unmigrate everything.
                call_command("migrate", "migrations", "zero", verbosity=0)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_prune_no_migrations_to_prune(self):
        out = io.StringIO()
        call_command("migrate", "migrations", prune=True, stdout=out, no_color=True)
        self.assertEqual(
            out.getvalue(),
            "Pruning migrations:\n  No migrations to prune.\n",
        )
        out = io.StringIO()
        call_command(
            "migrate",
            "migrations",
            prune=True,
            stdout=out,
            no_color=True,
            verbosity=0,
        )
        self.assertEqual(out.getvalue(), "")

    def test_prune_no_app_label(self):
        msg = "Migrations can be pruned only when an app is specified."
        with self.assertRaisesMessage(CommandError, msg):
            call_command("migrate", prune=True)


class MakeMigrationsTests(MigrationTestBase):
    """
    Tests running the makemigrations command.
    """

    def setUp(self):
        super().setUp()
        self._old_models = apps.app_configs["migrations"].models.copy()

    def tearDown(self):
        apps.app_configs["migrations"].models = self._old_models
        apps.all_models["migrations"] = self._old_models
        apps.clear_cache()
        super().tearDown()

    def test_files_content(self):
        self.assertTableNotExists("migrations_unicodemodel")
        apps.register_model("migrations", UnicodeModel)
        with self.temporary_migration_module() as migration_dir:
            call_command("makemigrations", "migrations", verbosity=0)

            # Check for empty __init__.py file in migrations folder
            init_file = os.path.join(migration_dir, "__init__.py")
            self.assertTrue(os.path.exists(init_file))

            with open(init_file) as fp:
                content = fp.read()
            self.assertEqual(content, "")

            # Check for existing 0001_initial.py file in migration folder
            initial_file = os.path.join(migration_dir, "0001_initial.py")
            self.assertTrue(os.path.exists(initial_file))

            with open(initial_file, encoding="utf-8") as fp:
                content = fp.read()
                self.assertIn("migrations.CreateModel", content)
                self.assertIn("initial = True", content)

                self.assertIn("úñí©óðé µóðéø", content)  # Meta.verbose_name
                self.assertIn("úñí©óðé µóðéøß", content)  # Meta.verbose_name_plural
                self.assertIn("ÚÑÍ¢ÓÐÉ", content)  # title.verbose_name
                self.assertIn("“Ðjáñgó”", content)  # title.default

    def test_makemigrations_order(self):
        """
        makemigrations should recognize number-only migrations (0001.py).
        """
        module = "migrations.test_migrations_order"
        with self.temporary_migration_module(module=module) as migration_dir:
            if hasattr(importlib, "invalidate_caches"):
                # importlib caches os.listdir() on some platforms like macOS
                # (#23850).
                importlib.invalidate_caches()
            call_command(
                "makemigrations", "migrations", "--empty", "-n", "a", "-v", "0"
            )
            self.assertTrue(os.path.exists(os.path.join(migration_dir, "0002_a.py")))

    def test_makemigrations_empty_connections(self):
        empty_connections = ConnectionHandler({"default": {}})
        with mock.patch(
            "django.core.management.commands.makemigrations.connections",
            new=empty_connections,
        ):
            # with no apps
            out = io.StringIO()
            call_command("makemigrations", stdout=out)
            self.assertIn("No changes detected", out.getvalue())
            # with an app
            with self.temporary_migration_module() as migration_dir:
                call_command("makemigrations", "migrations", verbosity=0)
                init_file = os.path.join(migration_dir, "__init__.py")
                self.assertTrue(os.path.exists(init_file))

    @override_settings(INSTALLED_APPS=["migrations", "migrations2"])
    def test_makemigrations_consistency_checks_respect_routers(self):
        """
        The history consistency checks in makemigrations respect
        settings.DATABASE_ROUTERS.
        """

        def patched_has_table(migration_recorder):
            if migration_recorder.connection is connections["other"]:
                raise Exception("Other connection")
            else:
                return mock.DEFAULT

        self.assertTableNotExists("migrations_unicodemodel")
        apps.register_model("migrations", UnicodeModel)
        with mock.patch.object(
            MigrationRecorder, "has_table", autospec=True, side_effect=patched_has_table
        ) as has_table:
            with self.temporary_migration_module() as migration_dir:
                call_command("makemigrations", "migrations", verbosity=0)
                initial_file = os.path.join(migration_dir, "0001_initial.py")
                self.assertTrue(os.path.exists(initial_file))
                self.assertEqual(has_table.call_count, 1)  # 'default' is checked

                # Router says not to migrate 'other' so consistency shouldn't
                # be checked.
                with self.settings(DATABASE_ROUTERS=["migrations.routers.TestRouter"]):
                    call_command("makemigrations", "migrations", verbosity=0)
                self.assertEqual(has_table.call_count, 2)  # 'default' again

                # With a router that doesn't prohibit migrating 'other',
                # consistency is checked.
                with self.settings(
                    DATABASE_ROUTERS=["migrations.routers.DefaultOtherRouter"]
                ):
                    with self.assertRaisesMessage(Exception, "Other connection"):
                        call_command("makemigrations", "migrations", verbosity=0)
                self.assertEqual(has_table.call_count, 4)  # 'default' and 'other'

                # With a router that doesn't allow migrating on any database,
                # no consistency checks are made.
                with self.settings(DATABASE_ROUTERS=["migrations.routers.TestRouter"]):
                    with mock.patch.object(
                        TestRouter, "allow_migrate", return_value=False
                    ) as allow_migrate:
                        call_command("makemigrations", "migrations", verbosity=0)
                allow_migrate.assert_any_call(
                    "other", "migrations", model_name="UnicodeModel"
                )
                # allow_migrate() is called with the correct arguments.
                self.assertGreater(len(allow_migrate.mock_calls), 0)
                called_aliases = set()
                for mock_call in allow_migrate.mock_calls:
                    _, call_args, call_kwargs = mock_call
                    connection_alias, app_name = call_args
                    called_aliases.add(connection_alias)
                    # Raises an error if invalid app_name/model_name occurs.
                    apps.get_app_config(app_name).get_model(call_kwargs["model_name"])
                self.assertEqual(called_aliases, set(connections))
                self.assertEqual(has_table.call_count, 4)

    def test_failing_migration(self):
        # If a migration fails to serialize, it shouldn't generate an empty file. #21280
        apps.register_model("migrations", UnserializableModel)

        with self.temporary_migration_module() as migration_dir:
            with self.assertRaisesMessage(ValueError, "Cannot serialize"):
                call_command("makemigrations", "migrations", verbosity=0)

            initial_file = os.path.join(migration_dir, "0001_initial.py")
            self.assertFalse(os.path.exists(initial_file))

    def test_makemigrations_conflict_exit(self):
        """
        makemigrations exits if it detects a conflict.
        """
        with self.temporary_migration_module(
            module="migrations.test_migrations_conflict"
        ):
            with self.assertRaises(CommandError) as context:
                call_command("makemigrations")
        self.assertEqual(
            str(context.exception),
            "Conflicting migrations detected; multiple leaf nodes in the "
            "migration graph: (0002_conflicting_second, 0002_second in "
            "migrations).\n"
            "To fix them run 'python manage.py makemigrations --merge'",
        )

    def test_makemigrations_merge_no_conflict(self):
        """
        makemigrations exits if in merge mode with no conflicts.
        """
        out = io.StringIO()
        with self.temporary_migration_module(module="migrations.test_migrations"):
            call_command("makemigrations", merge=True, stdout=out)
        self.assertIn("No conflicts detected to merge.", out.getvalue())

    def test_makemigrations_empty_no_app_specified(self):
        """
        makemigrations exits if no app is specified with 'empty' mode.
        """
        msg = "You must supply at least one app label when using --empty."
        with self.assertRaisesMessage(CommandError, msg):
            call_command("makemigrations", empty=True)

    def test_makemigrations_empty_migration(self):
        """
        makemigrations properly constructs an empty migration.
        """
        with self.temporary_migration_module() as migration_dir:
            call_command("makemigrations", "migrations", empty=True, verbosity=0)

            # Check for existing 0001_initial.py file in migration folder
            initial_file = os.path.join(migration_dir, "0001_initial.py")
            self.assertTrue(os.path.exists(initial_file))

            with open(initial_file, encoding="utf-8") as fp:
                content = fp.read()

                # Remove all whitespace to check for empty dependencies and operations
                content = content.replace(" ", "")
                self.assertIn(
                    "dependencies=[]" if HAS_BLACK else "dependencies=[\n]", content
                )
                self.assertIn(
                    "operations=[]" if HAS_BLACK else "operations=[\n]", content
                )

    @override_settings(MIGRATION_MODULES={"migrations": None})
    def test_makemigrations_disabled_migrations_for_app(self):
        """
        makemigrations raises a nice error when migrations are disabled for an
        app.
        """
        msg = (
            "Django can't create migrations for app 'migrations' because migrations "
            "have been disabled via the MIGRATION_MODULES setting."
        )
        with self.assertRaisesMessage(ValueError, msg):
            call_command("makemigrations", "migrations", empty=True, verbosity=0)

    def test_makemigrations_no_changes_no_apps(self):
        """
        makemigrations exits when there are no changes and no apps are specified.
        """
        out = io.StringIO()
        call_command("makemigrations", stdout=out)
        self.assertIn("No changes detected", out.getvalue())

    def test_makemigrations_no_changes(self):
        """
        makemigrations exits when there are no changes to an app.
        """
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_changes"
        ):
            call_command("makemigrations", "migrations", stdout=out)
        self.assertIn("No changes detected in app 'migrations'", out.getvalue())

    def test_makemigrations_no_apps_initial(self):
        """
        makemigrations should detect initial is needed on empty migration
        modules if no app provided.
        """
        out = io.StringIO()
        with self.temporary_migration_module(module="migrations.test_migrations_empty"):
            call_command("makemigrations", stdout=out)
        self.assertIn("0001_initial.py", out.getvalue())

    def test_makemigrations_no_init(self):
        """Migration directories without an __init__.py file are allowed."""
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_init"
        ):
            call_command("makemigrations", stdout=out)
        self.assertIn("0001_initial.py", out.getvalue())

    def test_makemigrations_migrations_announce(self):
        """
        makemigrations announces the migration at the default verbosity level.
        """
        out = io.StringIO()
        with self.temporary_migration_module():
            call_command("makemigrations", "migrations", stdout=out)
        self.assertIn("Migrations for 'migrations'", out.getvalue())

    def test_makemigrations_no_common_ancestor(self):
        """
        makemigrations fails to merge migrations with no common ancestor.
        """
        with self.assertRaises(ValueError) as context:
            with self.temporary_migration_module(
                module="migrations.test_migrations_no_ancestor"
            ):
                call_command("makemigrations", "migrations", merge=True)
        exception_message = str(context.exception)
        self.assertIn("Could not find common ancestor of", exception_message)
        self.assertIn("0002_second", exception_message)
        self.assertIn("0002_conflicting_second", exception_message)

    def test_makemigrations_interactive_reject(self):
        """
        makemigrations enters and exits interactive mode properly.
        """
        # Monkeypatch interactive questioner to auto reject
        with mock.patch("builtins.input", mock.Mock(return_value="N")):
            with self.temporary_migration_module(
                module="migrations.test_migrations_conflict"
            ) as migration_dir:
                with captured_stdout():
                    call_command(
                        "makemigrations",
                        "migrations",
                        name="merge",
                        merge=True,
                        interactive=True,
                        verbosity=0,
                    )
                merge_file = os.path.join(migration_dir, "0003_merge.py")
                self.assertFalse(os.path.exists(merge_file))

    def test_makemigrations_interactive_accept(self):
        """
        makemigrations enters interactive mode and merges properly.
        """
        # Monkeypatch interactive questioner to auto accept
        with mock.patch("builtins.input", mock.Mock(return_value="y")):
            out = io.StringIO()
            with self.temporary_migration_module(
                module="migrations.test_migrations_conflict"
            ) as migration_dir:
                call_command(
                    "makemigrations",
                    "migrations",
                    name="merge",
                    merge=True,
                    interactive=True,
                    stdout=out,
                )
                merge_file = os.path.join(migration_dir, "0003_merge.py")
                self.assertTrue(os.path.exists(merge_file))
            self.assertIn("Created new merge migration", out.getvalue())

    def test_makemigrations_default_merge_name(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_conflict"
        ) as migration_dir:
            call_command(
                "makemigrations",
                "migrations",
                merge=True,
                interactive=False,
                stdout=out,
            )
            merge_file = os.path.join(
                migration_dir,
                "0003_merge_0002_conflicting_second_0002_second.py",
            )
            self.assertIs(os.path.exists(merge_file), True)
            with open(merge_file, encoding="utf-8") as fp:
                content = fp.read()
            if HAS_BLACK:
                target_str = '("migrations", "0002_conflicting_second")'
            else:
                target_str = "('migrations', '0002_conflicting_second')"
            self.assertIn(target_str, content)
        self.assertIn("Created new merge migration %s" % merge_file, out.getvalue())

    @mock.patch("django.db.migrations.utils.datetime")
    def test_makemigrations_auto_merge_name(self, mock_datetime):
        mock_datetime.datetime.now.return_value = datetime.datetime(2016, 1, 2, 3, 4)
        with mock.patch("builtins.input", mock.Mock(return_value="y")):
            out = io.StringIO()
            with self.temporary_migration_module(
                module="migrations.test_migrations_conflict_long_name"
            ) as migration_dir:
                call_command(
                    "makemigrations",
                    "migrations",
                    merge=True,
                    interactive=True,
                    stdout=out,
                )
                merge_file = os.path.join(migration_dir, "0003_merge_20160102_0304.py")
                self.assertTrue(os.path.exists(merge_file))
            self.assertIn("Created new merge migration", out.getvalue())

    def test_makemigrations_non_interactive_not_null_addition(self):
        """
        Non-interactive makemigrations fails when a default is missing on a
        new not-null field.
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)
            silly_int = models.IntegerField()

            class Meta:
                app_label = "migrations"

        with self.assertRaises(SystemExit):
            with self.temporary_migration_module(
                module="migrations.test_migrations_no_default"
            ):
                with captured_stdout() as out:
                    call_command("makemigrations", "migrations", interactive=False)
        self.assertIn(
            "Field 'silly_int' on model 'sillymodel' not migrated: it is "
            "impossible to add a non-nullable field without specifying a "
            "default.",
            out.getvalue(),
        )

    def test_makemigrations_interactive_not_null_addition(self):
        """
        makemigrations messages when adding a NOT NULL field in interactive
        mode.
        """

        class Author(models.Model):
            silly_field = models.BooleanField(null=False)

            class Meta:
                app_label = "migrations"

        input_msg = (
            "It is impossible to add a non-nullable field 'silly_field' to "
            "author without specifying a default. This is because the "
            "database needs something to populate existing rows.\n"
            "Please select a fix:\n"
            " 1) Provide a one-off default now (will be set on all existing "
            "rows with a null value for this column)\n"
            " 2) Quit and manually define a default value in models.py."
        )
        with self.temporary_migration_module(module="migrations.test_migrations"):
            # 2 - quit.
            with mock.patch("builtins.input", return_value="2"):
                with captured_stdout() as out, self.assertRaises(SystemExit):
                    call_command("makemigrations", "migrations", interactive=True)
            self.assertIn(input_msg, out.getvalue())
            # 1 - provide a default.
            with mock.patch("builtins.input", return_value="1"):
                with captured_stdout() as out:
                    call_command("makemigrations", "migrations", interactive=True)
            output = out.getvalue()
            self.assertIn(input_msg, output)
            self.assertIn("Please enter the default value as valid Python.", output)
            self.assertIn(
                "The datetime and django.utils.timezone modules are "
                "available, so it is possible to provide e.g. timezone.now as "
                "a value",
                output,
            )
            self.assertIn("Type 'exit' to exit this prompt", output)

    def test_makemigrations_non_interactive_not_null_alteration(self):
        """
        Non-interactive makemigrations fails when a default is missing on a
        field changed to not-null.
        """

        class Author(models.Model):
            name = models.CharField(max_length=255)
            slug = models.SlugField()
            age = models.IntegerField(default=0)

            class Meta:
                app_label = "migrations"

        with self.temporary_migration_module(module="migrations.test_migrations"):
            with captured_stdout() as out:
                call_command("makemigrations", "migrations", interactive=False)
        self.assertIn("Alter field slug on author", out.getvalue())
        self.assertIn(
            "Field 'slug' on model 'author' given a default of NOT PROVIDED "
            "and must be corrected.",
            out.getvalue(),
        )

    def test_makemigrations_interactive_not_null_alteration(self):
        """
        makemigrations messages when changing a NULL field to NOT NULL in
        interactive mode.
        """

        class Author(models.Model):
            slug = models.SlugField(null=False)

            class Meta:
                app_label = "migrations"

        input_msg = (
            "It is impossible to change a nullable field 'slug' on author to "
            "non-nullable without providing a default. This is because the "
            "database needs something to populate existing rows.\n"
            "Please select a fix:\n"
            " 1) Provide a one-off default now (will be set on all existing "
            "rows with a null value for this column)\n"
            " 2) Ignore for now. Existing rows that contain NULL values will "
            "have to be handled manually, for example with a RunPython or "
            "RunSQL operation.\n"
            " 3) Quit and manually define a default value in models.py."
        )
        with self.temporary_migration_module(module="migrations.test_migrations"):
            # No message appears if --dry-run.
            with captured_stdout() as out:
                call_command(
                    "makemigrations",
                    "migrations",
                    interactive=True,
                    dry_run=True,
                )
            self.assertNotIn(input_msg, out.getvalue())
            # 3 - quit.
            with mock.patch("builtins.input", return_value="3"):
                with captured_stdout() as out, self.assertRaises(SystemExit):
                    call_command("makemigrations", "migrations", interactive=True)
            self.assertIn(input_msg, out.getvalue())
            # 1 - provide a default.
            with mock.patch("builtins.input", return_value="1"):
                with captured_stdout() as out:
                    call_command("makemigrations", "migrations", interactive=True)
            output = out.getvalue()
            self.assertIn(input_msg, output)
            self.assertIn("Please enter the default value as valid Python.", output)
            self.assertIn(
                "The datetime and django.utils.timezone modules are "
                "available, so it is possible to provide e.g. timezone.now as "
                "a value",
                output,
            )
            self.assertIn("Type 'exit' to exit this prompt", output)

    def test_makemigrations_non_interactive_no_model_rename(self):
        """
        makemigrations adds and removes a possible model rename in
        non-interactive mode.
        """

        class RenamedModel(models.Model):
            silly_field = models.BooleanField(default=False)

            class Meta:
                app_label = "migrations"

        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_default"
        ):
            call_command("makemigrations", "migrations", interactive=False, stdout=out)
        self.assertIn("Delete model SillyModel", out.getvalue())
        self.assertIn("Create model RenamedModel", out.getvalue())

    def test_makemigrations_non_interactive_no_field_rename(self):
        """
        makemigrations adds and removes a possible field rename in
        non-interactive mode.
        """

        class SillyModel(models.Model):
            silly_rename = models.BooleanField(default=False)

            class Meta:
                app_label = "migrations"

        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_default"
        ):
            call_command("makemigrations", "migrations", interactive=False, stdout=out)
        self.assertIn("Remove field silly_field from sillymodel", out.getvalue())
        self.assertIn("Add field silly_rename to sillymodel", out.getvalue())

    @mock.patch("builtins.input", return_value="Y")
    def test_makemigrations_model_rename_interactive(self, mock_input):
        class RenamedModel(models.Model):
            silly_field = models.BooleanField(default=False)

            class Meta:
                app_label = "migrations"

        with self.temporary_migration_module(
            module="migrations.test_migrations_no_default",
        ):
            with captured_stdout() as out:
                call_command("makemigrations", "migrations", interactive=True)
        self.assertIn("Rename model SillyModel to RenamedModel", out.getvalue())

    @mock.patch("builtins.input", return_value="Y")
    def test_makemigrations_field_rename_interactive(self, mock_input):
        class SillyModel(models.Model):
            silly_rename = models.BooleanField(default=False)

            class Meta:
                app_label = "migrations"

        with self.temporary_migration_module(
            module="migrations.test_migrations_no_default",
        ):
            with captured_stdout() as out:
                call_command("makemigrations", "migrations", interactive=True)
        self.assertIn(
            "Rename field silly_field on sillymodel to silly_rename",
            out.getvalue(),
        )

    def test_makemigrations_handle_merge(self):
        """
        makemigrations properly merges the conflicting migrations with --noinput.
        """
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_conflict"
        ) as migration_dir:
            call_command(
                "makemigrations",
                "migrations",
                name="merge",
                merge=True,
                interactive=False,
                stdout=out,
            )
            merge_file = os.path.join(migration_dir, "0003_merge.py")
            self.assertTrue(os.path.exists(merge_file))
        output = out.getvalue()
        self.assertIn("Merging migrations", output)
        self.assertIn("Branch 0002_second", output)
        self.assertIn("Branch 0002_conflicting_second", output)
        self.assertIn("Created new merge migration", output)

    def test_makemigration_merge_dry_run(self):
        """
        makemigrations respects --dry-run option when fixing migration
        conflicts (#24427).
        """
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_conflict"
        ) as migration_dir:
            call_command(
                "makemigrations",
                "migrations",
                name="merge",
                dry_run=True,
                merge=True,
                interactive=False,
                stdout=out,
            )
            merge_file = os.path.join(migration_dir, "0003_merge.py")
            self.assertFalse(os.path.exists(merge_file))
        output = out.getvalue()
        self.assertIn("Merging migrations", output)
        self.assertIn("Branch 0002_second", output)
        self.assertIn("Branch 0002_conflicting_second", output)
        self.assertNotIn("Created new merge migration", output)

    def test_makemigration_merge_dry_run_verbosity_3(self):
        """
        `makemigrations --merge --dry-run` writes the merge migration file to
        stdout with `verbosity == 3` (#24427).
        """
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_conflict"
        ) as migration_dir:
            call_command(
                "makemigrations",
                "migrations",
                name="merge",
                dry_run=True,
                merge=True,
                interactive=False,
                stdout=out,
                verbosity=3,
            )
            merge_file = os.path.join(migration_dir, "0003_merge.py")
            self.assertFalse(os.path.exists(merge_file))
        output = out.getvalue()
        self.assertIn("Merging migrations", output)
        self.assertIn("Branch 0002_second", output)
        self.assertIn("Branch 0002_conflicting_second", output)
        self.assertNotIn("Created new merge migration", output)

        # Additional output caused by verbosity 3
        # The complete merge migration file that would be written
        self.assertIn("class Migration(migrations.Migration):", output)
        self.assertIn("dependencies = [", output)
        self.assertIn("('migrations', '0002_second')", output)
        self.assertIn("('migrations', '0002_conflicting_second')", output)
        self.assertIn("operations = [", output)
        self.assertIn("]", output)

    def test_makemigrations_dry_run(self):
        """
        `makemigrations --dry-run` should not ask for defaults.
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)
            silly_date = models.DateField()  # Added field without a default
            silly_auto_now = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "migrations"

        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_default"
        ):
            call_command("makemigrations", "migrations", dry_run=True, stdout=out)
        # Output the expected changes directly, without asking for defaults
        self.assertIn("Add field silly_date to sillymodel", out.getvalue())

    def test_makemigrations_dry_run_verbosity_3(self):
        """
        Allow `makemigrations --dry-run` to output the migrations file to
        stdout (with verbosity == 3).
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)
            silly_char = models.CharField(default="")

            class Meta:
                app_label = "migrations"

        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_default"
        ):
            call_command(
                "makemigrations", "migrations", dry_run=True, stdout=out, verbosity=3
            )

        # Normal --dry-run output
        self.assertIn("- Add field silly_char to sillymodel", out.getvalue())

        # Additional output caused by verbosity 3
        # The complete migrations file that would be written
        self.assertIn("class Migration(migrations.Migration):", out.getvalue())
        self.assertIn("dependencies = [", out.getvalue())
        self.assertIn("('migrations', '0001_initial'),", out.getvalue())
        self.assertIn("migrations.AddField(", out.getvalue())
        self.assertIn("model_name='sillymodel',", out.getvalue())
        self.assertIn("name='silly_char',", out.getvalue())

    def test_makemigrations_scriptable(self):
        """
        With scriptable=True, log output is diverted to stderr, and only the
        paths of generated migration files are written to stdout.
        """
        out = io.StringIO()
        err = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.migrations.test_migrations",
        ) as migration_dir:
            call_command(
                "makemigrations",
                "migrations",
                scriptable=True,
                stdout=out,
                stderr=err,
            )
        initial_file = os.path.join(migration_dir, "0001_initial.py")
        self.assertEqual(out.getvalue(), f"{initial_file}\n")
        self.assertIn("    - Create model ModelWithCustomBase\n", err.getvalue())

    @mock.patch("builtins.input", return_value="Y")
    def test_makemigrations_scriptable_merge(self, mock_input):
        out = io.StringIO()
        err = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_conflict",
        ) as migration_dir:
            call_command(
                "makemigrations",
                "migrations",
                merge=True,
                name="merge",
                scriptable=True,
                stdout=out,
                stderr=err,
            )
        merge_file = os.path.join(migration_dir, "0003_merge.py")
        self.assertEqual(out.getvalue(), f"{merge_file}\n")
        self.assertIn(f"Created new merge migration {merge_file}", err.getvalue())

    def test_makemigrations_migrations_modules_path_not_exist(self):
        """
        makemigrations creates migrations when specifying a custom location
        for migration files using MIGRATION_MODULES if the custom path
        doesn't already exist.
        """

        class SillyModel(models.Model):
            silly_field = models.BooleanField(default=False)

            class Meta:
                app_label = "migrations"

        out = io.StringIO()
        migration_module = "migrations.test_migrations_path_doesnt_exist.foo.bar"
        with self.temporary_migration_module(module=migration_module) as migration_dir:
            call_command("makemigrations", "migrations", stdout=out)

            # Migrations file is actually created in the expected path.
            initial_file = os.path.join(migration_dir, "0001_initial.py")
            self.assertTrue(os.path.exists(initial_file))

        # Command output indicates the migration is created.
        self.assertIn(" - Create model SillyModel", out.getvalue())

    @override_settings(MIGRATION_MODULES={"migrations": "some.nonexistent.path"})
    def test_makemigrations_migrations_modules_nonexistent_toplevel_package(self):
        msg = (
            "Could not locate an appropriate location to create migrations "
            "package some.nonexistent.path. Make sure the toplevel package "
            "exists and can be imported."
        )
        with self.assertRaisesMessage(ValueError, msg):
            call_command("makemigrations", "migrations", empty=True, verbosity=0)

    def test_makemigrations_interactive_by_default(self):
        """
        The user is prompted to merge by default if there are conflicts and
        merge is True. Answer negative to differentiate it from behavior when
        --noinput is specified.
        """
        # Monkeypatch interactive questioner to auto reject
        out = io.StringIO()
        with mock.patch("builtins.input", mock.Mock(return_value="N")):
            with self.temporary_migration_module(
                module="migrations.test_migrations_conflict"
            ) as migration_dir:
                call_command(
                    "makemigrations", "migrations", name="merge", merge=True, stdout=out
                )
                merge_file = os.path.join(migration_dir, "0003_merge.py")
                # This will fail if interactive is False by default
                self.assertFalse(os.path.exists(merge_file))
            self.assertNotIn("Created new merge migration", out.getvalue())

    @override_settings(
        INSTALLED_APPS=[
            "migrations",
            "migrations.migrations_test_apps.unspecified_app_with_conflict",
        ]
    )
    def test_makemigrations_unspecified_app_with_conflict_no_merge(self):
        """
        makemigrations does not raise a CommandError when an unspecified app
        has conflicting migrations.
        """
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_changes"
        ):
            call_command("makemigrations", "migrations", merge=False, verbosity=0)

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.migrated_app",
            "migrations.migrations_test_apps.unspecified_app_with_conflict",
        ]
    )
    def test_makemigrations_unspecified_app_with_conflict_merge(self):
        """
        makemigrations does not create a merge for an unspecified app even if
        it has conflicting migrations.
        """
        # Monkeypatch interactive questioner to auto accept
        with mock.patch("builtins.input", mock.Mock(return_value="y")):
            out = io.StringIO()
            with self.temporary_migration_module(
                app_label="migrated_app"
            ) as migration_dir:
                call_command(
                    "makemigrations",
                    "migrated_app",
                    name="merge",
                    merge=True,
                    interactive=True,
                    stdout=out,
                )
                merge_file = os.path.join(migration_dir, "0003_merge.py")
                self.assertFalse(os.path.exists(merge_file))
            self.assertIn("No conflicts detected to merge.", out.getvalue())

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.migrated_app",
            "migrations.migrations_test_apps.conflicting_app_with_dependencies",
        ]
    )
    def test_makemigrations_merge_dont_output_dependency_operations(self):
        """
        makemigrations --merge does not output any operations from apps that
        don't belong to a given app.
        """
        # Monkeypatch interactive questioner to auto accept
        with mock.patch("builtins.input", mock.Mock(return_value="N")):
            out = io.StringIO()
            with mock.patch(
                "django.core.management.color.supports_color", lambda *args: False
            ):
                call_command(
                    "makemigrations",
                    "conflicting_app_with_dependencies",
                    merge=True,
                    interactive=True,
                    stdout=out,
                )
            self.assertEqual(
                out.getvalue().lower(),
                "merging conflicting_app_with_dependencies\n"
                "  branch 0002_conflicting_second\n"
                "    - create model something\n"
                "  branch 0002_second\n"
                "    - delete model tribble\n"
                "    - remove field silly_field from author\n"
                "    - add field rating to author\n"
                "    - create model book\n"
                "\n"
                "merging will only work if the operations printed above do not "
                "conflict\n"
                "with each other (working on different fields or models)\n"
                "should these migration branches be merged? [y/n] ",
            )

    def test_makemigrations_with_custom_name(self):
        """
        makemigrations --name generate a custom migration name.
        """
        with self.temporary_migration_module() as migration_dir:

            def cmd(migration_count, migration_name, *args):
                call_command(
                    "makemigrations",
                    "migrations",
                    "--verbosity",
                    "0",
                    "--name",
                    migration_name,
                    *args,
                )
                migration_file = os.path.join(
                    migration_dir, "%s_%s.py" % (migration_count, migration_name)
                )
                # Check for existing migration file in migration folder
                self.assertTrue(os.path.exists(migration_file))
                with open(migration_file, encoding="utf-8") as fp:
                    content = fp.read()
                    content = content.replace(" ", "")
                return content

            # generate an initial migration
            migration_name_0001 = "my_initial_migration"
            content = cmd("0001", migration_name_0001)
            self.assertIn(
                "dependencies=[]" if HAS_BLACK else "dependencies=[\n]", content
            )

            # importlib caches os.listdir() on some platforms like macOS
            # (#23850).
            if hasattr(importlib, "invalidate_caches"):
                importlib.invalidate_caches()

            # generate an empty migration
            migration_name_0002 = "my_custom_migration"
            content = cmd("0002", migration_name_0002, "--empty")
            if HAS_BLACK:
                template_str = 'dependencies=[\n("migrations","0001_%s"),\n]'
            else:
                template_str = "dependencies=[\n('migrations','0001_%s'),\n]"
            self.assertIn(
                template_str % migration_name_0001,
                content,
            )
            self.assertIn("operations=[]" if HAS_BLACK else "operations=[\n]", content)

    def test_makemigrations_with_invalid_custom_name(self):
        msg = "The migration name must be a valid Python identifier."
        with self.assertRaisesMessage(CommandError, msg):
            call_command(
                "makemigrations", "migrations", "--name", "invalid name", "--empty"
            )

    def test_makemigrations_check(self):
        """
        makemigrations --check should exit with a non-zero status when
        there are changes to an app requiring migrations.
        """
        with self.temporary_migration_module():
            with self.assertRaises(SystemExit):
                call_command("makemigrations", "--check", "migrations", verbosity=0)

        with self.temporary_migration_module(
            module="migrations.test_migrations_no_changes"
        ):
            call_command("makemigrations", "--check", "migrations", verbosity=0)

    def test_makemigrations_migration_path_output(self):
        """
        makemigrations should print the relative paths to the migrations unless
        they are outside of the current tree, in which case the absolute path
        should be shown.
        """
        out = io.StringIO()
        apps.register_model("migrations", UnicodeModel)
        with self.temporary_migration_module() as migration_dir:
            call_command("makemigrations", "migrations", stdout=out)
            self.assertIn(
                os.path.join(migration_dir, "0001_initial.py"), out.getvalue()
            )

    def test_makemigrations_migration_path_output_valueerror(self):
        """
        makemigrations prints the absolute path if os.path.relpath() raises a
        ValueError when it's impossible to obtain a relative path, e.g. on
        Windows if Django is installed on a different drive than where the
        migration files are created.
        """
        out = io.StringIO()
        with self.temporary_migration_module() as migration_dir:
            with mock.patch("os.path.relpath", side_effect=ValueError):
                call_command("makemigrations", "migrations", stdout=out)
        self.assertIn(os.path.join(migration_dir, "0001_initial.py"), out.getvalue())

    def test_makemigrations_inconsistent_history(self):
        """
        makemigrations should raise InconsistentMigrationHistory exception if
        there are some migrations applied before their dependencies.
        """
        recorder = MigrationRecorder(connection)
        recorder.record_applied("migrations", "0002_second")
        msg = (
            "Migration migrations.0002_second is applied before its dependency "
            "migrations.0001_initial"
        )
        with self.temporary_migration_module(module="migrations.test_migrations"):
            with self.assertRaisesMessage(InconsistentMigrationHistory, msg):
                call_command("makemigrations")

    def test_makemigrations_inconsistent_history_db_failure(self):
        msg = (
            "Got an error checking a consistent migration history performed "
            "for database connection 'default': could not connect to server"
        )
        with mock.patch(
            "django.db.migrations.loader.MigrationLoader.check_consistent_history",
            side_effect=OperationalError("could not connect to server"),
        ):
            with self.temporary_migration_module():
                with self.assertWarns(RuntimeWarning) as cm:
                    call_command("makemigrations", verbosity=0)
                self.assertEqual(str(cm.warning), msg)

    @mock.patch("builtins.input", return_value="1")
    @mock.patch(
        "django.db.migrations.questioner.sys.stdin",
        mock.MagicMock(encoding=sys.getdefaultencoding()),
    )
    def test_makemigrations_auto_now_add_interactive(self, *args):
        """
        makemigrations prompts the user when adding auto_now_add to an existing
        model.
        """

        class Entry(models.Model):
            title = models.CharField(max_length=255)
            creation_date = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "migrations"

        input_msg = (
            "It is impossible to add the field 'creation_date' with "
            "'auto_now_add=True' to entry without providing a default. This "
            "is because the database needs something to populate existing "
            "rows.\n"
            " 1) Provide a one-off default now which will be set on all "
            "existing rows\n"
            " 2) Quit and manually define a default value in models.py."
        )
        # Monkeypatch interactive questioner to auto accept
        prompt_stdout = io.StringIO()
        with self.temporary_migration_module(module="migrations.test_auto_now_add"):
            call_command(
                "makemigrations", "migrations", interactive=True, stdout=prompt_stdout
            )
        prompt_output = prompt_stdout.getvalue()
        self.assertIn(input_msg, prompt_output)
        self.assertIn("Please enter the default value as valid Python.", prompt_output)
        self.assertIn(
            "Accept the default 'timezone.now' by pressing 'Enter' or provide "
            "another value.",
            prompt_output,
        )
        self.assertIn("Type 'exit' to exit this prompt", prompt_output)
        self.assertIn("Add field creation_date to entry", prompt_output)

    @mock.patch("builtins.input", return_value="2")
    def test_makemigrations_auto_now_add_interactive_quit(self, mock_input):
        class Author(models.Model):
            publishing_date = models.DateField(auto_now_add=True)

            class Meta:
                app_label = "migrations"

        with self.temporary_migration_module(module="migrations.test_migrations"):
            with captured_stdout():
                with self.assertRaises(SystemExit):
                    call_command("makemigrations", "migrations", interactive=True)

    def test_makemigrations_non_interactive_auto_now_add_addition(self):
        """
        Non-interactive makemigrations fails when a default is missing on a
        new field when auto_now_add=True.
        """

        class Entry(models.Model):
            creation_date = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "migrations"

        with self.temporary_migration_module(module="migrations.test_auto_now_add"):
            with self.assertRaises(SystemExit), captured_stdout() as out:
                call_command("makemigrations", "migrations", interactive=False)
        self.assertIn(
            "Field 'creation_date' on model 'entry' not migrated: it is "
            "impossible to add a field with 'auto_now_add=True' without "
            "specifying a default.",
            out.getvalue(),
        )

    def test_makemigrations_interactive_unique_callable_default_addition(self):
        """
        makemigrations prompts the user when adding a unique field with
        a callable default.
        """

        class Book(models.Model):
            created = models.DateTimeField(unique=True, default=timezone.now)

            class Meta:
                app_label = "migrations"

        version = get_docs_version()
        input_msg = (
            f"Callable default on unique field book.created will not generate "
            f"unique values upon migrating.\n"
            f"Please choose how to proceed:\n"
            f" 1) Continue making this migration as the first step in writing "
            f"a manual migration to generate unique values described here: "
            f"https://docs.djangoproject.com/en/{version}/howto/"
            f"writing-migrations/#migrations-that-add-unique-fields.\n"
            f" 2) Quit and edit field options in models.py.\n"
        )
        with self.temporary_migration_module(module="migrations.test_migrations"):
            # 2 - quit.
            with mock.patch("builtins.input", return_value="2"):
                with captured_stdout() as out, self.assertRaises(SystemExit):
                    call_command("makemigrations", "migrations", interactive=True)
            out_value = out.getvalue()
            self.assertIn(input_msg, out_value)
            self.assertNotIn("Add field created to book", out_value)
            # 1 - continue.
            with mock.patch("builtins.input", return_value="1"):
                with captured_stdout() as out:
                    call_command("makemigrations", "migrations", interactive=True)
            out_value = out.getvalue()
            self.assertIn(input_msg, out_value)
            self.assertIn("Add field created to book", out_value)

    def test_makemigrations_non_interactive_unique_callable_default_addition(self):
        class Book(models.Model):
            created = models.DateTimeField(unique=True, default=timezone.now)

            class Meta:
                app_label = "migrations"

        with self.temporary_migration_module(module="migrations.test_migrations"):
            with captured_stdout() as out:
                call_command("makemigrations", "migrations", interactive=False)
            out_value = out.getvalue()
            self.assertIn("Add field created to book", out_value)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"},
    )
    def test_makemigrations_continues_number_sequence_after_squash(self):
        with self.temporary_migration_module(
            module="migrations.test_migrations_squashed"
        ):
            with captured_stdout() as out:
                call_command(
                    "makemigrations",
                    "migrations",
                    interactive=False,
                    empty=True,
                )
            out_value = out.getvalue()
            self.assertIn("0003_auto", out_value)


class SquashMigrationsTests(MigrationTestBase):
    """
    Tests running the squashmigrations command.
    """

    def test_squashmigrations_squashes(self):
        """
        squashmigrations squashes migrations.
        """
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "squashmigrations",
                "migrations",
                "0002",
                interactive=False,
                stdout=out,
                no_color=True,
            )

            squashed_migration_file = os.path.join(
                migration_dir, "0001_squashed_0002_second.py"
            )
            self.assertTrue(os.path.exists(squashed_migration_file))
        self.assertEqual(
            out.getvalue(),
            "Will squash the following migrations:\n"
            " - 0001_initial\n"
            " - 0002_second\n"
            "Optimizing...\n"
            "  Optimized from 8 operations to 2 operations.\n"
            "Created new squashed migration %s\n"
            "  You should commit this migration but leave the old ones in place;\n"
            "  the new migration will be used for new installs. Once you are sure\n"
            "  all instances of the codebase have applied the migrations you "
            "squashed,\n"
            "  you can delete them.\n" % squashed_migration_file,
        )

    def test_squashmigrations_initial_attribute(self):
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "squashmigrations", "migrations", "0002", interactive=False, verbosity=0
            )

            squashed_migration_file = os.path.join(
                migration_dir, "0001_squashed_0002_second.py"
            )
            with open(squashed_migration_file, encoding="utf-8") as fp:
                content = fp.read()
                self.assertIn("initial = True", content)

    def test_squashmigrations_optimizes(self):
        """
        squashmigrations optimizes operations.
        """
        out = io.StringIO()
        with self.temporary_migration_module(module="migrations.test_migrations"):
            call_command(
                "squashmigrations",
                "migrations",
                "0002",
                interactive=False,
                verbosity=1,
                stdout=out,
            )
        self.assertIn("Optimized from 8 operations to 2 operations.", out.getvalue())

    def test_ticket_23799_squashmigrations_no_optimize(self):
        """
        squashmigrations --no-optimize doesn't optimize operations.
        """
        out = io.StringIO()
        with self.temporary_migration_module(module="migrations.test_migrations"):
            call_command(
                "squashmigrations",
                "migrations",
                "0002",
                interactive=False,
                verbosity=1,
                no_optimize=True,
                stdout=out,
            )
        self.assertIn("Skipping optimization", out.getvalue())

    def test_squashmigrations_valid_start(self):
        """
        squashmigrations accepts a starting migration.
        """
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_changes"
        ) as migration_dir:
            call_command(
                "squashmigrations",
                "migrations",
                "0002",
                "0003",
                interactive=False,
                verbosity=1,
                stdout=out,
            )

            squashed_migration_file = os.path.join(
                migration_dir, "0002_second_squashed_0003_third.py"
            )
            with open(squashed_migration_file, encoding="utf-8") as fp:
                content = fp.read()
                if HAS_BLACK:
                    test_str = '        ("migrations", "0001_initial")'
                else:
                    test_str = "        ('migrations', '0001_initial')"
                self.assertIn(test_str, content)
                self.assertNotIn("initial = True", content)
        out = out.getvalue()
        self.assertNotIn(" - 0001_initial", out)
        self.assertIn(" - 0002_second", out)
        self.assertIn(" - 0003_third", out)

    def test_squashmigrations_invalid_start(self):
        """
        squashmigrations doesn't accept a starting migration after the ending migration.
        """
        with self.temporary_migration_module(
            module="migrations.test_migrations_no_changes"
        ):
            msg = (
                "The migration 'migrations.0003_third' cannot be found. Maybe "
                "it comes after the migration 'migrations.0002_second'"
            )
            with self.assertRaisesMessage(CommandError, msg):
                call_command(
                    "squashmigrations",
                    "migrations",
                    "0003",
                    "0002",
                    interactive=False,
                    verbosity=0,
                )

    def test_squashed_name_with_start_migration_name(self):
        """--squashed-name specifies the new migration's name."""
        squashed_name = "squashed_name"
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "squashmigrations",
                "migrations",
                "0001",
                "0002",
                squashed_name=squashed_name,
                interactive=False,
                verbosity=0,
            )
            squashed_migration_file = os.path.join(
                migration_dir, "0001_%s.py" % squashed_name
            )
            self.assertTrue(os.path.exists(squashed_migration_file))

    def test_squashed_name_without_start_migration_name(self):
        """--squashed-name also works if a start migration is omitted."""
        squashed_name = "squashed_name"
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "squashmigrations",
                "migrations",
                "0001",
                squashed_name=squashed_name,
                interactive=False,
                verbosity=0,
            )
            squashed_migration_file = os.path.join(
                migration_dir, "0001_%s.py" % squashed_name
            )
            self.assertTrue(os.path.exists(squashed_migration_file))

    def test_squashed_name_exists(self):
        msg = "Migration 0001_initial already exists. Use a different name."
        with self.temporary_migration_module(module="migrations.test_migrations"):
            with self.assertRaisesMessage(CommandError, msg):
                call_command(
                    "squashmigrations",
                    "migrations",
                    "0001",
                    "0002",
                    squashed_name="initial",
                    interactive=False,
                    verbosity=0,
                )

    def test_squashmigrations_manual_porting(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_manual_porting",
        ) as migration_dir:
            call_command(
                "squashmigrations",
                "migrations",
                "0002",
                interactive=False,
                stdout=out,
                no_color=True,
            )
            squashed_migration_file = os.path.join(
                migration_dir,
                "0001_squashed_0002_second.py",
            )
            self.assertTrue(os.path.exists(squashed_migration_file))
        black_warning = ""
        if HAS_BLACK:
            black_warning = (
                "Squashed migration couldn't be formatted using the "
                '"black" command. You can call it manually.\n'
            )
        self.assertEqual(
            out.getvalue(),
            f"Will squash the following migrations:\n"
            f" - 0001_initial\n"
            f" - 0002_second\n"
            f"Optimizing...\n"
            f"  No optimizations possible.\n"
            f"Created new squashed migration {squashed_migration_file}\n"
            f"  You should commit this migration but leave the old ones in place;\n"
            f"  the new migration will be used for new installs. Once you are sure\n"
            f"  all instances of the codebase have applied the migrations you "
            f"squashed,\n"
            f"  you can delete them.\n"
            f"Manual porting required\n"
            f"  Your migrations contained functions that must be manually copied "
            f"over,\n"
            f"  as we could not safely copy their implementation.\n"
            f"  See the comment at the top of the squashed migration for details.\n"
            + black_warning,
        )


class AppLabelErrorTests(TestCase):
    """
    This class inherits TestCase because MigrationTestBase uses
    `available_apps = ['migrations']` which means that it's the only installed
    app. 'django.contrib.auth' must be in INSTALLED_APPS for some of these
    tests.
    """

    nonexistent_app_error = "No installed app with label 'nonexistent_app'."
    did_you_mean_auth_error = (
        "No installed app with label 'django.contrib.auth'. Did you mean 'auth'?"
    )

    def test_makemigrations_nonexistent_app_label(self):
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            call_command("makemigrations", "nonexistent_app", stderr=err)
        self.assertIn(self.nonexistent_app_error, err.getvalue())

    def test_makemigrations_app_name_specified_as_label(self):
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            call_command("makemigrations", "django.contrib.auth", stderr=err)
        self.assertIn(self.did_you_mean_auth_error, err.getvalue())

    def test_migrate_nonexistent_app_label(self):
        with self.assertRaisesMessage(CommandError, self.nonexistent_app_error):
            call_command("migrate", "nonexistent_app")

    def test_migrate_app_name_specified_as_label(self):
        with self.assertRaisesMessage(CommandError, self.did_you_mean_auth_error):
            call_command("migrate", "django.contrib.auth")

    def test_showmigrations_nonexistent_app_label(self):
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            call_command("showmigrations", "nonexistent_app", stderr=err)
        self.assertIn(self.nonexistent_app_error, err.getvalue())

    def test_showmigrations_app_name_specified_as_label(self):
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            call_command("showmigrations", "django.contrib.auth", stderr=err)
        self.assertIn(self.did_you_mean_auth_error, err.getvalue())

    def test_sqlmigrate_nonexistent_app_label(self):
        with self.assertRaisesMessage(CommandError, self.nonexistent_app_error):
            call_command("sqlmigrate", "nonexistent_app", "0002")

    def test_sqlmigrate_app_name_specified_as_label(self):
        with self.assertRaisesMessage(CommandError, self.did_you_mean_auth_error):
            call_command("sqlmigrate", "django.contrib.auth", "0002")

    def test_squashmigrations_nonexistent_app_label(self):
        with self.assertRaisesMessage(CommandError, self.nonexistent_app_error):
            call_command("squashmigrations", "nonexistent_app", "0002")

    def test_squashmigrations_app_name_specified_as_label(self):
        with self.assertRaisesMessage(CommandError, self.did_you_mean_auth_error):
            call_command("squashmigrations", "django.contrib.auth", "0002")

    def test_optimizemigration_nonexistent_app_label(self):
        with self.assertRaisesMessage(CommandError, self.nonexistent_app_error):
            call_command("optimizemigration", "nonexistent_app", "0002")

    def test_optimizemigration_app_name_specified_as_label(self):
        with self.assertRaisesMessage(CommandError, self.did_you_mean_auth_error):
            call_command("optimizemigration", "django.contrib.auth", "0002")


class OptimizeMigrationTests(MigrationTestBase):
    def test_no_optimization_possible(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "optimizemigration", "migrations", "0002", stdout=out, no_color=True
            )
            migration_file = os.path.join(migration_dir, "0002_second.py")
            self.assertTrue(os.path.exists(migration_file))
            call_command(
                "optimizemigration",
                "migrations",
                "0002",
                stdout=out,
                no_color=True,
                verbosity=0,
            )
        self.assertEqual(out.getvalue(), "No optimizations possible.\n")

    def test_optimization(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "optimizemigration", "migrations", "0001", stdout=out, no_color=True
            )
            initial_migration_file = os.path.join(migration_dir, "0001_initial.py")
            self.assertTrue(os.path.exists(initial_migration_file))
            with open(initial_migration_file) as fp:
                content = fp.read()
                self.assertIn(
                    '("bool", models.BooleanField'
                    if HAS_BLACK
                    else "('bool', models.BooleanField",
                    content,
                )
        self.assertEqual(
            out.getvalue(),
            f"Optimizing from 4 operations to 2 operations.\n"
            f"Optimized migration {initial_migration_file}\n",
        )

    def test_optimization_no_verbosity(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations"
        ) as migration_dir:
            call_command(
                "optimizemigration",
                "migrations",
                "0001",
                stdout=out,
                no_color=True,
                verbosity=0,
            )
            initial_migration_file = os.path.join(migration_dir, "0001_initial.py")
            self.assertTrue(os.path.exists(initial_migration_file))
            with open(initial_migration_file) as fp:
                content = fp.read()
                self.assertIn(
                    '("bool", models.BooleanField'
                    if HAS_BLACK
                    else "('bool', models.BooleanField",
                    content,
                )
        self.assertEqual(out.getvalue(), "")

    def test_creates_replace_migration_manual_porting(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_manual_porting"
        ) as migration_dir:
            call_command(
                "optimizemigration", "migrations", "0003", stdout=out, no_color=True
            )
            optimized_migration_file = os.path.join(
                migration_dir, "0003_third_optimized.py"
            )
            self.assertTrue(os.path.exists(optimized_migration_file))
            with open(optimized_migration_file) as fp:
                content = fp.read()
                self.assertIn("replaces = [", content)
        black_warning = ""
        if HAS_BLACK:
            black_warning = (
                "Optimized migration couldn't be formatted using the "
                '"black" command. You can call it manually.\n'
            )
        self.assertEqual(
            out.getvalue(),
            "Optimizing from 3 operations to 2 operations.\n"
            "Manual porting required\n"
            "  Your migrations contained functions that must be manually copied over,\n"
            "  as we could not safely copy their implementation.\n"
            "  See the comment at the top of the optimized migration for details.\n"
            + black_warning
            + f"Optimized migration {optimized_migration_file}\n",
        )

    def test_fails_squash_migration_manual_porting(self):
        out = io.StringIO()
        with self.temporary_migration_module(
            module="migrations.test_migrations_manual_porting"
        ) as migration_dir:
            msg = (
                "Migration will require manual porting but is already a squashed "
                "migration.\nTransition to a normal migration first: "
                "https://docs.djangoproject.com/en/dev/topics/migrations/"
                "#squashing-migrations"
            )
            with self.assertRaisesMessage(CommandError, msg):
                call_command("optimizemigration", "migrations", "0004", stdout=out)
            optimized_migration_file = os.path.join(
                migration_dir, "0004_fourth_optimized.py"
            )
            self.assertFalse(os.path.exists(optimized_migration_file))
        self.assertEqual(
            out.getvalue(), "Optimizing from 3 operations to 2 operations.\n"
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_optimizemigration_check(self):
        with self.assertRaises(SystemExit):
            call_command(
                "optimizemigration", "--check", "migrations", "0001", verbosity=0
            )

        call_command("optimizemigration", "--check", "migrations", "0002", verbosity=0)

    @override_settings(
        INSTALLED_APPS=["migrations.migrations_test_apps.unmigrated_app_simple"],
    )
    def test_app_without_migrations(self):
        msg = "App 'unmigrated_app_simple' does not have migrations."
        with self.assertRaisesMessage(CommandError, msg):
            call_command("optimizemigration", "unmigrated_app_simple", "0001")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_clashing_prefix"},
    )
    def test_ambigious_prefix(self):
        msg = (
            "More than one migration matches 'a' in app 'migrations'. Please "
            "be more specific."
        )
        with self.assertRaisesMessage(CommandError, msg):
            call_command("optimizemigration", "migrations", "a")

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_unknown_prefix(self):
        msg = "Cannot find a migration matching 'nonexistent' from app 'migrations'."
        with self.assertRaisesMessage(CommandError, msg):
            call_command("optimizemigration", "migrations", "nonexistent")
