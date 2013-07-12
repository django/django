"""
SQLite3 backend for django.

Works with either the pysqlite2 module or the sqlite3 module in the
standard library.
"""
from __future__ import unicode_literals

import datetime
import decimal
import warnings
import re

from django.conf import settings
from django.db import utils
from django.db.backends import (util, BaseDatabaseFeatures,
    BaseDatabaseOperations, BaseDatabaseWrapper, BaseDatabaseValidation)
from django.db.backends.sqlite3.client import DatabaseClient
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.db.backends.sqlite3.introspection import DatabaseIntrospection
from django.db.models import fields
from django.db.models.sql import aggregates
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.safestring import SafeBytes
from django.utils import six
from django.utils import timezone

try:
    try:
        from pysqlite2 import dbapi2 as Database
    except ImportError:
        from sqlite3 import dbapi2 as Database
except ImportError as exc:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading either pysqlite2 or sqlite3 modules (tried in that order): %s" % exc)

try:
    import pytz
except ImportError:
    pytz = None

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError


def parse_datetime_with_timezone_support(value):
    dt = parse_datetime(value)
    # Confirm that dt is naive before overwriting its tzinfo.
    if dt is not None and settings.USE_TZ and timezone.is_naive(dt):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def adapt_datetime_with_timezone_support(value):
    # Equivalent to DateTimeField.get_db_prep_value. Used only by raw SQL.
    if settings.USE_TZ:
        if timezone.is_naive(value):
            warnings.warn("SQLite received a naive datetime (%s)"
                          " while time zone support is active." % value,
                          RuntimeWarning)
            default_timezone = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_timezone)
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(str(" "))


def decoder(conv_func):
    """ The Python sqlite3 interface returns always byte strings.
        This function converts the received value to a regular string before
        passing it to the receiver function.
    """
    return lambda s: conv_func(s.decode('utf-8'))

Database.register_converter(str("bool"), decoder(lambda s: s == '1'))
Database.register_converter(str("time"), decoder(parse_time))
Database.register_converter(str("date"), decoder(parse_date))
Database.register_converter(str("datetime"), decoder(parse_datetime_with_timezone_support))
Database.register_converter(str("timestamp"), decoder(parse_datetime_with_timezone_support))
Database.register_converter(str("TIMESTAMP"), decoder(parse_datetime_with_timezone_support))
Database.register_converter(str("decimal"), decoder(util.typecast_decimal))

Database.register_adapter(datetime.datetime, adapt_datetime_with_timezone_support)
Database.register_adapter(decimal.Decimal, util.rev_typecast_decimal)
Database.register_adapter(str, lambda s: s.decode('utf-8'))
Database.register_adapter(SafeBytes, lambda s: s.decode('utf-8'))


class DatabaseFeatures(BaseDatabaseFeatures):
    # SQLite cannot handle us only partially reading from a cursor's result set
    # and then writing the same rows to the database in another cursor. This
    # setting ensures we always read result sets fully into memory all in one
    # go.
    can_use_chunked_reads = False
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True
    supports_timezones = False
    supports_1000_query_parameters = False
    supports_mixed_date_datetime_comparisons = False
    has_bulk_insert = True
    can_combine_inserts_with_and_without_auto_increment_pk = False
    autocommits_when_autocommit_is_off = True
    supports_paramstyle_pyformat = False

    @cached_property
    def uses_savepoints(self):
        return Database.sqlite_version_info >= (3, 6, 8)

    @cached_property
    def supports_stddev(self):
        """Confirm support for STDDEV and related stats functions

        SQLite supports STDDEV as an extension package; so
        connection.ops.check_aggregate_support() can't unilaterally
        rule out support for STDDEV. We need to manually check
        whether the call works.
        """
        cursor = self.connection.cursor()
        cursor.execute('CREATE TABLE STDDEV_TEST (X INT)')
        try:
            cursor.execute('SELECT STDDEV(*) FROM STDDEV_TEST')
            has_support = True
        except utils.DatabaseError:
            has_support = False
        cursor.execute('DROP TABLE STDDEV_TEST')
        return has_support

    @cached_property
    def has_zoneinfo_database(self):
        return pytz is not None


