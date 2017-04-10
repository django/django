import unittest
from django.db import connection
from django.test import TestCase


class LoggingCursorMixin:
    def __init__(self, bucket, *args, **kwargs):
        super().__init__(bucket, *args, **kwargs)
        self.bucket = bucket

    def execute(self, sql, *args, **kwargs):
        self.bucket.append(sql)
        super().execute(sql, *args, **kwargs)


@unittest.skipUnless(connection.vendor == 'mysql', 'MySQL specific test.')
class MySQLCursorOptionsTestCase(TestCase):
    try:
        from MySQLdb.cursors import Cursor

        class MySQLLoggingCursor(LoggingCursorMixin, Cursor):
            pass
    except ImportError:
        pass


@unittest.skipUnless(connection.vendor == 'postgresql', 'Postgresql specific test.')
class PostgreSQLCursorOptionsTestCase(TestCase):
    try:
        from psycopg2.extensions import cursor

        class PostgresLoggingCursor(LoggingCursorMixin, cursor):
            pass
    except ImportError:
        pass


@unittest.skipUnless(connection.vendor == 'sqlite', 'SQLite specific test.')
class SQLiteCursorOptionsTestCase(TestCase):
    try:
        from django.db.backends.sqlite3.base import SQLiteCursorWrapper

        class SQLiteLoggingCursor(LoggingCursorMixin, SQLiteCursorWrapper):
            pass

    except ImportError:
        pass
