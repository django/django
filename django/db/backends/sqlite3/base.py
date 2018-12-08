"""
SQLite3 backend for the sqlite3 module in the standard library.
"""
import datetime
import decimal
import math
import operator
import re
import warnings
from sqlite3 import dbapi2 as Database

import pytz

from django.core.exceptions import ImproperlyConfigured
from django.db import utils
from django.db.backends import utils as backend_utils
from django.db.backends.base.base import BaseDatabaseWrapper
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_time
from django.utils.duration import duration_microseconds

from .client import DatabaseClient                          # isort:skip
from .creation import DatabaseCreation                      # isort:skip
from .features import DatabaseFeatures                      # isort:skip
from .introspection import DatabaseIntrospection            # isort:skip
from .operations import DatabaseOperations                  # isort:skip
from .schema import DatabaseSchemaEditor                    # isort:skip


def decoder(conv_func):
    """
    Convert bytestrings from Python's sqlite3 interface to a regular string.
    """
    return lambda s: conv_func(s.decode())


Database.register_converter("bool", b'1'.__eq__)
Database.register_converter("time", decoder(parse_time))
Database.register_converter("datetime", decoder(parse_datetime))
Database.register_converter("timestamp", decoder(parse_datetime))
Database.register_converter("TIMESTAMP", decoder(parse_datetime))

