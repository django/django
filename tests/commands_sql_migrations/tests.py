from __future__ import unicode_literals

from django.apps import apps
from django.core.management import CommandError
from django.core.management.color import no_style
from django.core.management.sql import (
    sql_all, sql_create, sql_delete, sql_destroy_indexes, sql_indexes,
)
from django.db import DEFAULT_DB_ALIAS, connections
from django.test import TestCase


class SQLCommandsMigrationsTestCase(TestCase):
    """Tests that apps with migrations can not use sql commands."""

    def test_sql_create(self):
        app_config = apps.get_app_config('commands_sql_migrations')
        with self.assertRaises(CommandError):
            sql_create(app_config, no_style(), connections[DEFAULT_DB_ALIAS])

    def test_sql_delete(self):
        app_config = apps.get_app_config('commands_sql_migrations')
        with self.assertRaises(CommandError):
            sql_delete(app_config, no_style(), connections[DEFAULT_DB_ALIAS], close_connection=False)

    def test_sql_indexes(self):
        app_config = apps.get_app_config('commands_sql_migrations')
        with self.assertRaises(CommandError):
            sql_indexes(app_config, no_style(), connections[DEFAULT_DB_ALIAS])

    def test_sql_destroy_indexes(self):
        app_config = apps.get_app_config('commands_sql_migrations')
        with self.assertRaises(CommandError):
            sql_destroy_indexes(app_config, no_style(),
                                connections[DEFAULT_DB_ALIAS])

    def test_sql_all(self):
        app_config = apps.get_app_config('commands_sql_migrations')
        with self.assertRaises(CommandError):
            sql_all(app_config, no_style(), connections[DEFAULT_DB_ALIAS])
