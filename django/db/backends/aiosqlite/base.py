"""
SQLite backend for the sqlite3 module in the standard library.
"""
import decimal
from itertools import chain
from sqlite3 import dbapi2

import aiosqlite as Database
from aiosqlite.context import contextmanager as aiosqlite_contextmanager

from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError
from django.db.backends.base.base import BaseAsyncDatabaseWrapper
from django.db.backends.sqlite3.base import (
    FORMAT_QMARK_REGEX, DatabaseWrapper as SQLiteDatabaseWrapper, decoder,
)
from django.utils.dateparse import parse_datetime, parse_time

from ._functions import register as register_functions
from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations


def check_sqlite_version():
    if Database.sqlite_version_info < (3, 9, 0):
        raise ImproperlyConfigured(
            'SQLite 3.9.0 or later is required (found %s).' % Database.sqlite_version
        )


check_sqlite_version()

Database.register_converter("bool", b'1'.__eq__)
Database.register_converter("time", decoder(parse_time))
Database.register_converter("datetime", decoder(parse_datetime))
Database.register_converter("timestamp", decoder(parse_datetime))

Database.register_adapter(decimal.Decimal, str)


def setup():
    for exc in [
        "DataError",
        "OperationalError",
        "IntegrityError",
        "InternalError",
        "ProgrammingError",
        "NotSupportedError",
        "DatabaseError",
        "InterfaceError",
        "Error",
    ]:
        setattr(Database, exc, getattr(dbapi2, exc))


setup()
del setup


class DatabaseWrapper(BaseAsyncDatabaseWrapper, SQLiteDatabaseWrapper):
    Database = Database
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    async def get_new_connection(self, conn_params):
        conn = await Database.connect(**conn_params)
        await register_functions(conn)

        await conn.execute('PRAGMA foreign_keys = ON')
        # The macOS bundled SQLite defaults legacy_alter_table ON, which
        # prevents atomic table renames (feature supports_atomic_references_rename)
        await conn.execute('PRAGMA legacy_alter_table = OFF')
        return conn

    def create_cursor(self, name=None):

        @aiosqlite_contextmanager
        async def cursor(conn):
            """Create an aiosqlite cursor wrapping a sqlite3 cursor object."""
            return SQLiteCursorWrapper(
                conn, await conn._execute(self.connection._conn.cursor),
            )

        return cursor(self.connection)

    async def close(self):
        await self.validate_task_sharing()
        # If database is in memory, closing the connection destroys the
        # database. However, we only worry about this on the sync side.
        # All async connections have a sync counterpart with creation permissions.
        await BaseAsyncDatabaseWrapper.close(self)

    async def _savepoint_allowed(self):
        # When 'isolation_level' is not None, sqlite3 commits before each
        # savepoint; it's a bug. When it is None, savepoints don't make sense
        # because autocommit is enabled. The only exception is inside 'atomic'
        # blocks. To work around that bug, on SQLite, 'atomic' starts a
        # transaction explicitly rather than simply disable autocommit.
        return self.in_atomic_block

    async def disable_constraint_checking(self):
        async with await self.cursor() as cursor:
            await cursor.execute('PRAGMA foreign_keys = OFF')
            # Foreign key constraints cannot be turned off while in a multi-
            # statement transaction. Fetch the current state of the pragma
            # to determine if constraints are effectively disabled.
            await cursor.execute('PRAGMA foreign_keys')
            enabled = (await cursor.fetchone())[0]
        return not bool(enabled)

    async def enable_constraint_checking(self):
        async with await self.cursor() as cursor:
            await cursor.execute('PRAGMA foreign_keys = ON')

    async def check_constraints(self, table_names=None):
        """See SQLiteDatabaseWrapper.check_constraints()."""
        if self.features.supports_pragma_foreign_key_check:
            async with await self.cursor() as cursor:
                if table_names is None:
                    violations = await (
                        await cursor.execute('PRAGMA foreign_key_check')
                    ).fetchall()
                else:
                    violations = chain.from_iterable(
                        await (
                            await cursor.execute(
                                'PRAGMA foreign_key_check(%s)'
                                % self.ops.quote_name(table_name)
                            )
                        ).fetchall()
                        for table_name in table_names
                    )
                # See https://www.sqlite.org/pragma.html#pragma_foreign_key_check
                for table_name, rowid, referenced_table_name, foreign_key_index in violations:
                    await cursor.execute('PRAGMA foreign_key_list(%s)' % self.ops.quote_name(table_name))
                    foreign_key = (await cursor.fetchall())[foreign_key_index]
                    column_name, referenced_column_name = foreign_key[3:5]
                    primary_key_column_name = await self.introspection.get_primary_key_column(cursor, table_name)
                    await cursor.execute(
                        'SELECT %s, %s FROM %s WHERE rowid = %%s' % (
                            self.ops.quote_name(primary_key_column_name),
                            self.ops.quote_name(column_name),
                            self.ops.quote_name(table_name),
                        ),
                        (rowid,),
                    )
                    primary_key_value, bad_value = await cursor.fetchone()
                    raise IntegrityError(
                        "The row in table '%s' with primary key '%s' has an "
                        "invalid foreign key: %s.%s contains a value '%s' that "
                        "does not have a corresponding value in %s.%s." % (
                            table_name, primary_key_value, table_name, column_name,
                            bad_value, referenced_table_name, referenced_column_name
                        )
                    )
        else:
            async with await self.cursor() as cursor:
                if table_names is None:
                    table_names = await self.introspection.table_names(cursor)
                for table_name in table_names:
                    primary_key_column_name = await self.introspection.get_primary_key_column(cursor, table_name)
                    if not primary_key_column_name:
                        continue
                    relations = await self.introspection.get_relations(cursor, table_name)
                    for column_name, (referenced_column_name, referenced_table_name) in relations:
                        await cursor.execute(
                            """
                            SELECT REFERRING.`%s`, REFERRING.`%s` FROM `%s` as REFERRING
                            LEFT JOIN `%s` as REFERRED
                            ON (REFERRING.`%s` = REFERRED.`%s`)
                            WHERE REFERRING.`%s` IS NOT NULL AND REFERRED.`%s` IS NULL
                            """
                            % (
                                primary_key_column_name, column_name, table_name,
                                referenced_table_name, column_name, referenced_column_name,
                                column_name, referenced_column_name,
                            )
                        )
                        for bad_row in await cursor.fetchall():
                            raise IntegrityError(
                                "The row in table '%s' with primary key '%s' has an "
                                "invalid foreign key: %s.%s contains a value '%s' that "
                                "does not have a corresponding value in %s.%s." % (
                                    table_name, bad_row[0], table_name, column_name,
                                    bad_row[1], referenced_table_name, referenced_column_name,
                                )
                            )

    async def is_usable(self):
        return True

    async def _start_transaction_under_autocommit(self):
        """
        Start a transaction explicitly in autocommit mode.

        Staying in autocommit mode works around a bug of sqlite3 that breaks
        savepoints when autocommit is disabled.
        """
        await (await self.cursor()).execute("BEGIN")


class SQLiteCursorWrapper(Database.Cursor):
    """
    See django.db.backends.sqlite.base.SQLiteCursorWrapper
    """

    async def execute(self, query, params=None):
        if params is None:
            return await Database.Cursor.execute(self, query)
        query = self.convert_query(query)
        return await Database.Cursor.execute(self, query, params)

    async def executemany(self, query, param_list):
        query = self.convert_query(query)
        return await Database.Cursor.executemany(self, query, param_list)

    def convert_query(self, query):
        return FORMAT_QMARK_REGEX.sub('?', query).replace('%%', '%')
