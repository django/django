from unittest import mock

from django.apps.registry import apps as global_apps
from django.db import DatabaseError, connection, migrations, models
from django.db.migrations.exceptions import InvalidMigrationPlan
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState
from django.test import (
    SimpleTestCase,
    modify_settings,
    override_settings,
    skipUnlessDBFeature,
)
from django.test.utils import isolate_lru_cache

from .test_base import MigrationTestBase


@modify_settings(INSTALLED_APPS={"append": "migrations2"})
class ExecutorTests(MigrationTestBase):
    """
    Tests the migration executor (full end-to-end running).

    Bear in mind that if these are failing you should fix the other
    test failures first, as they may be propagating into here.
    """

    available_apps = [
        "migrations",
        "migrations2",
        "django.contrib.auth",
        "django.contrib.contenttypes",
    ]

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_run(self):
        """
        Tests running a simple set of migrations.
        """
        executor = MigrationExecutor(connection)
        # Let's look at the plan first and make sure it's up to scratch
        plan = executor.migration_plan([("migrations", "0002_second")])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
                (executor.loader.graph.nodes["migrations", "0002_second"], False),
            ],
        )
        # Were the tables there before?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_book")
        # Alright, let's try running it
        executor.migrate([("migrations", "0002_second")])
        # Are the tables there now?
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_book")
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        # Alright, let's undo what we did
        plan = executor.migration_plan([("migrations", None)])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0002_second"], True),
                (executor.loader.graph.nodes["migrations", "0001_initial"], True),
            ],
        )
        executor.migrate([("migrations", None)])
        # Are the tables gone?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_book")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_run_with_squashed(self):
        """
        Tests running a squashed migration from zero (should ignore what it replaces)
        """
        executor = MigrationExecutor(connection)
        # Check our leaf node is the squashed one
        leaves = [
            key for key in executor.loader.graph.leaf_nodes() if key[0] == "migrations"
        ]
        self.assertEqual(leaves, [("migrations", "0001_squashed_0002")])
        # Check the plan
        plan = executor.migration_plan([("migrations", "0001_squashed_0002")])
        self.assertEqual(
            plan,
            [
                (
                    executor.loader.graph.nodes["migrations", "0001_squashed_0002"],
                    False,
                ),
            ],
        )
        # Were the tables there before?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_book")
        # Alright, let's try running it
        executor.migrate([("migrations", "0001_squashed_0002")])
        # Are the tables there now?
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_book")
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        # Alright, let's undo what we did. Should also just use squashed.
        plan = executor.migration_plan([("migrations", None)])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_squashed_0002"], True),
            ],
        )
        executor.migrate([("migrations", None)])
        # Are the tables gone?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_book")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"},
    )
    def test_migrate_backward_to_squashed_migration(self):
        executor = MigrationExecutor(connection)
        try:
            self.assertTableNotExists("migrations_author")
            self.assertTableNotExists("migrations_book")
            executor.migrate([("migrations", "0001_squashed_0002")])
            self.assertTableExists("migrations_author")
            self.assertTableExists("migrations_book")
            executor.loader.build_graph()
            # Migrate backward to a squashed migration.
            executor.migrate([("migrations", "0001_initial")])
            self.assertTableExists("migrations_author")
            self.assertTableNotExists("migrations_book")
        finally:
            # Unmigrate everything.
            executor = MigrationExecutor(connection)
            executor.migrate([("migrations", None)])
            self.assertTableNotExists("migrations_author")
            self.assertTableNotExists("migrations_book")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_non_atomic"}
    )
    def test_non_atomic_migration(self):
        """
        Applying a non-atomic migration works as expected.
        """
        executor = MigrationExecutor(connection)
        with self.assertRaisesMessage(RuntimeError, "Abort migration"):
            executor.migrate([("migrations", "0001_initial")])
        self.assertTableExists("migrations_publisher")
        migrations_apps = executor.loader.project_state(
            ("migrations", "0001_initial")
        ).apps
        Publisher = migrations_apps.get_model("migrations", "Publisher")
        self.assertTrue(Publisher.objects.exists())
        self.assertTableNotExists("migrations_book")

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_atomic_operation"}
    )
    def test_atomic_operation_in_non_atomic_migration(self):
        """
        An atomic operation is properly rolled back inside a non-atomic
        migration.
        """
        executor = MigrationExecutor(connection)
        with self.assertRaisesMessage(RuntimeError, "Abort migration"):
            executor.migrate([("migrations", "0001_initial")])
        migrations_apps = executor.loader.project_state(
            ("migrations", "0001_initial")
        ).apps
        Editor = migrations_apps.get_model("migrations", "Editor")
        self.assertFalse(Editor.objects.exists())
        # Record previous migration as successful.
        executor.migrate([("migrations", "0001_initial")], fake=True)
        # Rebuild the graph to reflect the new DB state.
        executor.loader.build_graph()
        # Migrating backwards is also atomic.
        with self.assertRaisesMessage(RuntimeError, "Abort migration"):
            executor.migrate([("migrations", None)])
        self.assertFalse(Editor.objects.exists())

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations",
            "migrations2": "migrations2.test_migrations_2",
        }
    )
    def test_empty_plan(self):
        """
        Re-planning a full migration of a fully-migrated set doesn't
        perform spurious unmigrations and remigrations.

        There was previously a bug where the executor just always performed the
        backwards plan for applied migrations - which even for the most recent
        migration in an app, might include other, dependent apps, and these
        were being unmigrated.
        """
        # Make the initial plan, check it
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(
            [
                ("migrations", "0002_second"),
                ("migrations2", "0001_initial"),
            ]
        )
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
                (executor.loader.graph.nodes["migrations", "0002_second"], False),
                (executor.loader.graph.nodes["migrations2", "0001_initial"], False),
            ],
        )
        # Fake-apply all migrations
        executor.migrate(
            [("migrations", "0002_second"), ("migrations2", "0001_initial")], fake=True
        )
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        # Now plan a second time and make sure it's empty
        plan = executor.migration_plan(
            [
                ("migrations", "0002_second"),
                ("migrations2", "0001_initial"),
            ]
        )
        self.assertEqual(plan, [])
        # The resulting state should include applied migrations.
        state = executor.migrate(
            [
                ("migrations", "0002_second"),
                ("migrations2", "0001_initial"),
            ]
        )
        self.assertIn(("migrations", "book"), state.models)
        self.assertIn(("migrations", "author"), state.models)
        self.assertIn(("migrations2", "otherauthor"), state.models)
        # Erase all the fake records
        executor.recorder.record_unapplied("migrations2", "0001_initial")
        executor.recorder.record_unapplied("migrations", "0002_second")
        executor.recorder.record_unapplied("migrations", "0001_initial")

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations",
            "migrations2": "migrations2.test_migrations_2_no_deps",
        }
    )
    def test_mixed_plan_not_supported(self):
        """
        Although the MigrationExecutor interfaces allows for mixed migration
        plans (combined forwards and backwards migrations) this is not
        supported.
        """
        # Prepare for mixed plan
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan([("migrations", "0002_second")])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
                (executor.loader.graph.nodes["migrations", "0002_second"], False),
            ],
        )
        executor.migrate(None, plan)
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        self.assertIn(
            ("migrations", "0001_initial"), executor.loader.applied_migrations
        )
        self.assertIn(("migrations", "0002_second"), executor.loader.applied_migrations)
        self.assertNotIn(
            ("migrations2", "0001_initial"), executor.loader.applied_migrations
        )

        # Generate mixed plan
        plan = executor.migration_plan(
            [
                ("migrations", None),
                ("migrations2", "0001_initial"),
            ]
        )
        msg = (
            "Migration plans with both forwards and backwards migrations are "
            "not supported. Please split your migration process into separate "
            "plans of only forwards OR backwards migrations."
        )
        with self.assertRaisesMessage(InvalidMigrationPlan, msg) as cm:
            executor.migrate(None, plan)
        self.assertEqual(
            cm.exception.args[1],
            [
                (executor.loader.graph.nodes["migrations", "0002_second"], True),
                (executor.loader.graph.nodes["migrations", "0001_initial"], True),
                (executor.loader.graph.nodes["migrations2", "0001_initial"], False),
            ],
        )
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        executor.migrate(
            [
                ("migrations", None),
                ("migrations2", None),
            ]
        )
        # Are the tables gone?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_book")
        self.assertTableNotExists("migrations2_otherauthor")

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_soft_apply(self):
        """
        Tests detection of initial migrations already having been applied.
        """
        state = {"faked": None}

        def fake_storer(phase, migration=None, fake=None):
            state["faked"] = fake

        executor = MigrationExecutor(connection, progress_callback=fake_storer)
        # Were the tables there before?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        # Run it normally
        self.assertEqual(
            executor.migration_plan([("migrations", "0001_initial")]),
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
            ],
        )
        executor.migrate([("migrations", "0001_initial")])
        # Are the tables there now?
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble")
        # We shouldn't have faked that one
        self.assertIs(state["faked"], False)
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        # Fake-reverse that
        executor.migrate([("migrations", None)], fake=True)
        # Are the tables still there?
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble")
        # Make sure that was faked
        self.assertIs(state["faked"], True)
        # Finally, migrate forwards; this should fake-apply our initial migration
        executor.loader.build_graph()
        self.assertEqual(
            executor.migration_plan([("migrations", "0001_initial")]),
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
            ],
        )
        # Applying the migration should raise a database level error
        # because we haven't given the --fake-initial option
        with self.assertRaises(DatabaseError):
            executor.migrate([("migrations", "0001_initial")])
        # Reset the faked state
        state = {"faked": None}
        # Allow faking of initial CreateModel operations
        executor.migrate([("migrations", "0001_initial")], fake_initial=True)
        self.assertIs(state["faked"], True)
        # And migrate back to clean up the database
        executor.loader.build_graph()
        executor.migrate([("migrations", None)])
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_migrations_custom_user",
            "django.contrib.auth": "django.contrib.auth.migrations",
        },
        AUTH_USER_MODEL="migrations.Author",
    )
    def test_custom_user(self):
        """
        Regression test for #22325 - references to a custom user model defined in the
        same app are not resolved correctly.
        """
        with isolate_lru_cache(global_apps.get_swappable_settings_name):
            executor = MigrationExecutor(connection)
            self.assertTableNotExists("migrations_author")
            self.assertTableNotExists("migrations_tribble")
            # Migrate forwards
            executor.migrate([("migrations", "0001_initial")])
            self.assertTableExists("migrations_author")
            self.assertTableExists("migrations_tribble")
            # The soft-application detection works.
            # Change table_names to not return auth_user during this as it
            # wouldn't be there in a normal run, and ensure migrations.Author
            # exists in the global app registry temporarily.
            old_table_names = connection.introspection.table_names
            connection.introspection.table_names = lambda c: [
                x for x in old_table_names(c) if x != "auth_user"
            ]
            migrations_apps = executor.loader.project_state(
                ("migrations", "0001_initial"),
            ).apps
            global_apps.get_app_config("migrations").models["author"] = (
                migrations_apps.get_model("migrations", "author")
            )
            try:
                migration = executor.loader.get_migration("auth", "0001_initial")
                self.assertIs(executor.detect_soft_applied(None, migration)[0], True)
            finally:
                connection.introspection.table_names = old_table_names
                del global_apps.get_app_config("migrations").models["author"]
                # Migrate back to clean up the database.
                executor.loader.build_graph()
                executor.migrate([("migrations", None)])
                self.assertTableNotExists("migrations_author")
                self.assertTableNotExists("migrations_tribble")

    @override_settings(
        MIGRATION_MODULES={
            "migrations": "migrations.test_add_many_to_many_field_initial",
        },
    )
    def test_detect_soft_applied_add_field_manytomanyfield(self):
        """
        executor.detect_soft_applied() detects ManyToManyField tables from an
        AddField operation. This checks the case of AddField in a migration
        with other operations (0001) and the case of AddField in its own
        migration (0002).
        """
        tables = [
            # from 0001
            "migrations_project",
            "migrations_task",
            "migrations_project_tasks",
            # from 0002
            "migrations_task_projects",
        ]
        executor = MigrationExecutor(connection)
        # Create the tables for 0001 but make it look like the migration hasn't
        # been applied.
        executor.migrate([("migrations", "0001_initial")])
        executor.migrate([("migrations", None)], fake=True)
        for table in tables[:3]:
            self.assertTableExists(table)
        # Table detection sees 0001 is applied but not 0002.
        migration = executor.loader.get_migration("migrations", "0001_initial")
        self.assertIs(executor.detect_soft_applied(None, migration)[0], True)
        migration = executor.loader.get_migration("migrations", "0002_initial")
        self.assertIs(executor.detect_soft_applied(None, migration)[0], False)

        # Create the tables for both migrations but make it look like neither
        # has been applied.
        executor.loader.build_graph()
        executor.migrate([("migrations", "0001_initial")], fake=True)
        executor.migrate([("migrations", "0002_initial")])
        executor.loader.build_graph()
        executor.migrate([("migrations", None)], fake=True)
        # Table detection sees 0002 is applied.
        migration = executor.loader.get_migration("migrations", "0002_initial")
        self.assertIs(executor.detect_soft_applied(None, migration)[0], True)

        # Leave the tables for 0001 except the many-to-many table. That missing
        # table should cause detect_soft_applied() to return False.
        with connection.schema_editor() as editor:
            for table in tables[2:]:
                editor.execute(editor.sql_delete_table % {"table": table})
        migration = executor.loader.get_migration("migrations", "0001_initial")
        self.assertIs(executor.detect_soft_applied(None, migration)[0], False)

        # Cleanup by removing the remaining tables.
        with connection.schema_editor() as editor:
            for table in tables[:2]:
                editor.execute(editor.sql_delete_table % {"table": table})
        for table in tables:
            self.assertTableNotExists(table)

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.lookuperror_a",
            "migrations.migrations_test_apps.lookuperror_b",
            "migrations.migrations_test_apps.lookuperror_c",
        ]
    )
    def test_unrelated_model_lookups_forwards(self):
        """
        #24123 - All models of apps already applied which are
        unrelated to the first app being applied are part of the initial model
        state.
        """
        try:
            executor = MigrationExecutor(connection)
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")
            executor.migrate([("lookuperror_b", "0003_b3")])
            self.assertTableExists("lookuperror_b_b3")
            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()

            # Migrate forwards -- This led to a lookup LookupErrors because
            # lookuperror_b.B2 is already applied
            executor.migrate(
                [
                    ("lookuperror_a", "0004_a4"),
                    ("lookuperror_c", "0003_c3"),
                ]
            )
            self.assertTableExists("lookuperror_a_a4")
            self.assertTableExists("lookuperror_c_c3")

            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()
        finally:
            # Cleanup
            executor.migrate(
                [
                    ("lookuperror_a", None),
                    ("lookuperror_b", None),
                    ("lookuperror_c", None),
                ]
            )
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.lookuperror_a",
            "migrations.migrations_test_apps.lookuperror_b",
            "migrations.migrations_test_apps.lookuperror_c",
        ]
    )
    def test_unrelated_model_lookups_backwards(self):
        """
        #24123 - All models of apps being unapplied which are
        unrelated to the first app being unapplied are part of the initial
        model state.
        """
        try:
            executor = MigrationExecutor(connection)
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")
            executor.migrate(
                [
                    ("lookuperror_a", "0004_a4"),
                    ("lookuperror_b", "0003_b3"),
                    ("lookuperror_c", "0003_c3"),
                ]
            )
            self.assertTableExists("lookuperror_b_b3")
            self.assertTableExists("lookuperror_a_a4")
            self.assertTableExists("lookuperror_c_c3")
            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()

            # Migrate backwards -- This led to a lookup LookupErrors because
            # lookuperror_b.B2 is not in the initial state (unrelated to app c)
            executor.migrate([("lookuperror_a", None)])

            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()
        finally:
            # Cleanup
            executor.migrate([("lookuperror_b", None), ("lookuperror_c", None)])
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.mutate_state_a",
            "migrations.migrations_test_apps.mutate_state_b",
        ]
    )
    def test_unrelated_applied_migrations_mutate_state(self):
        """
        #26647 - Unrelated applied migrations should be part of the final
        state in both directions.
        """
        executor = MigrationExecutor(connection)
        executor.migrate(
            [
                ("mutate_state_b", "0002_add_field"),
            ]
        )
        # Migrate forward.
        executor.loader.build_graph()
        state = executor.migrate(
            [
                ("mutate_state_a", "0001_initial"),
            ]
        )
        self.assertIn("added", state.models["mutate_state_b", "b"].fields)
        executor.loader.build_graph()
        # Migrate backward.
        state = executor.migrate(
            [
                ("mutate_state_a", None),
            ]
        )
        self.assertIn("added", state.models["mutate_state_b", "b"].fields)
        executor.migrate(
            [
                ("mutate_state_b", None),
            ]
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_process_callback(self):
        """
        #24129 - Tests callback process
        """
        call_args_list = []

        def callback(*args):
            call_args_list.append(args)

        executor = MigrationExecutor(connection, progress_callback=callback)
        # Were the tables there before?
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        executor.migrate(
            [
                ("migrations", "0001_initial"),
                ("migrations", "0002_second"),
            ]
        )
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()

        executor.migrate(
            [
                ("migrations", None),
                ("migrations", None),
            ]
        )
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")

        migrations = executor.loader.graph.nodes
        expected = [
            ("render_start",),
            ("render_success",),
            ("apply_start", migrations["migrations", "0001_initial"], False),
            ("apply_success", migrations["migrations", "0001_initial"], False),
            ("apply_start", migrations["migrations", "0002_second"], False),
            ("apply_success", migrations["migrations", "0002_second"], False),
            ("render_start",),
            ("render_success",),
            ("unapply_start", migrations["migrations", "0002_second"], False),
            ("unapply_success", migrations["migrations", "0002_second"], False),
            ("unapply_start", migrations["migrations", "0001_initial"], False),
            ("unapply_success", migrations["migrations", "0001_initial"], False),
        ]
        self.assertEqual(call_args_list, expected)

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.alter_fk.author_app",
            "migrations.migrations_test_apps.alter_fk.book_app",
        ]
    )
    def test_alter_id_type_with_fk(self):
        try:
            executor = MigrationExecutor(connection)
            self.assertTableNotExists("author_app_author")
            self.assertTableNotExists("book_app_book")
            # Apply initial migrations
            executor.migrate(
                [
                    ("author_app", "0001_initial"),
                    ("book_app", "0001_initial"),
                ]
            )
            self.assertTableExists("author_app_author")
            self.assertTableExists("book_app_book")
            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()

            # Apply PK type alteration
            executor.migrate([("author_app", "0002_alter_id")])

            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()
        finally:
            # We can't simply unapply the migrations here because there is no
            # implicit cast from VARCHAR to INT on the database level.
            with connection.schema_editor() as editor:
                editor.execute(editor.sql_delete_table % {"table": "book_app_book"})
                editor.execute(editor.sql_delete_table % {"table": "author_app_author"})
            self.assertTableNotExists("author_app_author")
            self.assertTableNotExists("book_app_book")
            executor.migrate([("author_app", None)], fake=True)

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_apply_all_replaced_marks_replacement_as_applied(self):
        """
        Applying all replaced migrations marks replacement as applied (#24628).
        """
        recorder = MigrationRecorder(connection)
        # Place the database in a state where the replaced migrations are
        # partially applied: 0001 is applied, 0002 is not.
        recorder.record_applied("migrations", "0001_initial")
        executor = MigrationExecutor(connection)
        # Use fake because we don't actually have the first migration
        # applied, so the second will fail. And there's no need to actually
        # create/modify tables here, we're just testing the
        # MigrationRecord, which works the same with or without fake.
        executor.migrate([("migrations", "0002_second")], fake=True)

        # Because we've now applied 0001 and 0002 both, their squashed
        # replacement should be marked as applied.
        self.assertIn(
            ("migrations", "0001_squashed_0002"),
            recorder.applied_migrations(),
        )

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_migrate_marks_replacement_applied_even_if_it_did_nothing(self):
        """
        A new squash migration will be marked as applied even if all its
        replaced migrations were previously already applied (#24628).
        """
        recorder = MigrationRecorder(connection)
        # Record all replaced migrations as applied
        recorder.record_applied("migrations", "0001_initial")
        recorder.record_applied("migrations", "0002_second")
        executor = MigrationExecutor(connection)
        executor.migrate([("migrations", "0001_squashed_0002")])

        # Because 0001 and 0002 are both applied, even though this migrate run
        # didn't apply anything new, their squashed replacement should be
        # marked as applied.
        self.assertIn(
            ("migrations", "0001_squashed_0002"),
            recorder.applied_migrations(),
        )

    @override_settings(
        MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"}
    )
    def test_migrate_marks_replacement_unapplied(self):
        executor = MigrationExecutor(connection)
        executor.migrate([("migrations", "0001_squashed_0002")])
        try:
            self.assertIn(
                ("migrations", "0001_squashed_0002"),
                executor.recorder.applied_migrations(),
            )
        finally:
            executor.loader.build_graph()
            executor.migrate([("migrations", None)])
            self.assertNotIn(
                ("migrations", "0001_squashed_0002"),
                executor.recorder.applied_migrations(),
            )

    # When the feature is False, the operation and the record won't be
    # performed in a transaction and the test will systematically pass.
    @skipUnlessDBFeature("can_rollback_ddl")
    def test_migrations_applied_and_recorded_atomically(self):
        """Migrations are applied and recorded atomically."""

        class Migration(migrations.Migration):
            operations = [
                migrations.CreateModel(
                    "model",
                    [
                        ("id", models.AutoField(primary_key=True)),
                    ],
                ),
            ]

        executor = MigrationExecutor(connection)
        with mock.patch(
            "django.db.migrations.executor.MigrationExecutor.record_migration"
        ) as record_migration:
            record_migration.side_effect = RuntimeError("Recording migration failed.")
            with self.assertRaisesMessage(RuntimeError, "Recording migration failed."):
                executor.apply_migration(
                    ProjectState(),
                    Migration("0001_initial", "record_migration"),
                )
                executor.migrate([("migrations", "0001_initial")])
        # The migration isn't recorded as applied since it failed.
        migration_recorder = MigrationRecorder(connection)
        self.assertIs(
            migration_recorder.migration_qs.filter(
                app="record_migration",
                name="0001_initial",
            ).exists(),
            False,
        )
        self.assertTableNotExists("record_migration_model")

    def test_migrations_not_applied_on_deferred_sql_failure(self):
        """Migrations are not recorded if deferred SQL application fails."""

        class DeferredSQL:
            def __str__(self):
                raise DatabaseError("Failed to apply deferred SQL")

        class Migration(migrations.Migration):
            atomic = False

            def apply(self, project_state, schema_editor, collect_sql=False):
                schema_editor.deferred_sql.append(DeferredSQL())

        executor = MigrationExecutor(connection)
        with self.assertRaisesMessage(DatabaseError, "Failed to apply deferred SQL"):
            executor.apply_migration(
                ProjectState(),
                Migration("0001_initial", "deferred_sql"),
            )
        # The migration isn't recorded as applied since it failed.
        migration_recorder = MigrationRecorder(connection)
        self.assertIs(
            migration_recorder.migration_qs.filter(
                app="deferred_sql",
                name="0001_initial",
            ).exists(),
            False,
        )

    @mock.patch.object(MigrationRecorder, "has_table", return_value=False)
    def test_migrate_skips_schema_creation(self, mocked_has_table):
        """
        The django_migrations table is not created if there are no migrations
        to record.
        """
        executor = MigrationExecutor(connection)
        # 0 queries, since the query for has_table is being mocked.
        with self.assertNumQueries(0):
            executor.migrate([], plan=[])


