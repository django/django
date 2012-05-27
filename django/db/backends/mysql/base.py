"""
MySQL database backend for Django.

Requires MySQLdb: http://sourceforge.net/projects/mysql-python
"""

import datetime
import re
import sys
import warnings

try:
    import MySQLdb as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading MySQLdb module: %s" % e)

# We want version (1, 2, 1, 'final', 2) or later. We can't just use
# lexicographic ordering in this check because then (1, 2, 1, 'gamma')
# inadvertently passes the version test.
version = Database.version_info
if (version < (1,2,1) or (version[:3] == (1, 2, 1) and
        (len(version) < 5 or version[3] != 'final' or version[4] < 2))):
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("MySQLdb-1.2.1p2 or newer is required; you have %s" % Database.__version__)

from MySQLdb.converters import conversions, Thing2Literal
from MySQLdb.constants import FIELD_TYPE, CLIENT

from django.db import utils
from django.db.backends import *
from django.db.backends.signals import connection_created
from django.db.backends.mysql.client import DatabaseClient
from django.db.backends.mysql.creation import DatabaseCreation
from django.db.backends.mysql.introspection import DatabaseIntrospection
from django.db.backends.mysql.validation import DatabaseValidation
from django.utils.safestring import SafeString, SafeUnicode
from django.utils import timezone

# Raise exceptions for database warnings if DEBUG is on
from django.conf import settings
if settings.DEBUG:
    warnings.filterwarnings("error", category=Database.Warning)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

# It's impossible to import datetime_or_None directly from MySQLdb.times
parse_datetime = conversions[FIELD_TYPE.DATETIME]

def parse_datetime_with_timezone_support(value):
    dt = parse_datetime(value)
    # Confirm that dt is naive before overwriting its tzinfo.
    if dt is not None and settings.USE_TZ and timezone.is_naive(dt):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def adapt_datetime_with_timezone_support(value, conv):
    # Equivalent to DateTimeField.get_db_prep_value. Used only by raw SQL.
    if settings.USE_TZ:
        if timezone.is_naive(value):
            warnings.warn(u"SQLite received a naive datetime (%s)"
                          u" while time zone support is active." % value,
                          RuntimeWarning)
            default_timezone = timezone.get_default_timezone()
            value = timezone.make_aware(value, default_timezone)
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return Thing2Literal(value.strftime("%Y-%m-%d %H:%M:%S"), conv)

# MySQLdb-1.2.1 returns TIME columns as timedelta -- they are more like
# timedelta in terms of actual behavior as they are signed and include days --
# and Django expects time, so we still need to override that. We also need to
# add special handling for SafeUnicode and SafeString as MySQLdb's type
# checking is too tight to catch those (see Django ticket #6052).
# Finally, MySQLdb always returns naive datetime objects. However, when
# timezone support is active, Django expects timezone-aware datetime objects.
django_conversions = conversions.copy()
django_conversions.update({
    FIELD_TYPE.TIME: util.typecast_time,
    FIELD_TYPE.DECIMAL: util.typecast_decimal,
    FIELD_TYPE.NEWDECIMAL: util.typecast_decimal,
    FIELD_TYPE.DATETIME: parse_datetime_with_timezone_support,
    datetime.datetime: adapt_datetime_with_timezone_support,
})

# This should match the numerical portion of the version numbers (we can treat
# versions like 5.0.24 and 5.0.24a as the same). Based on the list of version
# at http://dev.mysql.com/doc/refman/4.1/en/news.html and
# http://dev.mysql.com/doc/refman/5.0/en/news.html .
server_version_re = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{1,2})')

# MySQLdb-1.2.1 and newer automatically makes use of SHOW WARNINGS on
# MySQL-4.1 and newer, so the MysqlDebugWrapper is unnecessary. Since the
# point is to raise Warnings as exceptions, this can be done with the Python
# warning module, and this is setup when the connection is created, and the
# standard util.CursorDebugWrapper can be used. Also, using sql_mode
# TRADITIONAL will automatically cause most warnings to be treated as errors.

class CursorWrapper(object):
    """
    A thin wrapper around MySQLdb's normal cursor class so that we can catch
    particular exception instances and reraise them with the right types.

    Implemented as a wrapper, rather than a subclass, so that we aren't stuck
    to the particular underlying representation returned by Connection.cursor().
    """
    codes_for_integrityerror = (1048,)

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, args=None):
        try:
            return self.cursor.execute(query, args)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.OperationalError, e:
            # Map some error codes to IntegrityError, since they seem to be
            # misclassified and Django would prefer the more logical place.
            if e[0] in self.codes_for_integrityerror:
                raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def executemany(self, query, args):
        try:
            return self.cursor.executemany(query, args)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.OperationalError, e:
            # Map some error codes to IntegrityError, since they seem to be
            # misclassified and Django would prefer the more logical place.
            if e[0] in self.codes_for_integrityerror:
                raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)