class DatabaseOperations(BaseDatabaseOperations):
    def bulk_batch_size(self, fields, objs):
        """
        SQLite has a compile-time default (SQLITE_LIMIT_VARIABLE_NUMBER) of
        999 variables per query.

        If there is just single field to insert, then we can hit another
        limit, SQLITE_MAX_COMPOUND_SELECT which defaults to 500.
        """
        limit = 999 if len(fields) > 1 else 500
        return (limit // len(fields)) if len(fields) > 0 else len(objs)

    def check_aggregate_support(self, aggregate):
        bad_fields = (fields.DateField, fields.DateTimeField, fields.TimeField)
        bad_aggregates = (aggregates.Sum, aggregates.Avg,
                          aggregates.Variance, aggregates.StdDev)
        if (isinstance(aggregate.source, bad_fields) and
                isinstance(aggregate, bad_aggregates)):
            raise NotImplementedError(
                'You cannot use Sum, Avg, StdDev and Variance aggregations '
                'on date/time fields in sqlite3 '
                'since date/time is saved as text.')

    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_date_extract that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_extract('%s', %s)" % (lookup_type.lower(), field_name)

    def date_interval_sql(self, sql, connector, timedelta):
        # It would be more straightforward if we could use the sqlite strftime
        # function, but it does not allow for keeping six digits of fractional
        # second information, nor does it allow for formatting date and datetime
        # values differently. So instead we register our own function that
        # formats the datetime combined with the delta in a manner suitable
        # for comparisons.
        return 'django_format_dtdelta(%s, "%s", "%d", "%d", "%d")' % (sql,
            connector, timedelta.days, timedelta.seconds, timedelta.microseconds)

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_trunc('%s', %s)" % (lookup_type.lower(), field_name)

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_extract_sql.
        if settings.USE_TZ:
            if pytz is None:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("This query requires pytz, "
                                           "but it isn't installed.")
        return "django_datetime_extract('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_trunc_sql.
        if settings.USE_TZ:
            if pytz is None:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("This query requires pytz, "
                                           "but it isn't installed.")
        return "django_datetime_trunc('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def drop_foreignkey_sql(self):
        return ""

    def pk_default_value(self):
        return "NULL"

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

    def no_limit_value(self):
        return -1

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # NB: The generated SQL below is specific to SQLite
        # Note: The DELETE FROM... SQL generated below works for SQLite databases
        # because constraints don't exist
        sql = ['%s %s %s;' % (
            style.SQL_KEYWORD('DELETE'),
            style.SQL_KEYWORD('FROM'),
            style.SQL_FIELD(self.quote_name(table))
        ) for table in tables]
        # Note: No requirement for reset of auto-incremented indices (cf. other
        # sql_flush() implementations). Just return SQL at this point
        return sql

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("SQLite backend does not support timezone-aware datetimes when USE_TZ is False.")

        return six.text_type(value)

    def value_to_db_time(self, value):
        if value is None:
            return None

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            raise ValueError("SQLite backend does not support timezone-aware times.")

        return six.text_type(value)

    def convert_values(self, value, field):
        """SQLite returns floats when it should be returning decimals,
        and gets dates and datetimes wrong.
        For consistency with other backends, coerce when required.
        """
        if value is None:
            return None

        internal_type = field.get_internal_type()
        if internal_type == 'DecimalField':
            return util.typecast_decimal(field.format_number(value))
        elif internal_type and internal_type.endswith('IntegerField') or internal_type == 'AutoField':
            return int(value)
        elif internal_type == 'DateField':
            return parse_date(value)
        elif internal_type == 'DateTimeField':
            return parse_datetime_with_timezone_support(value)
        elif internal_type == 'TimeField':
            return parse_time(value)

        # No field, or the field isn't known to be a decimal or integer
        return value

    def bulk_insert_sql(self, fields, num_values):
        res = []
        res.append("SELECT %s" % ", ".join(
            "%%s AS %s" % self.quote_name(f.column) for f in fields
        ))
        res.extend(["UNION ALL SELECT %s" % ", ".join(["%s"] * len(fields))] * (num_values - 1))
        return " ".join(res)


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'sqlite'
    # SQLite requires LIKE statements to include an ESCAPE clause if the value
    # being escaped has a percent or underscore in it.
    # See http://www.sqlite.org/lang_expr.html for an explanation.
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

    Database = Database

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def get_connection_params(self):
        settings_dict = self.settings_dict
        if not settings_dict['NAME']:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value.")
        kwargs = {
            'database': settings_dict['NAME'],
            'detect_types': Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
        }
        kwargs.update(settings_dict['OPTIONS'])
        # Always allow the underlying SQLite connection to be shareable
        # between multiple threads. The safe-guarding will be handled at a
        # higher level by the `BaseDatabaseWrapper.allow_thread_sharing`
        # property. This is necessary as the shareability is disabled by
        # default in pysqlite and it cannot be changed once a connection is
        # opened.
        if 'check_same_thread' in kwargs and kwargs['check_same_thread']:
            warnings.warn(
                'The `check_same_thread` option was provided and set to '
                'True. It will be overriden with False. Use the '
                '`DatabaseWrapper.allow_thread_sharing` property instead '
                'for controlling thread shareability.',
                RuntimeWarning
            )
        kwargs.update({'check_same_thread': False})
        return kwargs

    def get_new_connection(self, conn_params):
        conn = Database.connect(**conn_params)
        conn.create_function("django_date_extract", 2, _sqlite_date_extract)
        conn.create_function("django_date_trunc", 2, _sqlite_date_trunc)
        conn.create_function("django_datetime_extract", 3, _sqlite_datetime_extract)
        conn.create_function("django_datetime_trunc", 3, _sqlite_datetime_trunc)
        conn.create_function("regexp", 2, _sqlite_regexp)
        conn.create_function("django_format_dtdelta", 5, _sqlite_format_dtdelta)
        return conn

    def init_connection_state(self):
        pass

    def create_cursor(self):
        return self.connection.cursor(factory=SQLiteCursorWrapper)

    def close(self):
        self.validate_thread_sharing()
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if self.settings_dict['NAME'] != ":memory:":
            BaseDatabaseWrapper.close(self)

    def _savepoint_allowed(self):
        # When 'isolation_level' is not None, sqlite3 commits before each
        # savepoint; it's a bug. When it is None, savepoints don't make sense
        # because autocommit is enabled. The only exception is inside atomic
        # blocks. To work around that bug, on SQLite, atomic starts a
        # transaction explicitly rather than simply disable autocommit.
        return self.in_atomic_block

    def _set_autocommit(self, autocommit):
        if autocommit:
            level = None
        else:
            # sqlite3's internal default is ''. It's different from None.
            # See Modules/_sqlite/connection.c.
            level = ''
        # 'isolation_level' is a misleading API.
        # SQLite always runs at the SERIALIZABLE isolation level.
        self.connection.isolation_level = level

    def check_constraints(self, table_names=None):
        """
        Checks each table name in `table_names` for rows with invalid foreign key references. This method is
        intended to be used in conjunction with `disable_constraint_checking()` and `enable_constraint_checking()`, to
        determine if rows with invalid references were entered while constraint checks were off.

        Raises an IntegrityError on the first invalid foreign key reference encountered (if any) and provides
        detailed information about the invalid reference in the error message.

        Backends can override this method if they can more directly apply constraint checking (e.g. via "SET CONSTRAINTS
        ALL IMMEDIATE")
        """
        cursor = self.cursor()
        if table_names is None:
            table_names = self.introspection.table_names(cursor)
        for table_name in table_names:
            primary_key_column_name = self.introspection.get_primary_key_column(cursor, table_name)
            if not primary_key_column_name:
                continue
            key_columns = self.introspection.get_key_columns(cursor, table_name)
            for column_name, referenced_table_name, referenced_column_name in key_columns:
                cursor.execute("""
                    SELECT REFERRING.`%s`, REFERRING.`%s` FROM `%s` as REFERRING
                    LEFT JOIN `%s` as REFERRED
                    ON (REFERRING.`%s` = REFERRED.`%s`)
                    WHERE REFERRING.`%s` IS NOT NULL AND REFERRED.`%s` IS NULL"""
                    % (primary_key_column_name, column_name, table_name, referenced_table_name,
                    column_name, referenced_column_name, column_name, referenced_column_name))
                for bad_row in cursor.fetchall():
                    raise utils.IntegrityError("The row in table '%s' with primary key '%s' has an invalid "
                        "foreign key: %s.%s contains a value '%s' that does not have a corresponding value in %s.%s."
                        % (table_name, bad_row[0], table_name, column_name, bad_row[1],
                        referenced_table_name, referenced_column_name))

    def is_usable(self):
        return True

    def _start_transaction_under_autocommit(self):
        """
        Start a transaction explicitly in autocommit mode.

        Staying in autocommit mode works around a bug of sqlite3 that breaks
        savepoints when autocommit is disabled.
        """
        self.cursor().execute("BEGIN")

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
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    else:
        return getattr(dt, lookup_type)


def _sqlite_date_trunc(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i" % (dt.year, dt.month, dt.day)


def _sqlite_datetime_extract(lookup_type, dt, tzname):
    if dt is None:
        return None
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if tzname is not None:
        dt = timezone.localtime(dt, pytz.timezone(tzname))
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    else:
        return getattr(dt, lookup_type)


def _sqlite_datetime_trunc(lookup_type, dt, tzname):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if tzname is not None:
        dt = timezone.localtime(dt, pytz.timezone(tzname))
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)
    elif lookup_type == 'hour':
        return "%i-%02i-%02i %02i:00:00" % (dt.year, dt.month, dt.day, dt.hour)
    elif lookup_type == 'minute':
        return "%i-%02i-%02i %02i:%02i:00" % (dt.year, dt.month, dt.day, dt.hour, dt.minute)
    elif lookup_type == 'second':
        return "%i-%02i-%02i %02i:%02i:%02i" % (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def _sqlite_format_dtdelta(dt, conn, days, secs, usecs):
    try:
        dt = util.typecast_timestamp(dt)
        delta = datetime.timedelta(int(days), int(secs), int(usecs))
        if conn.strip() == '+':
            dt = dt + delta
        else:
            dt = dt - delta
    except (ValueError, TypeError):
        return None
    # typecast_timestamp returns a date or a datetime without timezone.
    # It will be formatted as "%Y-%m-%d" or "%Y-%m-%d %H:%M:%S[.%f]"
    return str(dt)


def _sqlite_regexp(re_pattern, re_string):
    return bool(re.search(re_pattern, force_text(re_string))) if re_string is not None else False
