from __future__ import unicode_literals

from django.core.management.color import no_style
from django.core.management.sql import (sql_create, sql_delete, sql_indexes,
    sql_destroy_indexes, sql_all)
from django.db import connections, DEFAULT_DB_ALIAS, models
from django.test import TestCase
from django.utils import six

# See also initial_sql_regress for 'custom_sql_for_model' tests


class SQLCommandsTestCase(TestCase):
    """Tests for several functions in django/core/management/sql.py"""
    def test_sql_create(self):
        app = models.get_app('commands_sql')
        output = sql_create(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # Lower so that Oracle's upper case tbl names wont break
        sql = output[0].lower()
        six.assertRegex(self, sql, r'^create table .commands_sql_book.*')

    def test_sql_delete(self):
        app = models.get_app('commands_sql')
        output = sql_delete(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # Oracle produces DROP SEQUENCE and DROP TABLE for this command.
        if connections[DEFAULT_DB_ALIAS].vendor == 'oracle':
            sql = output[1].lower()
        else:
            sql = output[0].lower()
        six.assertRegex(self, sql, r'^drop table .commands_sql_book.*')

    def test_sql_indexes(self):
        app = models.get_app('commands_sql')
        output = sql_indexes(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # PostgreSQL creates two indexes
        self.assertIn(len(output), [1, 2])
        self.assertTrue(output[0].startswith("CREATE INDEX"))

    def test_sql_destroy_indexes(self):
        app = models.get_app('commands_sql')
        output = sql_destroy_indexes(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # PostgreSQL creates two indexes
        self.assertIn(len(output), [1, 2])
        self.assertTrue(output[0].startswith("DROP INDEX"))

    def test_sql_all(self):
        app = models.get_app('commands_sql')
        output = sql_all(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # PostgreSQL creates two indexes
        self.assertIn(len(output), [2, 3])
        self.assertTrue(output[0].startswith('CREATE TABLE'))
        self.assertTrue(output[1].startswith('CREATE INDEX'))