class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    update_can_self_select = False
    allows_group_by_pk = True
    related_fields_match_type = True
    allow_sliced_subqueries = False
    has_bulk_insert = True
    has_select_for_update = True
    has_select_for_update_nowait = False
    supports_forward_references = False
    supports_long_model_names = False
    supports_microsecond_precision = False
    supports_regex_backreferencing = False
    supports_date_lookup_using_string = False
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    allows_primary_key_0 = False

    def __init__(self, connection):
        super(DatabaseFeatures, self).__init__(connection)
        self._storage_engine = None

    def _mysql_storage_engine(self):
        "Internal method used in Django tests. Don't rely on this from your code"
        if self._storage_engine is None:
            cursor = self.connection.cursor()
            cursor.execute('CREATE TABLE INTROSPECT_TEST (X INT)')
            # This command is MySQL specific; the second column
            # will tell you the default table type of the created
            # table. Since all Django's test tables will have the same
            # table type, that's enough to evaluate the feature.
            cursor.execute("SHOW TABLE STATUS WHERE Name='INTROSPECT_TEST'")
            result = cursor.fetchone()
            cursor.execute('DROP TABLE INTROSPECT_TEST')
            self._storage_engine = result[1]
        return self._storage_engine

    def _can_introspect_foreign_keys(self):
        "Confirm support for introspected foreign keys"
        return self._mysql_storage_engine() != 'MyISAM'

