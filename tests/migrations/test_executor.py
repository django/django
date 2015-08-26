from django.apps.registry import apps as global_apps
from django.db import connection
from django.db.migrations.exceptions import InvalidMigrationPlan
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.recorder import MigrationRecorder
from django.db.utils import DatabaseError
from django.test import TestCase, modify_settings, override_settings

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

    @override_settings(MIGRATION_MODULES={
        "migrations": "migrations.test_migrations",
        "migrations2": "migrations2.test_migrations_2_no_deps",
    })
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
        self.assertIn(('migrations', '0001_initial'), executor.loader.applied_migrations)
        self.assertIn(('migrations', '0002_second'), executor.loader.applied_migrations)
        self.assertNotIn(('migrations2', '0001_initial'), executor.loader.applied_migrations)

        # Generate mixed plan
        plan = executor.migration_plan([
            ("migrations", None),
            ("migrations2", "0001_initial"),
        ])
        msg = (
            'Migration plans with both forwards and backwards migrations are '
            'not supported. Please split your migration process into separate '
            'plans of only forwards OR backwards migrations.'
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
        executor.migrate([
            ("migrations", None),
            ("migrations2", None),
        ])
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
        # Applying the migration should raise a database level error
        # because we haven't given the --fake-initial option
        with self.assertRaises(DatabaseError):
            executor.migrate([("migrations", "0001_initial")])
        # Reset the faked state
        state = {"faked": None}
        # Allow faking of initial CreateModel operations
        executor.migrate([("migrations", "0001_initial")], fake_initial=True)
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
        migrations_apps = executor.loader.project_state(("migrations", "0001_initial")).apps
        global_apps.get_app_config("migrations").models["author"] = migrations_apps.get_model("migrations", "author")
        try:
            migration = executor.loader.get_migration("auth", "0001_initial")
            self.assertEqual(executor.detect_soft_applied(None, migration)[0], True)
        finally:
            connection.introspection.table_names = old_table_names
            del global_apps.get_app_config("migrations").models["author"]
        # And migrate back to clean up the database
        executor.loader.build_graph()
        executor.migrate([("migrations", None)])
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.lookuperror_a",
            "migrations.migrations_test_apps.lookuperror_b",
            "migrations.migrations_test_apps.lookuperror_c"
        ]
    )
    def test_unrelated_model_lookups_forwards(self):
        """
        #24123 - Tests that all models of apps already applied which are
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
            executor.migrate([
                ("lookuperror_a", "0004_a4"),
                ("lookuperror_c", "0003_c3"),
            ])
            self.assertTableExists("lookuperror_a_a4")
            self.assertTableExists("lookuperror_c_c3")

            # Rebuild the graph to reflect the new DB state
            executor.loader.build_graph()
        finally:
            # Cleanup
            executor.migrate([
                ("lookuperror_a", None),
                ("lookuperror_b", None),
                ("lookuperror_c", None),
            ])
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")

    @override_settings(
        INSTALLED_APPS=[
            "migrations.migrations_test_apps.lookuperror_a",
            "migrations.migrations_test_apps.lookuperror_b",
            "migrations.migrations_test_apps.lookuperror_c"
        ]
    )
    def test_unrelated_model_lookups_backwards(self):
        """
        #24123 - Tests that all models of apps being unapplied which are
        unrelated to the first app being unapplied are part of the initial
        model state.
        """
        try:
            executor = MigrationExecutor(connection)
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")
            executor.migrate([
                ("lookuperror_a", "0004_a4"),
                ("lookuperror_b", "0003_b3"),
                ("lookuperror_c", "0003_c3"),
            ])
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
            executor.migrate([
                ("lookuperror_b", None),
                ("lookuperror_c", None)
            ])
            self.assertTableNotExists("lookuperror_a_a1")
            self.assertTableNotExists("lookuperror_b_b1")
            self.assertTableNotExists("lookuperror_c_c1")

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
        executor.migrate([
            ("migrations", "0001_initial"),
            ("migrations", "0002_second"),
        ])
        # Rebuild the graph to reflect the new DB state
        executor.loader.build_graph()

        executor.migrate([
            ("migrations", None),
            ("migrations", None),
        ])
        self.assertTableNotExists("migrations_author")
        self.assertTableNotExists("migrations_tribble")

        migrations = executor.loader.graph.nodes
        expected = [
            ("render_start", ),
            ("render_success", ),
            ("apply_start", migrations['migrations', '0001_initial'], False),
            ("apply_success", migrations['migrations', '0001_initial'], False),
            ("apply_start", migrations['migrations', '0002_second'], False),
            ("apply_success", migrations['migrations', '0002_second'], False),
            ("render_start", ),
            ("render_success", ),
            ("unapply_start", migrations['migrations', '0002_second'], False),
            ("unapply_success", migrations['migrations', '0002_second'], False),
            ("unapply_start", migrations['migrations', '0001_initial'], False),
            ("unapply_success", migrations['migrations', '0001_initial'], False),
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
            executor.migrate([
                ("author_app", "0001_initial"),
                ("book_app", "0001_initial"),
            ])
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

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"})
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

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"})
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


class FakeLoader(object):
    def __init__(self, graph, applied):
        self.graph = graph
        self.applied_migrations = applied


class FakeMigration(object):
    """Really all we need is any object with a debug-useful repr."""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'M<%s>' % self.name


class ExecutorUnitTests(TestCase):
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
        a1_impl = FakeMigration('a1')
        a1 = ('a', '1')
        a2_impl = FakeMigration('a2')
        a2 = ('a', '2')
        b1_impl = FakeMigration('b1')
        b1 = ('b', '1')
        graph = MigrationGraph()
        graph.add_node(a1, a1_impl)
        graph.add_node(a2, a2_impl)
        graph.add_node(b1, b1_impl)
        graph.add_dependency(None, b1, a1)
        graph.add_dependency(None, a2, a1)

        executor = MigrationExecutor(None)
        executor.loader = FakeLoader(graph, {a1, b1, a2})

        plan = executor.migration_plan({a1})

        self.assertEqual(plan, [(a2_impl, True)])

    def test_minimize_rollbacks_branchy(self):
        """
        Minimize rollbacks when target has multiple in-app children.

        a: 1 <---- 3 <--\
              \ \- 2 <--- 4
               \       \
        b:      \- 1 <--- 2
        """
        a1_impl = FakeMigration('a1')
        a1 = ('a', '1')
        a2_impl = FakeMigration('a2')
        a2 = ('a', '2')
        a3_impl = FakeMigration('a3')
        a3 = ('a', '3')
        a4_impl = FakeMigration('a4')
        a4 = ('a', '4')
        b1_impl = FakeMigration('b1')
        b1 = ('b', '1')
        b2_impl = FakeMigration('b2')
        b2 = ('b', '2')
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
        executor.loader = FakeLoader(graph, {a1, b1, a2, b2, a3, a4})

        plan = executor.migration_plan({a1})

        should_be_rolled_back = [b2_impl, a4_impl, a2_impl, a3_impl]
        exp = [(m, True) for m in should_be_rolled_back]
        self.assertEqual(plan, exp)

    def test_backwards_nothing_to_do(self):
        """
        If the current state satisfies the given target, do nothing.

        a: 1 <--- 2
        b:    \- 1
        c:     \- 1

        If a1 is applied already and a2 is not, and we're asked to migrate to
        a1, don't apply or unapply b1 or c1, regardless of their current state.
        """
        a1_impl = FakeMigration('a1')
        a1 = ('a', '1')
        a2_impl = FakeMigration('a2')
        a2 = ('a', '2')
        b1_impl = FakeMigration('b1')
        b1 = ('b', '1')
        c1_impl = FakeMigration('c1')
        c1 = ('c', '1')
        graph = MigrationGraph()
        graph.add_node(a1, a1_impl)
        graph.add_node(a2, a2_impl)
        graph.add_node(b1, b1_impl)
        graph.add_node(c1, c1_impl)
        graph.add_dependency(None, a2, a1)
        graph.add_dependency(None, b1, a1)
        graph.add_dependency(None, c1, a1)

        executor = MigrationExecutor(None)
        executor.loader = FakeLoader(graph, {a1, b1})

        plan = executor.migration_plan({a1})

        self.assertEqual(plan, [])
