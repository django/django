from django.db import connection, connections
from django.db.migrations.exceptions import (
    AmbiguityError, InconsistentMigrationHistory, NodeNotFoundError,
)
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase, modify_settings, override_settings


class RecorderTests(TestCase):
    """
    Tests recording migrations as applied or not.
    """
    multi_db = True

    def test_apply(self):
        """
        Tests marking migrations as applied/unapplied.
        """
        recorder = MigrationRecorder(connection)
        self.assertEqual(
            set((x, y) for (x, y) in recorder.applied_migrations() if x == "myapp"),
            set(),
        )
        recorder.record_applied("myapp", "0432_ponies")
        self.assertEqual(
            set((x, y) for (x, y) in recorder.applied_migrations() if x == "myapp"),
            {("myapp", "0432_ponies")},
        )
        # That should not affect records of another database
        recorder_other = MigrationRecorder(connections['other'])
        self.assertEqual(
            set((x, y) for (x, y) in recorder_other.applied_migrations() if x == "myapp"),
            set(),
        )
        recorder.record_unapplied("myapp", "0432_ponies")
        self.assertEqual(
            set((x, y) for (x, y) in recorder.applied_migrations() if x == "myapp"),
            set(),
        )


class LoaderTests(TestCase):
    """
    Tests the disk and database loader, and running through migrations
    in memory.
    """

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    @modify_settings(INSTALLED_APPS={'append': 'basic'})
    def test_load(self):
        """
        Makes sure the loader can load the migrations for the test apps,
        and then render them out to a new Apps.
        """
        # Load and test the plan
        migration_loader = MigrationLoader(connection)
        self.assertEqual(
            migration_loader.graph.forwards_plan(("migrations", "0002_second")),
            [
                ("migrations", "0001_initial"),
                ("migrations", "0002_second"),
            ],
        )
        # Now render it out!
        project_state = migration_loader.project_state(("migrations", "0002_second"))
        self.assertEqual(len(project_state.models), 2)

        author_state = project_state.models["migrations", "author"]
        self.assertEqual(
            [x for x, y in author_state.fields],
            ["id", "name", "slug", "age", "rating"]
        )

        book_state = project_state.models["migrations", "book"]
        self.assertEqual(
            [x for x, y in book_state.fields],
            ["id", "author"]
        )

        # Ensure we've included unmigrated apps in there too
        self.assertIn("basic", project_state.real_apps)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_unmigdep"})
    def test_load_unmigrated_dependency(self):
        """
        Makes sure the loader can load migrations with a dependency on an unmigrated app.
        """
        # Load and test the plan
        migration_loader = MigrationLoader(connection)
        self.assertEqual(
            migration_loader.graph.forwards_plan(("migrations", "0001_initial")),
            [
                ('contenttypes', '0001_initial'),
                ('auth', '0001_initial'),
                ("migrations", "0001_initial"),
            ],
        )
        # Now render it out!
        project_state = migration_loader.project_state(("migrations", "0001_initial"))
        self.assertEqual(len([m for a, m in project_state.models if a == "migrations"]), 1)

        book_state = project_state.models["migrations", "book"]
        self.assertEqual(
            [x for x, y in book_state.fields],
            ["id", "user"]
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_run_before"})
    def test_run_before(self):
        """
        Makes sure the loader uses Migration.run_before.
        """
        # Load and test the plan
        migration_loader = MigrationLoader(connection)
        self.assertEqual(
            migration_loader.graph.forwards_plan(("migrations", "0002_second")),
            [
                ("migrations", "0001_initial"),
                ("migrations", "0003_third"),
                ("migrations", "0002_second"),
            ],
        )

    @override_settings(MIGRATION_MODULES={
        "migrations": "migrations.test_migrations_first",
        "migrations2": "migrations2.test_migrations_2_first",
    })
    @modify_settings(INSTALLED_APPS={'append': 'migrations2'})
    def test_first(self):
        """
        Makes sure the '__first__' migrations build correctly.
        """
        migration_loader = MigrationLoader(connection)
        self.assertEqual(
            migration_loader.graph.forwards_plan(("migrations", "second")),
            [
                ("migrations", "thefirst"),
                ("migrations2", "0001_initial"),
                ("migrations2", "0002_second"),
                ("migrations", "second"),
            ],
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
    def test_name_match(self):
        "Tests prefix name matching"
        migration_loader = MigrationLoader(connection)
        self.assertEqual(
            migration_loader.get_migration_by_prefix("migrations", "0001").name,
            "0001_initial",
        )
        with self.assertRaises(AmbiguityError):
            migration_loader.get_migration_by_prefix("migrations", "0")
        with self.assertRaises(KeyError):
            migration_loader.get_migration_by_prefix("migrations", "blarg")

    def test_load_import_error(self):
        with override_settings(MIGRATION_MODULES={"migrations": "import_error_package"}):
            with self.assertRaises(ImportError):
                MigrationLoader(connection)

    def test_load_module_file(self):
        with override_settings(MIGRATION_MODULES={"migrations": "migrations.faulty_migrations.file"}):
            loader = MigrationLoader(connection)
            self.assertIn(
                "migrations", loader.unmigrated_apps,
                "App with migrations module file not in unmigrated apps."
            )

    def test_load_empty_dir(self):
        with override_settings(MIGRATION_MODULES={"migrations": "migrations.faulty_migrations.namespace"}):
            loader = MigrationLoader(connection)
            self.assertIn(
                "migrations", loader.unmigrated_apps,
                "App missing __init__.py in migrations module not in unmigrated apps."
            )

    @override_settings(
        INSTALLED_APPS=['migrations.migrations_test_apps.migrated_app'],
    )
    def test_marked_as_migrated(self):
        """
        Undefined MIGRATION_MODULES implies default migration module.
        """
        migration_loader = MigrationLoader(connection)
        self.assertEqual(migration_loader.migrated_apps, {'migrated_app'})
        self.assertEqual(migration_loader.unmigrated_apps, set())

    @override_settings(
        INSTALLED_APPS=['migrations.migrations_test_apps.migrated_app'],
        MIGRATION_MODULES={"migrated_app": None},
    )
    def test_marked_as_unmigrated(self):
        """
        MIGRATION_MODULES allows disabling of migrations for a particular app.
        """
        migration_loader = MigrationLoader(connection)
        self.assertEqual(migration_loader.migrated_apps, set())
        self.assertEqual(migration_loader.unmigrated_apps, {'migrated_app'})

    @override_settings(
        INSTALLED_APPS=['migrations.migrations_test_apps.migrated_app'],
        MIGRATION_MODULES={'migrated_app': 'missing-module'},
    )
    def test_explicit_missing_module(self):
        """
        If a MIGRATION_MODULES override points to a missing module, the error
        raised during the importation attempt should be propagated unless
        `ignore_no_migrations=True`.
        """
        with self.assertRaisesMessage(ImportError, 'missing-module'):
            migration_loader = MigrationLoader(connection)
        migration_loader = MigrationLoader(connection, ignore_no_migrations=True)
        self.assertEqual(migration_loader.migrated_apps, set())
        self.assertEqual(migration_loader.unmigrated_apps, {'migrated_app'})

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"})
    def test_loading_squashed(self):
        "Tests loading a squashed migration"
        migration_loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        self.addCleanup(recorder.flush)
        # Loading with nothing applied should just give us the one node
        self.assertEqual(
            len([x for x in migration_loader.graph.nodes if x[0] == "migrations"]),
            1,
        )
        # However, fake-apply one migration and it should now use the old two
        recorder.record_applied("migrations", "0001_initial")
        migration_loader.build_graph()
        self.assertEqual(
            len([x for x in migration_loader.graph.nodes if x[0] == "migrations"]),
            2,
        )

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed_complex"})
    def test_loading_squashed_complex(self):
        "Tests loading a complex set of squashed migrations"

        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        self.addCleanup(recorder.flush)

        def num_nodes():
            plan = set(loader.graph.forwards_plan(('migrations', '7_auto')))
            return len(plan - loader.applied_migrations)

        # Empty database: use squashed migration
        loader.build_graph()
        self.assertEqual(num_nodes(), 5)

        # Starting at 1 or 2 should use the squashed migration too
        recorder.record_applied("migrations", "1_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 4)

        recorder.record_applied("migrations", "2_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 3)

        # However, starting at 3 to 5 cannot use the squashed migration
        recorder.record_applied("migrations", "3_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 4)

        recorder.record_applied("migrations", "4_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 3)

        # Starting at 5 to 7 we are passed the squashed migrations
        recorder.record_applied("migrations", "5_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 2)

        recorder.record_applied("migrations", "6_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 1)

        recorder.record_applied("migrations", "7_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 0)

    @override_settings(MIGRATION_MODULES={
        "app1": "migrations.test_migrations_squashed_complex_multi_apps.app1",
        "app2": "migrations.test_migrations_squashed_complex_multi_apps.app2",
    })
    @modify_settings(INSTALLED_APPS={'append': [
        "migrations.test_migrations_squashed_complex_multi_apps.app1",
        "migrations.test_migrations_squashed_complex_multi_apps.app2",
    ]})
    def test_loading_squashed_complex_multi_apps(self):
        loader = MigrationLoader(connection)
        loader.build_graph()

        plan = set(loader.graph.forwards_plan(('app1', '4_auto')))
        expected_plan = {
            ('app1', '1_auto'),
            ('app2', '1_squashed_2'),
            ('app1', '2_squashed_3'),
            ('app1', '4_auto'),
        }
        self.assertEqual(plan, expected_plan)

    @override_settings(MIGRATION_MODULES={
        "app1": "migrations.test_migrations_squashed_complex_multi_apps.app1",
        "app2": "migrations.test_migrations_squashed_complex_multi_apps.app2",
    })
    @modify_settings(INSTALLED_APPS={'append': [
        "migrations.test_migrations_squashed_complex_multi_apps.app1",
        "migrations.test_migrations_squashed_complex_multi_apps.app2",
    ]})
    def test_loading_squashed_complex_multi_apps_partially_applied(self):
        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        recorder.record_applied('app1', '1_auto')
        recorder.record_applied('app1', '2_auto')
        loader.build_graph()

        plan = set(loader.graph.forwards_plan(('app1', '4_auto')))
        plan = plan - loader.applied_migrations
        expected_plan = {
            ('app2', '1_squashed_2'),
            ('app1', '3_auto'),
            ('app1', '4_auto'),
        }

        self.assertEqual(plan, expected_plan)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed_erroneous"})
    def test_loading_squashed_erroneous(self):
        "Tests loading a complex but erroneous set of squashed migrations"

        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        self.addCleanup(recorder.flush)

        def num_nodes():
            plan = set(loader.graph.forwards_plan(('migrations', '7_auto')))
            return len(plan - loader.applied_migrations)

        # Empty database: use squashed migration
        loader.build_graph()
        self.assertEqual(num_nodes(), 5)

        # Starting at 1 or 2 should use the squashed migration too
        recorder.record_applied("migrations", "1_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 4)

        recorder.record_applied("migrations", "2_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 3)

        # However, starting at 3 or 4, nonexistent migrations would be needed.
        msg = ("Migration migrations.6_auto depends on nonexistent node ('migrations', '5_auto'). "
               "Django tried to replace migration migrations.5_auto with any of "
               "[migrations.3_squashed_5] but wasn't able to because some of the replaced "
               "migrations are already applied.")

        recorder.record_applied("migrations", "3_auto")
        with self.assertRaisesMessage(NodeNotFoundError, msg):
            loader.build_graph()

        recorder.record_applied("migrations", "4_auto")
        with self.assertRaisesMessage(NodeNotFoundError, msg):
            loader.build_graph()

        # Starting at 5 to 7 we are passed the squashed migrations
        recorder.record_applied("migrations", "5_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 2)

        recorder.record_applied("migrations", "6_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 1)

        recorder.record_applied("migrations", "7_auto")
        loader.build_graph()
        self.assertEqual(num_nodes(), 0)

    @override_settings(
        MIGRATION_MODULES={'migrations': 'migrations.test_migrations'},
        INSTALLED_APPS=['migrations'],
    )
    def test_check_consistent_history(self):
        loader = MigrationLoader(connection=None)
        loader.check_consistent_history(connection)
        recorder = MigrationRecorder(connection)
        recorder.record_applied('migrations', '0002_second')
        msg = (
            "Migration migrations.0002_second is applied before its dependency "
            "migrations.0001_initial on database 'default'."
        )
        with self.assertRaisesMessage(InconsistentMigrationHistory, msg):
            loader.check_consistent_history(connection)

    @override_settings(
        MIGRATION_MODULES={'migrations': 'migrations.test_migrations_squashed_extra'},
        INSTALLED_APPS=['migrations'],
    )
    def test_check_consistent_history_squashed(self):
        """
        MigrationLoader.check_consistent_history() should ignore unapplied
        squashed migrations that have all of their `replaces` applied.
        """
        loader = MigrationLoader(connection=None)
        recorder = MigrationRecorder(connection)
        recorder.record_applied('migrations', '0001_initial')
        recorder.record_applied('migrations', '0002_second')
        loader.check_consistent_history(connection)
        recorder.record_applied('migrations', '0003_third')
        loader.check_consistent_history(connection)

    @override_settings(MIGRATION_MODULES={
        "app1": "migrations.test_migrations_squashed_ref_squashed.app1",
        "app2": "migrations.test_migrations_squashed_ref_squashed.app2",
    })
    @modify_settings(INSTALLED_APPS={'append': [
        "migrations.test_migrations_squashed_ref_squashed.app1",
        "migrations.test_migrations_squashed_ref_squashed.app2",
    ]})
    def test_loading_squashed_ref_squashed(self):
        "Tests loading a squashed migration with a new migration referencing it"
        r"""
        The sample migrations are structured like this:

        app_1       1 --> 2 ---------------------*--> 3        *--> 4
                     \                          /             /
                      *-------------------*----/--> 2_sq_3 --*
                       \                 /    /
        =============== \ ============= / == / ======================
        app_2            *--> 1_sq_2 --*    /
                          \                /
                           *--> 1 --> 2 --*

        Where 2_sq_3 is a replacing migration for 2 and 3 in app_1,
        as 1_sq_2 is a replacing migration for 1 and 2 in app_2.
        """

        loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        self.addCleanup(recorder.flush)

        # Load with nothing applied: both migrations squashed.
        loader.build_graph()
        plan = set(loader.graph.forwards_plan(('app1', '4_auto')))
        plan = plan - loader.applied_migrations
        expected_plan = {
            ('app1', '1_auto'),
            ('app2', '1_squashed_2'),
            ('app1', '2_squashed_3'),
            ('app1', '4_auto'),
        }
        self.assertEqual(plan, expected_plan)

        # Fake-apply a few from app1: unsquashes migration in app1.
        recorder.record_applied('app1', '1_auto')
        recorder.record_applied('app1', '2_auto')
        loader.build_graph()
        plan = set(loader.graph.forwards_plan(('app1', '4_auto')))
        plan = plan - loader.applied_migrations
        expected_plan = {
            ('app2', '1_squashed_2'),
            ('app1', '3_auto'),
            ('app1', '4_auto'),
        }
        self.assertEqual(plan, expected_plan)

        # Fake-apply one from app2: unsquashes migration in app2 too.
        recorder.record_applied('app2', '1_auto')
        loader.build_graph()
        plan = set(loader.graph.forwards_plan(('app1', '4_auto')))
        plan = plan - loader.applied_migrations
        expected_plan = {
            ('app2', '2_auto'),
            ('app1', '3_auto'),
            ('app1', '4_auto'),
        }
        self.assertEqual(plan, expected_plan)