class DatabaseOperations(BaseDatabaseOperations):
    compiler_module = "django.db.backends.mysql.compiler"

    def date_extract_sql(self, lookup_type, field_name):
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        if lookup_type == 'week_day':
            # DAYOFWEEK() returns an integer, 1-7, Sunday=1.
            # Note: WEEKDAY() returns 0-6, Monday=0.
            return "DAYOFWEEK(%s)" % field_name
        else:
            return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s') # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql

    def date_interval_sql(self, sql, connector, timedelta):
        return "(%s %s INTERVAL '%d 0:0:%d:%d' DAY_MICROSECOND)" % (sql, connector,
                timedelta.days, timedelta.seconds, timedelta.microseconds)

    def drop_foreignkey_sql(self):
        return "DROP FOREIGN KEY"

    def force_no_ordering(self):
        """
        "ORDER BY NULL" prevents MySQL from implicitly ordering by grouped
        columns. If no ordering would otherwise be applied, we don't want any
        implicit sorting going on.
        """
        return ["NULL"]

    def fulltext_search_sql(self, field_name):
        return 'MATCH (%s) AGAINST (%%s IN BOOLEAN MODE)' % field_name

    def last_executed_query(self, cursor, sql, params):
        # With MySQLdb, cursor objects have an (undocumented) "_last_executed"
        # attribute where the exact query sent to the database is saved.
        # See MySQLdb/cursors.py in the source distribution.
        return cursor._last_executed

    def no_limit_value(self):
        # 2**64 - 1, as recommended by the MySQL documentation
        return 18446744073709551615L

    def quote_name(self, name):
        if name.startswith("`") and name.endswith("`"):
            return name # Quoting once is enough.
        return "`%s`" % name

    def random_function_sql(self):
        return 'RAND()'

    def sql_flush(self, style, tables, sequences):
        # NB: The generated SQL below is specific to MySQL
        # 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
        # to clear all tables of all data
        if tables:
            sql = ['SET FOREIGN_KEY_CHECKS = 0;']
            for table in tables:
                sql.append('%s %s;' % (style.SQL_KEYWORD('TRUNCATE'), style.SQL_FIELD(self.quote_name(table))))
            sql.append('SET FOREIGN_KEY_CHECKS = 1;')

            # 'ALTER TABLE table AUTO_INCREMENT = 1;'... style SQL statements
            # to reset sequence indices
            sql.extend(["%s %s %s %s %s;" % \
                (style.SQL_KEYWORD('ALTER'),
                 style.SQL_KEYWORD('TABLE'),
                 style.SQL_TABLE(self.quote_name(sequence['table'])),
                 style.SQL_KEYWORD('AUTO_INCREMENT'),
                 style.SQL_FIELD('= 1'),
                ) for sequence in sequences])
            return sql
        else:
            return []

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("MySQL backend does not support timezone-aware datetimes when USE_TZ is False.")

        # MySQL doesn't support microseconds
        return unicode(value.replace(microsecond=0))

    def value_to_db_time(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware times
        if timezone.is_aware(value):
            raise ValueError("MySQL backend does not support timezone-aware times.")

        # MySQL doesn't support microseconds
        return unicode(value.replace(microsecond=0))

    def year_lookup_bounds(self, value):
        # Again, no microseconds
        first = '%s-01-01 00:00:00'
        second = '%s-12-31 23:59:59.99'
        return [first % value, second % value]

    def max_name_length(self):
        return 64

    def bulk_insert_sql(self, fields, num_values):
        items_sql = "(%s)" % ", ".join(["%s"] * len(fields))
        return "VALUES " + ", ".join([items_sql] * num_values)

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT %s" % sid

    def savepoint_commit_sql(self, sid):
        return "RELEASE SAVEPOINT %s" % sid

    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT %s" % sid

class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'mysql'
    operators = {
        'exact': '= %s',
        'iexact': 'LIKE %s',
        'contains': 'LIKE BINARY %s',
        'icontains': 'LIKE %s',
        'regex': 'REGEXP BINARY %s',
        'iregex': 'REGEXP %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE BINARY %s',
        'endswith': 'LIKE BINARY %s',
        'istartswith': 'LIKE %s',
        'iendswith': 'LIKE %s',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.server_version = None
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = DatabaseValidation(self)

    def _valid_connection(self):
        if self.connection is not None:
            try:
                self.connection.ping()
                return True
            except DatabaseError:
                self.connection.close()
                self.connection = None
        return False

    def _cursor(self):
        new_connection = False
        if not self._valid_connection():
            new_connection = True
            kwargs = {
                'conv': django_conversions,
                'charset': 'utf8',
                'use_unicode': True,
            }
            settings_dict = self.settings_dict
            if settings_dict['USER']:
                kwargs['user'] = settings_dict['USER']
            if settings_dict['NAME']:
                kwargs['db'] = settings_dict['NAME']
            if settings_dict['PASSWORD']:
                kwargs['passwd'] = settings_dict['PASSWORD']
            if settings_dict['HOST'].startswith('/'):
                kwargs['unix_socket'] = settings_dict['HOST']
            elif settings_dict['HOST']:
                kwargs['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                kwargs['port'] = int(settings_dict['PORT'])
            # We need the number of potentially affected rows after an
            # "UPDATE", not the number of changed rows.
            kwargs['client_flag'] = CLIENT.FOUND_ROWS
            kwargs.update(settings_dict['OPTIONS'])
            self.connection = Database.connect(**kwargs)
            self.connection.encoders[SafeUnicode] = self.connection.encoders[unicode]
            self.connection.encoders[SafeString] = self.connection.encoders[str]
            self.features.uses_savepoints = \
                self.get_server_version() >= (5, 0, 3)
            connection_created.send(sender=self.__class__, connection=self)
        cursor = self.connection.cursor()
        if new_connection:
            # SQL_AUTO_IS_NULL in MySQL controls whether an AUTO_INCREMENT column
            # on a recently-inserted row will return when the field is tested for
            # NULL.  Disabling this value brings this aspect of MySQL in line with
            # SQL standards.
            cursor.execute('SET SQL_AUTO_IS_NULL = 0')
        return CursorWrapper(cursor)

    def _rollback(self):
        try:
            BaseDatabaseWrapper._rollback(self)
        except Database.NotSupportedError:
            pass

    def get_server_version(self):
        if not self.server_version:
            new_connection = False
            if not self._valid_connection():
                # Ensure we have a connection with the DB by using a temporary
                # cursor
                new_connection = True
                self.cursor().close()
            server_info = self.connection.get_server_info()
            if new_connection:
                # Make sure we close the connection
                self.connection.close()
                self.connection = None
            m = server_version_re.match(server_info)
            if not m:
                raise Exception('Unable to determine MySQL version from version string %r' % server_info)
            self.server_version = tuple([int(x) for x in m.groups()])
        return self.server_version

    def disable_constraint_checking(self):
        """
        Disables foreign key checks, primarily for use in adding rows with forward references. Always returns True,
        to indicate constraint checks need to be re-enabled.
        """
        self.cursor().execute('SET foreign_key_checks=0')
        return True

    def enable_constraint_checking(self):
        """
        Re-enable foreign key checks after they have been disabled.
        """
        self.cursor().execute('SET foreign_key_checks=1')

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
            table_names = self.introspection.get_table_list(cursor)
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
                        % (table_name, bad_row[0],
                        table_name, column_name, bad_row[1],
                        referenced_table_name, referenced_column_name))
