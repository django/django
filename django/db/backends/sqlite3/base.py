"""
SQLite backend for the sqlite3 module in the standard library.
"""
import datetime
import decimal
import warnings
from collections.abc import Mapping
from itertools import chain, tee
from sqlite3 import dbapi2 as Database

from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError
from django.db.backends.base.base import BaseDatabaseWrapper
from django.utils.asyncio import async_unsafe
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.regex_helper import _lazy_re_compile

from ._functions import register as register_functions
from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor


def decoder(conv_func):
    """
    Convert bytestrings from Python's sqlite3 interface to a regular string.
    """
    return lambda s: conv_func(s.decode())


def adapt_date(val):
    return val.isoformat()


def adapt_datetime(val):
    return val.isoformat(" ")


Database.register_converter("bool", b"1".__eq__)
Database.register_converter("date", decoder(parse_date))
Database.register_converter("time", decoder(parse_time))
Database.register_converter("datetime", decoder(parse_datetime))
Database.register_converter("timestamp", decoder(parse_datetime))

Database.register_adapter(decimal.Decimal, str)
Database.register_adapter(datetime.date, adapt_date)
Database.register_adapter(datetime.datetime, adapt_datetime)


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = "sqlite"
    display_name = "SQLite"
    # SQLite doesn't actually support most of these types, but it "does the right
    # thing" given more verbose field definitions, so leave them as is so that
    # schema inspection is more useful.
    data_types = {
        "AutoField": "integer",
        "BigAutoField": "integer",
        "BinaryField": "BLOB",
        "BooleanField": "bool",
        "CharField": "varchar(%(max_length)s)",
        "DateField": "date",
        "DateTimeField": "datetime",
        "DecimalField": "decimal",
        "DurationField": "bigint",
        "FileField": "varchar(%(max_length)s)",
        "FilePathField": "varchar(%(max_length)s)",
        "FloatField": "real",
        "IntegerField": "integer",
        "BigIntegerField": "bigint",
        "IPAddressField": "char(15)",
        "GenericIPAddressField": "char(39)",
        "JSONField": "text",
        "OneToOneField": "integer",
        "PositiveBigIntegerField": "bigint unsigned",
        "PositiveIntegerField": "integer unsigned",
        "PositiveSmallIntegerField": "smallint unsigned",
        "SlugField": "varchar(%(max_length)s)",
        "SmallAutoField": "integer",
        "SmallIntegerField": "smallint",
        "TextField": "text",
        "TimeField": "time",
        "UUIDField": "char(32)",
    }
    data_type_check_constraints = {
        "PositiveBigIntegerField": '"%(column)s" >= 0',
        "JSONField": '(JSON_VALID("%(column)s") OR "%(column)s" IS NULL)',
        "PositiveIntegerField": '"%(column)s" >= 0',
        "PositiveSmallIntegerField": '"%(column)s" >= 0',
    }
    data_types_suffix = {
        "AutoField": "AUTOINCREMENT",
        "BigAutoField": "AUTOINCREMENT",
        "SmallAutoField": "AUTOINCREMENT",
    }
    # SQLite requires LIKE statements to include an ESCAPE clause if the value
    # being escaped has a percent or underscore in it.
    # See https://www.sqlite.org/lang_expr.html for an explanation.
    operators = {
        "exact": "= %s",
        "iexact": "LIKE %s ESCAPE '\\'",
        "contains": "LIKE %s ESCAPE '\\'",
        "icontains": "LIKE %s ESCAPE '\\'",
        "regex": "REGEXP %s",
        "iregex": "REGEXP '(?i)' || %s",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s ESCAPE '\\'",
        "endswith": "LIKE %s ESCAPE '\\'",
        "istartswith": "LIKE %s ESCAPE '\\'",
        "iendswith": "LIKE %s ESCAPE '\\'",
    }

    # The patterns below are used to generate SQL pattern lookup clauses when
    # the right-hand side of the lookup isn't a raw string (it might be an expression
    # or the result of a bilateral transformation).
    # In those cases, special characters for LIKE operators (e.g. \, *, _) should be
    # escaped on database side.
    #
    # Note: we use str.format() here for readability as '%' is used as a wildcard for
    # the LIKE operator.
    pattern_esc = r"REPLACE(REPLACE(REPLACE({}, '\', '\\'), '%%', '\%%'), '_', '\_')"
    pattern_ops = {
        "contains": r"LIKE '%%' || {} || '%%' ESCAPE '\'",
        "icontains": r"LIKE '%%' || UPPER({}) || '%%' ESCAPE '\'",
        "startswith": r"LIKE {} || '%%' ESCAPE '\'",
        "istartswith": r"LIKE UPPER({}) || '%%' ESCAPE '\'",
        "endswith": r"LIKE '%%' || {} ESCAPE '\'",
        "iendswith": r"LIKE '%%' || UPPER({}) ESCAPE '\'",
    }

    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor
    # Classes instantiated in __init__().
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    def get_connection_params(self):
        settings_dict = self.settings_dict
        if not settings_dict["NAME"]:
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value."
            )
        kwargs = {
            "database": settings_dict["NAME"],
            "detect_types": Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
            **settings_dict["OPTIONS"],
        }
        # Always allow the underlying SQLite connection to be shareable
        # between multiple threads. The safe-guarding will be handled at a
        # higher level by the `BaseDatabaseWrapper.allow_thread_sharing`
        # property. This is necessary as the shareability is disabled by
        # default in sqlite3 and it cannot be changed once a connection is
        # opened.
        if "check_same_thread" in kwargs and kwargs["check_same_thread"]:
            warnings.warn(
                "The `check_same_thread` option was provided and set to "
                "True. It will be overridden with False. Use the "
                "`DatabaseWrapper.allow_thread_sharing` property instead "
                "for controlling thread shareability.",
                RuntimeWarning,
            )
        kwargs.update({"check_same_thread": False, "uri": True})
        return kwargs

    def get_database_version(self):
        return self.Database.sqlite_version_info

    @async_unsafe
    def get_new_connection(self, conn_params):
        conn = Database.connect(**conn_params)
        register_functions(conn)

        conn.execute("PRAGMA foreign_keys = ON")
        # The macOS bundled SQLite defaults legacy_alter_table ON, which
        # prevents atomic table renames (feature supports_atomic_references_rename)
        conn.execute("PRAGMA legacy_alter_table = OFF")
        return conn

    def create_cursor(self, name=None):
        return self.connection.cursor(factory=SQLiteCursorWrapper)

    @async_unsafe
    def close(self):
        self.validate_thread_sharing()
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if not self.is_in_memory_db():
            BaseDatabaseWrapper.close(self)

    def _savepoint_allowed(self):
        # When 'isolation_level' is not None, sqlite3 commits before each
        # savepoint; it's a bug. When it is None, savepoints don't make sense
        # because autocommit is enabled. The only exception is inside 'atomic'
        # blocks. To work around that bug, on SQLite, 'atomic' starts a
        # transaction explicitly rather than simply disable autocommit.
        return self.in_atomic_block

    def _set_autocommit(self, autocommit):
        if autocommit:
            level = None
        else:
            # sqlite3's internal default is ''. It's different from None.
            # See Modules/_sqlite/connection.c.
            level = ""
        # 'isolation_level' is a misleading API.
        # SQLite always runs at the SERIALIZABLE isolation level.
        with self.wrap_database_errors:
            self.connection.isolation_level = level

    def disable_constraint_checking(self):
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF")
            # Foreign key constraints cannot be turned off while in a multi-
            # statement transaction. Fetch the current state of the pragma
            # to determine if constraints are effectively disabled.
            enabled = cursor.execute("PRAGMA foreign_keys").fetchone()[0]
        return not bool(enabled)

    def enable_constraint_checking(self):
        with self.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = ON")

    def check_constraints(self, table_names=None):
        """
        Check each table name in `table_names` for rows with invalid foreign
        key references. This method is intended to be used in conjunction with
        `disable_constraint_checking()` and `enable_constraint_checking()`, to
        determine if rows with invalid references were entered while constraint
        checks were off.
        """
        if self.features.supports_pragma_foreign_key_check:
            with self.cursor() as cursor:
                if table_names is None:
                    violations = cursor.execute("PRAGMA foreign_key_check").fetchall()
                else:
                    violations = chain.from_iterable(
                        cursor.execute(
                            "PRAGMA foreign_key_check(%s)"
                            % self.ops.quote_name(table_name)
                        ).fetchall()
                        for table_name in table_names
                    )
                # See https://www.sqlite.org/pragma.html#pragma_foreign_key_check
                for (
                    table_name,
                    rowid,
                    referenced_table_name,
                    foreign_key_index,
                ) in violations:
                    foreign_key = cursor.execute(
                        "PRAGMA foreign_key_list(%s)" % self.ops.quote_name(table_name)
                    ).fetchall()[foreign_key_index]
                    column_name, referenced_column_name = foreign_key[3:5]
                    primary_key_column_name = self.introspection.get_primary_key_column(
                        cursor, table_name
                    )
                    primary_key_value, bad_value = cursor.execute(
                        "SELECT %s, %s FROM %s WHERE rowid = %%s"
                        % (
                            self.ops.quote_name(primary_key_column_name),
                            self.ops.quote_name(column_name),
                            self.ops.quote_name(table_name),
                        ),
                        (rowid,),
                    ).fetchone()
                    raise IntegrityError(
                        "The row in table '%s' with primary key '%s' has an "
                        "invalid foreign key: %s.%s contains a value '%s' that "
                        "does not have a corresponding value in %s.%s."
                        % (
                            table_name,
                            primary_key_value,
                            table_name,
                            column_name,
                            bad_value,
                            referenced_table_name,
                            referenced_column_name,
                        )
                    )
        else:
            with self.cursor() as cursor:
                if table_names is None:
                    table_names = self.introspection.table_names(cursor)
                for table_name in table_names:
                    primary_key_column_name = self.introspection.get_primary_key_column(
                        cursor, table_name
                    )
                    if not primary_key_column_name:
                        continue
                    relations = self.introspection.get_relations(cursor, table_name)
                    for column_name, (
                        referenced_column_name,
                        referenced_table_name,
                    ) in relations.items():
                        cursor.execute(
                            """
                            SELECT REFERRING.`%s`, REFERRING.`%s` FROM `%s` as REFERRING
                            LEFT JOIN `%s` as REFERRED
                            ON (REFERRING.`%s` = REFERRED.`%s`)
                            WHERE REFERRING.`%s` IS NOT NULL AND REFERRED.`%s` IS NULL
                            """
                            % (
                                primary_key_column_name,
                                column_name,
                                table_name,
                                referenced_table_name,
                                column_name,
                                referenced_column_name,
                                column_name,
                                referenced_column_name,
                            )
                        )
                        for bad_row in cursor.fetchall():
                            raise IntegrityError(
                                "The row in table '%s' with primary key '%s' has an "
                                "invalid foreign key: %s.%s contains a value '%s' that "
                                "does not have a corresponding value in %s.%s."
                                % (
                                    table_name,
                                    bad_row[0],
                                    table_name,
                                    column_name,
                                    bad_row[1],
                                    referenced_table_name,
                                    referenced_column_name,
                                )
                            )

    def is_usable(self):
        return True

    def _start_transaction_under_autocommit(self):
        """
        Start a transaction explicitly in autocommit mode.

        Staying in autocommit mode works around a bug of sqlite3 that breaks
        savepoints when autocommit is disabled.
        """
        self.cursor().execute("BEGIN")

    def is_in_memory_db(self):
        return self.creation.is_in_memory_db(self.settings_dict["NAME"])


