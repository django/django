"""
DuckDB backend for Django.
"""

from pathlib import Path
from collections.abc import Mapping

import duckdb

from django.db.backends.base.base import BaseDatabaseWrapper
from django.utils.asyncio import async_unsafe

from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor


def _get_varchar_column(data):
    if data["max_length"] is None:
        return "VARCHAR"
    return "VARCHAR(%(max_length)s)" % data


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = "duckdb"
    display_name = "DuckDB"
    data_types = {
        "AutoField": "INTEGER",
        "BigAutoField": "BIGINT",
        "BinaryField": "BLOB",
        "BooleanField": "BOOLEAN",
        "CharField": _get_varchar_column,
        "DateField": "DATE",
        "DateTimeField": "TIMESTAMP",
        "DecimalField": "DECIMAL",
        "DurationField": "BIGINT",
        "FileField": "VARCHAR(%(max_length)s)",
        "FilePathField": "VARCHAR(%(max_length)s)",
        "FloatField": "DOUBLE",
        "IntegerField": "INTEGER",
        "BigIntegerField": "BIGINT",
        "IPAddressField": "VARCHAR(15)",
        "GenericIPAddressField": "VARCHAR(39)",
        "JSONField": "JSON",
        "PositiveBigIntegerField": "BIGINT",
        "PositiveIntegerField": "INTEGER",
        "PositiveSmallIntegerField": "SMALLINT",
        "SlugField": "VARCHAR(%(max_length)s)",
        "SmallAutoField": "INTEGER",
        "SmallIntegerField": "SMALLINT",
        "TextField": "VARCHAR",
        "TimeField": "TIME",
        "UUIDField": "VARCHAR(32)",
    }
    data_type_check_constraints = {
        "PositiveBigIntegerField": '"%(column)s" >= 0',
        "PositiveIntegerField": '"%(column)s" >= 0',
        "PositiveSmallIntegerField": '"%(column)s" >= 0',
    }
    data_types_suffix = {}

    operators = {
        "exact": "= %s",
        "iexact": "ILIKE %s",
        "contains": "LIKE %s",
        "icontains": "ILIKE %s",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s",
        "endswith": "LIKE %s",
        "istartswith": "ILIKE %s",
        "iendswith": "ILIKE %s",
    }

    pattern_esc = r"REPLACE(REPLACE(REPLACE({}, '\\', '\\\\'), '%%', '\\%%'), '_', '\\_')"
    pattern_ops = {
        "contains": r"LIKE '%%' || {} || '%%'",
        "icontains": r"ILIKE '%%' || {} || '%%'",
        "startswith": r"LIKE {} || '%%'",
        "istartswith": r"ILIKE {} || '%%'",
        "endswith": r"LIKE '%%' || {}",
        "iendswith": r"ILIKE '%%' || {}",
    }

    Database = duckdb
    # DuckDB doesn't have InterfaceError; map it to OperationalError
    # The wrap_database_errors context manager needs these exception classes
    # on the Database module for proper error translation
    if not hasattr(duckdb, 'InterfaceError'):
        duckdb.InterfaceError = duckdb.OperationalError
    SchemaEditorClass = DatabaseSchemaEditor
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    def get_connection_params(self):
        settings_dict = self.settings_dict
        kwargs = {
            "database": settings_dict["NAME"] or ":memory:",
            **settings_dict["OPTIONS"],
        }
        return kwargs

    def get_database_version(self):
        # Return version as a tuple for Django's version check
        version_str = self.Database.__version__
        # Parse version string like "1.0.0" into a tuple (1, 0, 0)
        parts = version_str.split(".")
        return tuple(int(p) for p in parts if p.isdigit())

    @async_unsafe
    def get_new_connection(self, conn_params):
        database = conn_params["database"]
        if database != ":memory:":
            try:
                Path(database).parent.mkdir(exist_ok=True, parents=True)
            except OSError as e:
                raise duckdb.OperationalError(f"Error creating path to DuckDB database: {e}.")
        conn = self.Database.connect(**conn_params)
        # DuckDB autocommit is ON by default, which is what Django expects
        return conn

    def create_cursor(self, name=None):
        return DuckDBCursorWrapper(self.connection)

    @async_unsafe
    def close(self):
        self.validate_thread_sharing()
        BaseDatabaseWrapper.close(self)

    def _savepoint_allowed(self):
        return self.features.uses_savepoints and self.in_atomic_block

    def _set_autocommit(self, autocommit):
        # DuckDB doesn't have an AUTOCOMMIT setting.
        # It auto-commits each statement unless inside a BEGIN/COMMIT block.
        # Django's autocommit control is handled via the atomic() context manager
        # which calls _start_transaction_under_autocommit() to begin a transaction.
        # So we just need to ensure any pending transaction is committed when
        # switching to autocommit mode.
        if autocommit:
            try:
                with self.wrap_database_errors:
                    self.connection.commit()
            except Exception:
                pass  # No active transaction to commit

    def disable_constraint_checking(self):
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys(OFF)")
            enabled = cursor.execute("PRAGMA foreign_keys").fetchone()[0]
        return not bool(enabled)

    def enable_constraint_checking(self):
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys(ON)")

    def check_constraints(self, table_names=None):
        """
        Check each table name in `table_names` for rows with invalid foreign
        key references.
        """
        pass  # DuckDB does not have a PRAGMA foreign_key_check equivalent

    def is_usable(self):
        try:
            self.connection.execute("SELECT 1")
            return True
        except Exception:
            return False

    def _start_transaction_under_autocommit(self):
        self.cursor().execute("BEGIN")


