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

    available_apps = ["migrations"]

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
        self.assertNotIn("migrations_author", connection.introspection.get_table_list(connection.cursor()))
        self.assertNotIn("migrations_book", connection.introspection.get_table_list(connection.cursor()))
        # Alright, let's try running it
        executor.migrate([("migrations", "0002_second")])
        # Are the tables there now?
        self.assertIn("migrations_author", connection.introspection.get_table_list(connection.cursor()))
        self.assertIn("migrations_book", connection.introspection.get_table_list(connection.cursor()))
