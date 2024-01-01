import os
import shutil
import tempfile
from contextlib import contextmanager
from importlib import import_module

from django.apps import apps
from django.db import connection, connections, migrations, models
from django.db.migrations.migration import Migration
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.state import ProjectState
from django.test import TransactionTestCase
from django.test.utils import extend_sys_path
from django.utils.module_loading import module_dir


class MigrationTestBase(TransactionTestCase):
    """
    Contains an extended set of asserts for testing migrations and schema operations.
    """

    available_apps = ["migrations"]
    databases = {"default", "other"}

    def tearDown(self):
        # Reset applied-migrations state.
        for db in self.databases:
            recorder = MigrationRecorder(connections[db])
            recorder.migration_qs.filter(app="migrations").delete()

    def get_table_description(self, table, using="default"):
        with connections[using].cursor() as cursor:
            return connections[using].introspection.get_table_description(cursor, table)

    def assertTableExists(self, table, using="default"):
        with connections[using].cursor() as cursor:
            self.assertIn(table, connections[using].introspection.table_names(cursor))

    def assertTableNotExists(self, table, using="default"):
        with connections[using].cursor() as cursor:
            self.assertNotIn(
                table, connections[using].introspection.table_names(cursor)
            )

    def assertColumnExists(self, table, column, using="default"):
        self.assertIn(
            column, [c.name for c in self.get_table_description(table, using=using)]
        )

    def assertColumnNotExists(self, table, column, using="default"):
        self.assertNotIn(
            column, [c.name for c in self.get_table_description(table, using=using)]
        )

    def _get_column_allows_null(self, table, column, using):
        return [
            c.null_ok
            for c in self.get_table_description(table, using=using)
            if c.name == column
        ][0]

    def assertColumnNull(self, table, column, using="default"):
        self.assertTrue(self._get_column_allows_null(table, column, using))

    def assertColumnNotNull(self, table, column, using="default"):
        self.assertFalse(self._get_column_allows_null(table, column, using))

    def _get_column_collation(self, table, column, using):
        return next(
            f.collation
            for f in self.get_table_description(table, using=using)
            if f.name == column
        )

    def assertColumnCollation(self, table, column, collation, using="default"):
        self.assertEqual(self._get_column_collation(table, column, using), collation)

    def _get_table_comment(self, table, using):
        with connections[using].cursor() as cursor:
            return next(
                t.comment
                for t in connections[using].introspection.get_table_list(cursor)
                if t.name == table
            )

    def assertTableComment(self, table, comment, using="default"):
        self.assertEqual(self._get_table_comment(table, using), comment)

    def assertTableCommentNotExists(self, table, using="default"):
        self.assertIn(self._get_table_comment(table, using), [None, ""])

    def assertIndexExists(
        self, table, columns, value=True, using="default", index_type=None
    ):
        with connections[using].cursor() as cursor:
            self.assertEqual(
                value,
                any(
                    c["index"]
                    for c in connections[using]
                    .introspection.get_constraints(cursor, table)
                    .values()
                    if (
                        c["columns"] == list(columns)
                        and (index_type is None or c["type"] == index_type)
                        and not c["unique"]
                    )
                ),
            )

    def assertIndexNotExists(self, table, columns):
        return self.assertIndexExists(table, columns, False)

    def assertIndexNameExists(self, table, index, using="default"):
        with connections[using].cursor() as cursor:
            self.assertIn(
                index,
                connection.introspection.get_constraints(cursor, table),
            )

    def assertIndexNameNotExists(self, table, index, using="default"):
        with connections[using].cursor() as cursor:
            self.assertNotIn(
                index,
                connection.introspection.get_constraints(cursor, table),
            )

    def assertConstraintExists(self, table, name, value=True, using="default"):
        with connections[using].cursor() as cursor:
            constraints = (
                connections[using].introspection.get_constraints(cursor, table).items()
            )
            self.assertEqual(
                value,
                any(c["check"] for n, c in constraints if n == name),
            )

    def assertConstraintNotExists(self, table, name):
        return self.assertConstraintExists(table, name, False)

    def assertUniqueConstraintExists(self, table, columns, value=True, using="default"):
        with connections[using].cursor() as cursor:
            constraints = (
                connections[using].introspection.get_constraints(cursor, table).values()
            )
            self.assertEqual(
                value,
                any(c["unique"] for c in constraints if c["columns"] == list(columns)),
            )

    def assertFKExists(self, table, columns, to, value=True, using="default"):
        if not connections[using].features.can_introspect_foreign_keys:
            return
        with connections[using].cursor() as cursor:
            self.assertEqual(
                value,
                any(
                    c["foreign_key"] == to
                    for c in connections[using]
                    .introspection.get_constraints(cursor, table)
                    .values()
                    if c["columns"] == list(columns)
                ),
            )

    def assertFKNotExists(self, table, columns, to):
        return self.assertFKExists(table, columns, to, False)

    @contextmanager
    def temporary_migration_module(self, app_label="migrations", module=None):
        """
        Allows testing management commands in a temporary migrations module.

        Wrap all invocations to makemigrations and squashmigrations with this
        context manager in order to avoid creating migration files in your
        source tree inadvertently.

        Takes the application label that will be passed to makemigrations or
        squashmigrations and the Python path to a migrations module.

        The migrations module is used as a template for creating the temporary
        migrations module. If it isn't provided, the application's migrations
        module is used, if it exists.

        Returns the filesystem path to the temporary migrations module.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            target_dir = tempfile.mkdtemp(dir=temp_dir)
            with open(os.path.join(target_dir, "__init__.py"), "w"):
                pass
            target_migrations_dir = os.path.join(target_dir, "migrations")

            if module is None:
                module = apps.get_app_config(app_label).name + ".migrations"

            try:
                source_migrations_dir = module_dir(import_module(module))
            except (ImportError, ValueError):
                pass
            else:
                shutil.copytree(source_migrations_dir, target_migrations_dir)

            with extend_sys_path(temp_dir):
                new_module = os.path.basename(target_dir) + ".migrations"
                with self.settings(MIGRATION_MODULES={app_label: new_module}):
                    yield target_migrations_dir


class OperationTestBase(MigrationTestBase):
    """Common functions to help test operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._initial_table_names = frozenset(connection.introspection.table_names())

    def tearDown(self):
        self.cleanup_test_tables()
        super().tearDown()

    def cleanup_test_tables(self):
        table_names = (
            frozenset(connection.introspection.table_names())
            - self._initial_table_names
        )
        with connection.schema_editor() as editor:
            with connection.constraint_checks_disabled():
                for table_name in table_names:
                    editor.execute(
                        editor.sql_delete_table
                        % {
                            "table": editor.quote_name(table_name),
                        }
                    )

    def apply_operations(self, app_label, project_state, operations, atomic=True):
        migration = Migration("name", app_label)
        migration.operations = operations
        with connection.schema_editor(atomic=atomic) as editor:
            return migration.apply(project_state, editor)

    def unapply_operations(self, app_label, project_state, operations, atomic=True):
        migration = Migration("name", app_label)
        migration.operations = operations
        with connection.schema_editor(atomic=atomic) as editor:
            return migration.unapply(project_state, editor)

    def make_test_state(self, app_label, operation, **kwargs):
        """
        Makes a test state using set_up_test_model and returns the
        original state and the state after the migration is applied.
        """
        project_state = self.set_up_test_model(app_label, **kwargs)
        new_state = project_state.clone()
        operation.state_forwards(app_label, new_state)
        return project_state, new_state

    def set_up_test_model(
        self,
        app_label,
        second_model=False,
        third_model=False,
        index=False,
        multicol_index=False,
        related_model=False,
        mti_model=False,
        proxy_model=False,
        manager_model=False,
        unique_together=False,
        options=False,
        db_table=None,
        constraints=None,
        indexes=None,
    ):
        """Creates a test model state and database table."""
        # Make the "current" state.
        model_options = {
            "swappable": "TEST_SWAP_MODEL",
            "unique_together": [["pink", "weight"]] if unique_together else [],
        }
        if options:
            model_options["permissions"] = [("can_groom", "Can groom")]
        if db_table:
            model_options["db_table"] = db_table
        operations = [
            migrations.CreateModel(
                "Pony",
                [
                    ("id", models.AutoField(primary_key=True)),
                    ("pink", models.IntegerField(default=3)),
                    ("weight", models.FloatField()),
                    ("green", models.IntegerField(null=True)),
                    (
                        "yellow",
                        models.CharField(
                            blank=True, null=True, db_default="Yellow", max_length=20
                        ),
                    ),
                ],
                options=model_options,
            )
        ]
        if index:
            operations.append(
                migrations.AddIndex(
                    "Pony",
                    models.Index(fields=["pink"], name="pony_pink_idx"),
                )
            )
        if multicol_index:
            operations.append(
                migrations.AddIndex(
                    "Pony",
                    models.Index(fields=["pink", "weight"], name="pony_test_idx"),
                )
            )
        if indexes:
            for index in indexes:
                operations.append(migrations.AddIndex("Pony", index))
        if constraints:
            for constraint in constraints:
                operations.append(migrations.AddConstraint("Pony", constraint))
        if second_model:
            operations.append(
                migrations.CreateModel(
                    "Stable",
                    [
                        ("id", models.AutoField(primary_key=True)),
                    ],
                )
            )
        if third_model:
            operations.append(
                migrations.CreateModel(
                    "Van",
                    [
                        ("id", models.AutoField(primary_key=True)),
                    ],
                )
            )
        if related_model:
            operations.append(
                migrations.CreateModel(
                    "Rider",
                    [
                        ("id", models.AutoField(primary_key=True)),
                        ("pony", models.ForeignKey("Pony", models.CASCADE)),
                        (
                            "friend",
                            models.ForeignKey("self", models.CASCADE, null=True),
                        ),
                    ],
                )
            )
        if mti_model:
            operations.append(
                migrations.CreateModel(
                    "ShetlandPony",
                    fields=[
                        (
                            "pony_ptr",
                            models.OneToOneField(
                                "Pony",
                                models.CASCADE,
                                auto_created=True,
                                parent_link=True,
                                primary_key=True,
                                to_field="id",
                                serialize=False,
                            ),
                        ),
                        ("cuteness", models.IntegerField(default=1)),
                    ],
                    bases=["%s.Pony" % app_label],
                )
            )
        if proxy_model:
            operations.append(
                migrations.CreateModel(
                    "ProxyPony",
                    fields=[],
                    options={"proxy": True},
                    bases=["%s.Pony" % app_label],
                )
            )
        if manager_model:
            from .models import FoodManager, FoodQuerySet

            operations.append(
                migrations.CreateModel(
                    "Food",
                    fields=[
                        ("id", models.AutoField(primary_key=True)),
                    ],
                    managers=[
                        ("food_qs", FoodQuerySet.as_manager()),
                        ("food_mgr", FoodManager("a", "b")),
                        ("food_mgr_kwargs", FoodManager("x", "y", 3, 4)),
                    ],
                )
            )
        return self.apply_operations(app_label, ProjectState(), operations)
