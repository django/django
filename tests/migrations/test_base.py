import os
import shutil
import tempfile
from contextlib import contextmanager
from importlib import import_module

from django.apps import apps
from django.db import connections
from django.db.migrations.recorder import MigrationRecorder
from django.test import TransactionTestCase
from django.test.utils import extend_sys_path
from django.utils.module_loading import module_dir


class MigrationTestBase(TransactionTestCase):
    """
    Contains an extended set of asserts for testing migrations and schema operations.
    """

    available_apps = ["migrations"]

    def tearDown(self):
        # Reset applied-migrations state.
        for db in connections:
            recorder = MigrationRecorder(connections[db])
            recorder.migration_qs.filter(app='migrations').delete()

    def get_table_description(self, table, using='default'):
        with connections[using].cursor() as cursor:
            return connections[using].introspection.get_table_description(cursor, table)

    def assertTableExists(self, table, using='default'):
        with connections[using].cursor() as cursor:
            self.assertIn(table, connections[using].introspection.table_names(cursor))

    def assertTableNotExists(self, table, using='default'):
        with connections[using].cursor() as cursor:
            self.assertNotIn(table, connections[using].introspection.table_names(cursor))

    def assertColumnExists(self, table, column, using='default'):
        self.assertIn(column, [c.name for c in self.get_table_description(table, using=using)])

    def assertColumnNotExists(self, table, column, using='default'):
        self.assertNotIn(column, [c.name for c in self.get_table_description(table, using=using)])

    def _get_column_allows_null(self, table, column, using):
        return [c.null_ok for c in self.get_table_description(table, using=using) if c.name == column][0]

    def assertColumnNull(self, table, column, using='default'):
        self.assertEqual(self._get_column_allows_null(table, column, using), True)

    def assertColumnNotNull(self, table, column, using='default'):
        self.assertEqual(self._get_column_allows_null(table, column, using), False)

    def assertIndexExists(self, table, columns, value=True, using='default'):
        with connections[using].cursor() as cursor:
            self.assertEqual(
                value,
                any(
                    c["index"]
                    for c in connections[using].introspection.get_constraints(cursor, table).values()
                    if c['columns'] == list(columns)
                ),
            )

    def assertIndexNotExists(self, table, columns):
        return self.assertIndexExists(table, columns, False)

    def assertFKExists(self, table, columns, to, value=True, using='default'):
        with connections[using].cursor() as cursor:
            self.assertEqual(
                value,
                any(
                    c["foreign_key"] == to
                    for c in connections[using].introspection.get_constraints(cursor, table).values()
                    if c['columns'] == list(columns)
                ),
            )

    def assertFKNotExists(self, table, columns, to):
        return self.assertFKExists(table, columns, to, False)

    @contextmanager
    def temporary_migration_module(self, app_label='migrations', module=None):
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
        temp_dir = tempfile.mkdtemp()
        try:
            target_dir = tempfile.mkdtemp(dir=temp_dir)
            with open(os.path.join(target_dir, '__init__.py'), 'w'):
                pass
            target_migrations_dir = os.path.join(target_dir, 'migrations')

            if module is None:
                module = apps.get_app_config(app_label).name + '.migrations'

            try:
                source_migrations_dir = module_dir(import_module(module))
            except (ImportError, ValueError):
                pass
            else:
                shutil.copytree(source_migrations_dir, target_migrations_dir)

            with extend_sys_path(temp_dir):
                new_module = os.path.basename(target_dir) + '.migrations'
                with self.settings(MIGRATION_MODULES={app_label: new_module}):
                    yield target_migrations_dir

        finally:
            shutil.rmtree(temp_dir)
