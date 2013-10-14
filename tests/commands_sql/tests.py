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
    def count_ddl(self, output, cmd):
        return len([o for o in output if o.startswith(cmd)])

    def test_sql_create(self):
        app = models.get_app('commands_sql')
        output = sql_create(app, no_style(), connections[DEFAULT_DB_ALIAS])
        create_tables = [o for o in output if o.startswith('CREATE TABLE')]
        self.assertEqual(len(create_tables), 3)
        # Lower so that Oracle's upper case tbl names wont break
        sql = create_tables[-1].lower()
        six.assertRegex(self, sql, r'^create table .commands_sql_book.*')

    def test_sql_delete(self):
        app = models.get_app('commands_sql')
        output = sql_delete(app, no_style(), connections[DEFAULT_DB_ALIAS])
        drop_tables = [o for o in output if o.startswith('DROP TABLE')]
        self.assertEqual(len(drop_tables), 3)
        # Lower so that Oracle's upper case tbl names wont break
        sql = drop_tables[-1].lower()
        six.assertRegex(self, sql, r'^drop table .commands_sql_comment.*')

    def test_sql_indexes(self):
        app = models.get_app('commands_sql')
        output = sql_indexes(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # PostgreSQL creates one additional index for CharField
        self.assertIn(self.count_ddl(output, 'CREATE INDEX'), [3, 4])

    def test_sql_destroy_indexes(self):
        app = models.get_app('commands_sql')
        output = sql_destroy_indexes(app, no_style(), connections[DEFAULT_DB_ALIAS])
        # PostgreSQL creates one additional index for CharField
        self.assertIn(self.count_ddl(output, 'DROP INDEX'), [3, 4])

    def test_sql_all(self):
        app = models.get_app('commands_sql')
        output = sql_all(app, no_style(), connections[DEFAULT_DB_ALIAS])

        self.assertEqual(self.count_ddl(output, 'CREATE TABLE'), 3)
        # PostgreSQL creates one additional index for CharField
        self.assertIn(self.count_ddl(output, 'CREATE INDEX'), [3, 4])
