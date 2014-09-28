from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import modify_settings, override_settings
from django.apps.registry import apps as global_apps

from .test_base import MigrationTestBase


@modify_settings(INSTALLED_APPS={'append': 'migrations2'})
class ExecutorTests(MigrationTestBase):
    """
    Tests the migration executor (full end-to-end running).

    Bear in mind that if these are failing you should fix the other
    test failures first, as they may be propagating into here.
    """

    available_apps = ["migrations", "migrations2", "django.contrib.auth", "django.contrib.contenttypes"]

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

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"})
    def test_run_with_squashed(self):
        """
        Tests running a squashed migration from zero (should ignore what it replaces)
        """
        executor = MigrationExecutor(connection)
        # Check our leaf node is the squashed one
        leaves = [key for key in executor.loader.graph.leaf_nodes() if key[0] == "migrations"]
        self.assertEqual(leaves, [("migrations", "0001_squashed_0002")])
        # Check the plan
        plan = executor.migration_plan([("migrations", "0001_squashed_0002")])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_squashed_0002"], False),
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

    @override_settings(MIGRATION_MODULES={
        "migrations": "migrations.test_migrations",
        "migrations2": "migrations2.test_migrations_2",
    })
    def test_empty_plan(self):
        """
        Tests that re-planning a full migration of a fully-migrated set doesn't
        perform spurious unmigrations and remigrations.

        There was previously a bug where the executor just always performed the
        backwards plan for applied migrations - which even for the most recent
        migration in an app, might include other, dependent apps, and these
        were being unmigrated.
        """
        # Make the initial plan, check it
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan([
            ("migrations", "0002_second"),
            ("migrations2", "0001_initial"),
        ])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
                (executor.loader.graph.nodes["migrations", "0002_second"], False),
                (executor.loader.graph.nodes["migrations2", "0001_initial"], False),
            ],
        )
        # Fake-apply all migrations
        executor.migrate([
            ("migrations", "0002_second"),
            ("migrations2", "0001_initial")
        ], fake=True)
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        # Now plan a second time and make sure it's empty
        plan = executor.migration_plan([
            ("migrations", "0002_second"),
            ("migrations2", "0001_initial"),
        ])
        self.assertEqual(plan, [])
        # Erase all the fake records
        executor.recorder.record_unapplied("migrations2", "0001_initial")
        executor.recorder.record_unapplied("migrations", "0002_second")
        executor.recorder.record_unapplied("migrations", "0001_initial")

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_soft_apply(self):
        """
        Tests detection of initial migrations already having been applied.
        """
        state = {"faked": None}

        def fake_storer(phase, migration, fake):
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
        self.assertEqual(state["faked"], False)
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()
        # Fake-reverse that
        executor.migrate([("migrations", None)], fake=True)
        # Are the tables still there?
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble")
        # Make sure that was faked
        self.assertEqual(state["faked"], True)
        # Finally, migrate forwards; this should fake-apply our initial migration
        executor.loader.build_graph()
        self.assertEqual(
            executor.migration_plan([("migrations", "0001_initial")]),
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
            ],
        )
        executor.migrate([("migrations", "0001_initial")])
        self.assertEqual(state["faked"], True)
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
        executor = MigrationExecutor(connection)
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
        # Migrate forwards
        executor.migrate([("migrations", "0001_initial")])
        self.assertTableExists("migrations_author")
        self.assertTableExists("migrations_tribble")
        # Make sure the soft-application detection works (#23093)
        # Change table_names to not return auth_user during this as
        # it wouldn't be there in a normal run, and ensure migrations.Author
        # exists in the global app registry temporarily.
        old_table_names = connection.introspection.table_names
        connection.introspection.table_names = lambda c: [x for x in old_table_names(c) if x != "auth_user"]
        migrations_apps = executor.loader.project_state(("migrations", "0001_initial")).render()
        global_apps.get_app_config("migrations").models["author"] = migrations_apps.get_model("migrations", "author")
        try:
            migration = executor.loader.get_migration("auth", "0001_initial")
            self.assertEqual(executor.detect_soft_applied(migration), True)
        finally:
            connection.introspection.table_names = old_table_names
            del global_apps.get_app_config("migrations").models["author"]
        # And migrate back to clean up the database
        executor.loader.build_graph()
        executor.migrate([("migrations", None)])
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")