Database.register_adapter(decimal.Decimal, backend_utils.rev_typecast_decimal)


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'sqlite'
    display_name = 'SQLite'
    # SQLite doesn't actually support most of these types, but it "does the right
    # thing" given more verbose field definitions, so leave them as is so that
    # schema inspection is more useful.
    data_types = {
        'AutoField': 'integer',
        'BigAutoField': 'integer',
        'BinaryField': 'BLOB',
        'BooleanField': 'bool',
        'CharField': 'varchar(%(max_length)s)',
        'DateField': 'date',
        'DateTimeField': 'datetime',
        'DecimalField': 'decimal',
        'DurationField': 'bigint',
        'FileField': 'varchar(%(max_length)s)',
        'FilePathField': 'varchar(%(max_length)s)',
        'FloatField': 'real',
        'IntegerField': 'integer',
        'BigIntegerField': 'bigint',
        'IPAddressField': 'char(15)',
        'GenericIPAddressField': 'char(39)',
        'NullBooleanField': 'bool',
        'OneToOneField': 'integer',
        'PositiveIntegerField': 'integer unsigned',
        'PositiveSmallIntegerField': 'smallint unsigned',
        'SlugField': 'varchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField': 'text',
        'TimeField': 'time',
        'UUIDField': 'char(32)',
    }
    data_types_suffix = {
        'AutoField': 'AUTOINCREMENT',
        'BigAutoField': 'AUTOINCREMENT',
    }
    # SQLite requires LIKE statements to include an ESCAPE clause if the value
    # being escaped has a percent or underscore in it.
    # See https://www.sqlite.org/lang_expr.html for an explanation.
    operators = {
        'exact': '= %s',
        'iexact': "LIKE %s ESCAPE '\\'",
        'contains': "LIKE %s ESCAPE '\\'",
        'icontains': "LIKE %s ESCAPE '\\'",
        'regex': 'REGEXP %s',
        'iregex': "REGEXP '(?i)' || %s",
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKE %s ESCAPE '\\'",
        'endswith': "LIKE %s ESCAPE '\\'",
        'istartswith': "LIKE %s ESCAPE '\\'",
        'iendswith': "LIKE %s ESCAPE '\\'",
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
        'contains': r"LIKE '%%' || {} || '%%' ESCAPE '\'",
        'icontains': r"LIKE '%%' || UPPER({}) || '%%' ESCAPE '\'",
        'startswith': r"LIKE {} || '%%' ESCAPE '\'",
        'istartswith': r"LIKE UPPER({}) || '%%' ESCAPE '\'",
        'endswith': r"LIKE '%%' || {} ESCAPE '\'",
        'iendswith': r"LIKE '%%' || UPPER({}) ESCAPE '\'",
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
        if not settings_dict['NAME']:
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value.")
        kwargs = {
            'database': settings_dict['NAME'],
            'detect_types': Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
            **settings_dict['OPTIONS'],
        }
        # Always allow the underlying SQLite connection to be shareable
        # between multiple threads. The safe-guarding will be handled at a
        # higher level by the `BaseDatabaseWrapper.allow_thread_sharing`
        # property. This is necessary as the shareability is disabled by
        # default in pysqlite and it cannot be changed once a connection is
        # opened.
        if 'check_same_thread' in kwargs and kwargs['check_same_thread']:
            warnings.warn(
                'The `check_same_thread` option was provided and set to '
                'True. It will be overridden with False. Use the '
                '`DatabaseWrapper.allow_thread_sharing` property instead '
                'for controlling thread shareability.',
                RuntimeWarning
            )
        kwargs.update({'check_same_thread': False, 'uri': True})
        return kwargs

    def get_new_connection(self, conn_params):
        conn = Database.connect(**conn_params)
        conn.create_function("django_date_extract", 2, _sqlite_date_extract)
        conn.create_function("django_date_trunc", 2, _sqlite_date_trunc)
        conn.create_function("django_datetime_cast_date", 2, _sqlite_datetime_cast_date)
        conn.create_function("django_datetime_cast_time", 2, _sqlite_datetime_cast_time)
        conn.create_function("django_datetime_extract", 3, _sqlite_datetime_extract)
        conn.create_function("django_datetime_trunc", 3, _sqlite_datetime_trunc)
        conn.create_function("django_time_extract", 2, _sqlite_time_extract)
        conn.create_function("django_time_trunc", 2, _sqlite_time_trunc)
        conn.create_function("django_time_diff", 2, _sqlite_time_diff)
        conn.create_function("django_timestamp_diff", 2, _sqlite_timestamp_diff)
        conn.create_function("regexp", 2, _sqlite_regexp)
        conn.create_function("django_format_dtdelta", 3, _sqlite_format_dtdelta)
        conn.create_function("django_power", 2, _sqlite_power)
        conn.create_function('LPAD', 3, _sqlite_lpad)
        conn.create_function('REPEAT', 2, operator.mul)
        conn.create_function('RPAD', 3, _sqlite_rpad)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def init_connection_state(self):
        pass

    def create_cursor(self, name=None):
        return self.connection.cursor(factory=SQLiteCursorWrapper)

    def close(self):
        self.validate_thread_sharing()
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if not self.is_in_memory_db():
            BaseDatabaseWrapper.close(self)

    def _savepoint_allowed(self):
        # Two conditions are required here:
        # - A sufficiently recent version of SQLite to support savepoints,
        # - Being in a transaction, which can only happen inside 'atomic'.

        # When 'isolation_level' is not None, sqlite3 commits before each
        # savepoint; it's a bug. When it is None, savepoints don't make sense
        # because autocommit is enabled. The only exception is inside 'atomic'
        # blocks. To work around that bug, on SQLite, 'atomic' starts a
        # transaction explicitly rather than simply disable autocommit.
        return self.features.uses_savepoints and self.in_atomic_block

    def _set_autocommit(self, autocommit):
        if autocommit:
            level = None
        else:
            # sqlite3's internal default is ''. It's different from None.
            # See Modules/_sqlite/connection.c.
            level = ''
        # 'isolation_level' is a misleading API.
        # SQLite always runs at the SERIALIZABLE isolation level.
        with self.wrap_database_errors:
            self.connection.isolation_level = level

    def disable_constraint_checking(self):
        with self.cursor() as cursor:
            cursor.execute('PRAGMA foreign_keys = OFF')
            # Foreign key constraints cannot be turned off while in a multi-
            # statement transaction. Fetch the current state of the pragma
            # to determine if constraints are effectively disabled.
            enabled = cursor.execute('PRAGMA foreign_keys').fetchone()[0]
        return not bool(enabled)

    def enable_constraint_checking(self):
        self.cursor().execute('PRAGMA foreign_keys = ON')

    def check_constraints(self, table_names=None):
        """
        Check each table name in `table_names` for rows with invalid foreign
        key references. This method is intended to be used in conjunction with
        `disable_constraint_checking()` and `enable_constraint_checking()`, to
        determine if rows with invalid references were entered while constraint
        checks were off.
        """
        with self.cursor() as cursor:
            if table_names is None:
                table_names = self.introspection.table_names(cursor)
            for table_name in table_names:
                primary_key_column_name = self.introspection.get_primary_key_column(cursor, table_name)
                if not primary_key_column_name:
                    continue
                key_columns = self.introspection.get_key_columns(cursor, table_name)
                for column_name, referenced_table_name, referenced_column_name in key_columns:
                    cursor.execute(
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
                    for bad_row in cursor.fetchall():
                        raise utils.IntegrityError(
                            "The row in table '%s' with primary key '%s' has an "
                            "invalid foreign key: %s.%s contains a value '%s' that "
                            "does not have a corresponding value in %s.%s." % (
                                table_name, bad_row[0], table_name, column_name,
                                bad_row[1], referenced_table_name, referenced_column_name,
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
        return self.creation.is_in_memory_db(self.settings_dict['NAME'])


FORMAT_QMARK_REGEX = re.compile(r'(?<!%)%s')


class SQLiteCursorWrapper(Database.Cursor):
    """
    Django uses "format" style placeholders, but pysqlite2 uses "qmark" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def execute(self, query, params=None):
        if params is None:
            return Database.Cursor.execute(self, query)
        query = self.convert_query(query)
        return Database.Cursor.execute(self, query, params)

    def executemany(self, query, param_list):
        query = self.convert_query(query)
        return Database.Cursor.executemany(self, query, param_list)

    def convert_query(self, query):
        return FORMAT_QMARK_REGEX.sub('?', query).replace('%%', '%')


def _sqlite_date_extract(lookup_type, dt):
    if dt is None:
        return None
    try:
        dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    elif lookup_type == 'week':
        return dt.isocalendar()[1]
    elif lookup_type == 'quarter':
        return math.ceil(dt.month / 3)
    else:
        return getattr(dt, lookup_type)


def _sqlite_date_trunc(lookup_type, dt):
    try:
        dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01" % dt.year
    elif lookup_type == 'quarter':
        month_in_quarter = dt.month - (dt.month - 1) % 3
        return '%i-%02i-01' % (dt.year, month_in_quarter)
    elif lookup_type == 'month':
        return "%i-%02i-01" % (dt.year, dt.month)
    elif lookup_type == 'week':
        dt = dt - datetime.timedelta(days=dt.weekday())
        return "%i-%02i-%02i" % (dt.year, dt.month, dt.day)
    elif lookup_type == 'day':
        return "%i-%02i-%02i" % (dt.year, dt.month, dt.day)


def _sqlite_time_trunc(lookup_type, dt):
    try:
        dt = backend_utils.typecast_time(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'hour':
        return "%02i:00:00" % dt.hour
    elif lookup_type == 'minute':
        return "%02i:%02i:00" % (dt.hour, dt.minute)
    elif lookup_type == 'second':
        return "%02i:%02i:%02i" % (dt.hour, dt.minute, dt.second)


def _sqlite_datetime_parse(dt, tzname):
    if dt is None:
        return None
    try:
        dt = backend_utils.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if tzname is not None:
        dt = timezone.localtime(dt, pytz.timezone(tzname))
    return dt


def _sqlite_datetime_cast_date(dt, tzname):
    dt = _sqlite_datetime_parse(dt, tzname)
    if dt is None:
        return None
    return dt.date().isoformat()


def _sqlite_datetime_cast_time(dt, tzname):
    dt = _sqlite_datetime_parse(dt, tzname)
    if dt is None:
        return None
    return dt.time().isoformat()


def _sqlite_datetime_extract(lookup_type, dt, tzname):
    dt = _sqlite_datetime_parse(dt, tzname)
    if dt is None:
        return None
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    elif lookup_type == 'week':
        return dt.isocalendar()[1]
    elif lookup_type == 'quarter':
        return math.ceil(dt.month / 3)
    else:
        return getattr(dt, lookup_type)


def _sqlite_datetime_trunc(lookup_type, dt, tzname):
    dt = _sqlite_datetime_parse(dt, tzname)
    if dt is None:
        return None
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'quarter':
        month_in_quarter = dt.month - (dt.month - 1) % 3
        return '%i-%02i-01 00:00:00' % (dt.year, month_in_quarter)
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'week':
        dt = dt - datetime.timedelta(days=dt.weekday())
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)
    elif lookup_type == 'hour':
        return "%i-%02i-%02i %02i:00:00" % (dt.year, dt.month, dt.day, dt.hour)
    elif lookup_type == 'minute':
        return "%i-%02i-%02i %02i:%02i:00" % (dt.year, dt.month, dt.day, dt.hour, dt.minute)
    elif lookup_type == 'second':
        return "%i-%02i-%02i %02i:%02i:%02i" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def _sqlite_time_extract(lookup_type, dt):
    if dt is None:
        return None
    try:
        dt = backend_utils.typecast_time(dt)
    except (ValueError, TypeError):
        return None
    return getattr(dt, lookup_type)


def _sqlite_format_dtdelta(conn, lhs, rhs):
    """
    LHS and RHS can be either:
    - An integer number of microseconds
    - A string representing a datetime
    """
    try:
        real_lhs = datetime.timedelta(0, 0, lhs) if isinstance(lhs, int) else backend_utils.typecast_timestamp(lhs)
        real_rhs = datetime.timedelta(0, 0, rhs) if isinstance(rhs, int) else backend_utils.typecast_timestamp(rhs)
        if conn.strip() == '+':
            out = real_lhs + real_rhs
        else:
            out = real_lhs - real_rhs
    except (ValueError, TypeError):
        return None
    # typecast_timestamp returns a date or a datetime without timezone.
    # It will be formatted as "%Y-%m-%d" or "%Y-%m-%d %H:%M:%S[.%f]"
    return str(out)


def _sqlite_time_diff(lhs, rhs):
    left = backend_utils.typecast_time(lhs)
    right = backend_utils.typecast_time(rhs)
    return (
        (left.hour * 60 * 60 * 1000000) +
        (left.minute * 60 * 1000000) +
        (left.second * 1000000) +
        (left.microsecond) -
        (right.hour * 60 * 60 * 1000000) -
        (right.minute * 60 * 1000000) -
        (right.second * 1000000) -
        (right.microsecond)
    )


def _sqlite_timestamp_diff(lhs, rhs):
    left = backend_utils.typecast_timestamp(lhs)
    right = backend_utils.typecast_timestamp(rhs)
    return duration_microseconds(left - right)


def _sqlite_regexp(re_pattern, re_string):
    return bool(re.search(re_pattern, str(re_string))) if re_string is not None else False


def _sqlite_lpad(text, length, fill_text):
    if len(text) >= length:
        return text[:length]
    return (fill_text * length)[:length - len(text)] + text


def _sqlite_rpad(text, length, fill_text):
    return (text + fill_text * length)[:length]


def _sqlite_power(x, y):
    return x ** y