class DuckDBCursorWrapper:
    """
    Wraps DuckDB's cursor to convert Django's parameter styles to DuckDB's.

    DuckDB uses '?' for positional parameters. Django uses '%s' (format style)
    and '%(name)s' (pyformat style). This wrapper converts those to '?'
    placeholders.
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, params=None):
        if params is None:
            return self.cursor.execute(query)
        # Convert pyformat style (%(name)s) to named parameters
        # DuckDB doesn't support named params, so we use positional
        if isinstance(params, Mapping):
            param_names = list(params)
            query = self.convert_query(query, param_names=param_names)
            params = list(params.values())
        else:
            query = self.convert_query(query)
        return self.cursor.execute(query, params)

    def executemany(self, query, param_list):
        if not param_list:
            return
        iterator = iter(param_list)
        first = next(iterator, None)
        if first is None:
            return
        if isinstance(first, Mapping):
            param_names = list(first)
            query = self.convert_query(query, param_names=param_names)
            param_list = [list(p.values()) for p in iterator]
            # Don't forget the first item
            param_list = [list(first.values())] + param_list
        else:
            query = self.convert_query(query)
            param_list = [first] + list(iterator)
        return self.cursor.executemany(query, param_list)

    def convert_query(self, query, param_names=None):
        if param_names is None:
            # Convert %s to ? (but not %% which is a literal %)
            # We need to handle %%s carefully
            result = []
        else:
            # Convert %(name)s to ?
            result = []

        if param_names is None:
            # Simple %s -> ? conversion
            i = 0
            while i < len(query):
                if i < len(query) - 1 and query[i] == "%" and query[i + 1] == "%":
                    result.append("%")
                    i += 2
                elif i < len(query) - 1 and query[i] == "%" and query[i + 1] == "s":
                    result.append("?")
                    i += 2
                else:
                    result.append(query[i])
                    i += 1
            return "".join(result)
        else:
            # Convert %(name)s to ?
            for name in param_names:
                query = query.replace("%(" + name + ")s", "?", 1)
            # Also handle any remaining %s
            i = 0
            converted = []
            while i < len(query):
                if i < len(query) - 1 and query[i] == "%" and query[i + 1] == "%":
                    converted.append("%")
                    i += 2
                elif i < len(query) - 1 and query[i] == "%" and query[i + 1] == "s":
                    converted.append("?")
                    i += 2
                else:
                    converted.append(query[i])
                    i += 1
            return "".join(converted)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchmany(self, size):
        return self.cursor.fetchmany(size)

    def fetchall(self):
        return self.cursor.fetchall()

    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        # The wrapped object is the shared connection, which is closed by
        # DatabaseWrapper.close(); closing it here would drop the transaction.
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __iter__(self):
        return iter(self.cursor)
