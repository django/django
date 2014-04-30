from unittest import skipIf

from django.test import TestCase, override_settings
from django.db import connection, connections
from django.db.migrations.loader import MigrationLoader, AmbiguityError
from django.db.migrations.recorder import MigrationRecorder
from django.utils import six


class RecorderTests(TestCase):
    """
    Tests recording migrations as applied or not.
    """

    def test_apply(self):
        """
        Tests marking migrations as applied/unapplied.
        """
        recorder = MigrationRecorder(connection)
        self.assertEqual(
            recorder.applied_migrations(),
            set(),
        )
        recorder.record_applied("myapp", "0432_ponies")
        self.assertEqual(
            recorder.applied_migrations(),
            set([("myapp", "0432_ponies")]),
        )
        # That should not affect records of another database
        recorder_other = MigrationRecorder(connections['other'])
        self.assertEqual(
            recorder_other.applied_migrations(),
            set(),
        )
        recorder.record_unapplied("myapp", "0432_ponies")
        self.assertEqual(
            recorder.applied_migrations(),
            set(),
        )


class LoaderTests(TestCase):
    """
    Tests the disk and database loader, and running through migrations
    in memory.
    """

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations"})
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
        self.assertIn("contenttypes", project_state.real_apps)

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
        with override_settings(MIGRATION_MODULES={"migrations": "migrations.faulty_migrations.import_error"}):
            with self.assertRaises(ImportError):
                MigrationLoader(connection)

    def test_load_module_file(self):
        with override_settings(MIGRATION_MODULES={"migrations": "migrations.faulty_migrations.file"}):
            MigrationLoader(connection)

    @skipIf(six.PY2, "PY2 doesn't load empty dirs.")
    def test_load_empty_dir(self):
        with override_settings(MIGRATION_MODULES={"migrations": "migrations.faulty_migrations.namespace"}):
            MigrationLoader(connection)

    @override_settings(MIGRATION_MODULES={"migrations": "migrations.test_migrations_squashed"})
    def test_loading_squashed(self):
        "Tests loading a squashed migration"
        migration_loader = MigrationLoader(connection)
        recorder = MigrationRecorder(connection)
        # Loading with nothing applied should just give us the one node
        self.assertEqual(
            len(migration_loader.graph.nodes),
            1,
        )
        # However, fake-apply one migration and it should now use the old two
        recorder.record_applied("migrations", "0001_initial")
        migration_loader.build_graph()
        self.assertEqual(
            len(migration_loader.graph.nodes),
            2,
        )
        recorder.flush()
