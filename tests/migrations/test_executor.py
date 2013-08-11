from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class ExecutorTests(TransactionTestCase):
    """
    Tests the migration executor (full end-to-end running).

    Bear in mind that if these are failing you should fix the other
    test failures first, as they may be propagating into here.
    """

    available_apps = ["migrations", "django.contrib.sessions"]

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_run(self):
        """
        Tests running a simple set of migrations.
        """
        executor = MigrationExecutor(connection)
        executor.recorder.flush()
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
        self.assertNotIn("migrations_author", connection.introspection.get_table_list(connection.cursor()))
        self.assertNotIn("migrations_book", connection.introspection.get_table_list(connection.cursor()))
        # Alright, let's try running it
        executor.migrate([("migrations", "0002_second")])
        # Are the tables there now?
        self.assertIn("migrations_author", connection.introspection.get_table_list(connection.cursor()))
        self.assertIn("migrations_book", connection.introspection.get_table_list(connection.cursor()))

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations", "sessions": "migrations.test_migrations_2"})
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
        # We use 'sessions' here as the second app as it's always present
        # in INSTALLED_APPS, so we can happily assign it test migrations.
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan([("migrations", "0002_second"), ("sessions", "0001_initial")])
        self.assertEqual(
            plan,
            [
                (executor.loader.graph.nodes["migrations", "0001_initial"], False),
                (executor.loader.graph.nodes["migrations", "0002_second"], False),
                (executor.loader.graph.nodes["sessions", "0001_initial"], False),
            ],
        )
        # Fake-apply all migrations
        executor.migrate([("migrations", "0002_second"), ("sessions", "0001_initial")], fake=True)
        # Now plan a second time and make sure it's empty
        plan = executor.migration_plan([("migrations", "0002_second"), ("sessions", "0001_initial")])
        self.assertEqual(plan, [])
        # Erase all the fake records
        executor.recorder.flush()