FORMAT_QMARK_REGEX = _lazy_re_compile(r"(?<!%)%s")


class SQLiteCursorWrapper(Database.Cursor):
    """
    Django uses the "format" and "pyformat" styles, but Python's sqlite3 module
    supports neither of these styles.

    This wrapper performs the following conversions:

    - "format" style to "qmark" style
    - "pyformat" style to "named" style

    In both cases, if you want to use a literal "%s", you'll need to use "%%s".
    """

    def execute(self, query, params=None):
        if params is None:
            return super().execute(query)
        # Extract names if params is a mapping, i.e. "pyformat" style is used.
        param_names = list(params) if isinstance(params, Mapping) else None
        query = self.convert_query(query, param_names=param_names)
        return super().execute(query, params)

    def executemany(self, query, param_list):
        # Extract names if params is a mapping, i.e. "pyformat" style is used.
        # Peek carefully as a generator can be passed instead of a list/tuple.
        peekable, param_list = tee(iter(param_list))
        if (params := next(peekable, None)) and isinstance(params, Mapping):
            param_names = list(params)
        else:
            param_names = None
        query = self.convert_query(query, param_names=param_names)
        return super().executemany(query, param_list)

    def convert_query(self, query, *, param_names=None):
        if param_names is None:
            # Convert from "format" style to "qmark" style.
            return FORMAT_QMARK_REGEX.sub("?", query).replace("%%", "%")
        else:
            # Convert from "pyformat" style to "named" style.
            return query % {name: f":{name}" for name in param_names}