class FakeLoader:
    def __init__(self, graph, applied):
        self.graph = graph
        self.applied_migrations = applied
        self.replace_migrations = True


class FakeMigration:
    """Really all we need is any object with a debug-useful repr."""

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "M<%s>" % self.name


class ExecutorUnitTests(SimpleTestCase):
    """(More) isolated unit tests for executor methods."""

    def test_minimize_rollbacks(self):
        """
        Minimize unnecessary rollbacks in connected apps.

        When you say "./manage.py migrate appA 0001", rather than migrating to
        just after appA-0001 in the linearized migration plan (which could roll
        back migrations in other apps that depend on appA 0001, but don't need
        to be rolled back since we're not rolling back appA 0001), we migrate
        to just before appA-0002.
        """
        a1_impl = FakeMigration("a1")
        a1 = ("a", "1")
        a2_impl = FakeMigration("a2")
        a2 = ("a", "2")
        b1_impl = FakeMigration("b1")
        b1 = ("b", "1")
        graph = MigrationGraph()
        graph.add_node(a1, a1_impl)
        graph.add_node(a2, a2_impl)
        graph.add_node(b1, b1_impl)
        graph.add_dependency(None, b1, a1)
        graph.add_dependency(None, a2, a1)

        executor = MigrationExecutor(None)
        executor.loader = FakeLoader(
            graph,
            {
                a1: a1_impl,
                b1: b1_impl,
                a2: a2_impl,
            },
        )

        plan = executor.migration_plan({a1})

        self.assertEqual(plan, [(a2_impl, True)])

    def test_minimize_rollbacks_branchy(self):
        r"""
        Minimize rollbacks when target has multiple in-app children.

        a: 1 <---- 3 <--\
              \ \- 2 <--- 4
               \       \
        b:      \- 1 <--- 2
        """
        a1_impl = FakeMigration("a1")
        a1 = ("a", "1")
        a2_impl = FakeMigration("a2")
        a2 = ("a", "2")
        a3_impl = FakeMigration("a3")
        a3 = ("a", "3")
        a4_impl = FakeMigration("a4")
        a4 = ("a", "4")
        b1_impl = FakeMigration("b1")
        b1 = ("b", "1")
        b2_impl = FakeMigration("b2")
        b2 = ("b", "2")
        graph = MigrationGraph()
        graph.add_node(a1, a1_impl)
        graph.add_node(a2, a2_impl)
        graph.add_node(a3, a3_impl)
        graph.add_node(a4, a4_impl)
        graph.add_node(b1, b1_impl)
        graph.add_node(b2, b2_impl)
        graph.add_dependency(None, a2, a1)
        graph.add_dependency(None, a3, a1)
        graph.add_dependency(None, a4, a2)
        graph.add_dependency(None, a4, a3)
        graph.add_dependency(None, b2, b1)
        graph.add_dependency(None, b1, a1)
        graph.add_dependency(None, b2, a2)

        executor = MigrationExecutor(None)
        executor.loader = FakeLoader(
            graph,
            {
                a1: a1_impl,
                b1: b1_impl,
                a2: a2_impl,
                b2: b2_impl,
                a3: a3_impl,
                a4: a4_impl,
            },
        )

        plan = executor.migration_plan({a1})

        should_be_rolled_back = [b2_impl, a4_impl, a2_impl, a3_impl]
        exp = [(m, True) for m in should_be_rolled_back]
        self.assertEqual(plan, exp)

    def test_backwards_nothing_to_do(self):
        r"""
        If the current state satisfies the given target, do nothing.

        a: 1 <--- 2
        b:    \- 1
        c:     \- 1

        If a1 is applied already and a2 is not, and we're asked to migrate to
        a1, don't apply or unapply b1 or c1, regardless of their current state.
        """
        a1_impl = FakeMigration("a1")
        a1 = ("a", "1")
        a2_impl = FakeMigration("a2")
        a2 = ("a", "2")
        b1_impl = FakeMigration("b1")
        b1 = ("b", "1")
        c1_impl = FakeMigration("c1")
        c1 = ("c", "1")
        graph = MigrationGraph()
        graph.add_node(a1, a1_impl)
        graph.add_node(a2, a2_impl)
        graph.add_node(b1, b1_impl)
        graph.add_node(c1, c1_impl)
        graph.add_dependency(None, a2, a1)
        graph.add_dependency(None, b1, a1)
        graph.add_dependency(None, c1, a1)

        executor = MigrationExecutor(None)
        executor.loader = FakeLoader(
            graph,
            {
                a1: a1_impl,
                b1: b1_impl,
            },
        )

        plan = executor.migration_plan({a1})

        self.assertEqual(plan, [])
