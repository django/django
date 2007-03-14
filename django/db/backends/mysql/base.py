"""
MySQL database backend for Django.

Requires MySQLdb: http://sourceforge.net/projects/mysql-python
"""

from django.db.backends import util
try:
    import MySQLdb as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading MySQLdb module: %s" % e
if Database.version_info < (1,2,1,'final',2):
    raise ImportError, "MySQLdb-1.2.1p2 or newer is required; you have %s" % MySQLdb.__version__

from MySQLdb.converters import conversions
from MySQLdb.constants import FIELD_TYPE
import types
import re

DatabaseError = Database.DatabaseError

# MySQLdb-1.2.1 supports the Python boolean type, and only uses datetime
# module for time-related columns; older versions could have used mx.DateTime
# or strings if there were no datetime module. However, MySQLdb still returns
# TIME columns as timedelta -- they are more like timedelta in terms of actual
# behavior as they are signed and include days -- and Django expects time, so
# we still need to override that.
django_conversions = conversions.copy()
django_conversions.update({
    FIELD_TYPE.TIME: util.typecast_time,
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

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

class DatabaseWrapper(local):
    def __init__(self, **kwargs):
        self.connection = None
        self.queries = []
        self.server_version = None
        self.options = kwargs

    def _valid_connection(self):
        if self.connection is not None:
            try:
                self.connection.ping()
                return True
            except DatabaseError:
                self.connection.close()
                self.connection = None
        return False

    def cursor(self):
        from django.conf import settings
        from warnings import filterwarnings
        if not self._valid_connection():
            kwargs = {
                'conv': django_conversions,
            }
            if settings.DATABASE_USER:
                kwargs['user'] = settings.DATABASE_USER
            if settings.DATABASE_NAME:
                kwargs['db'] = settings.DATABASE_NAME
            if settings.DATABASE_PASSWORD:
                kwargs['passwd'] = settings.DATABASE_PASSWORD
            if settings.DATABASE_HOST.startswith('/'):
                kwargs['unix_socket'] = settings.DATABASE_HOST
            elif settings.DATABASE_HOST:
                kwargs['host'] = settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                kwargs['port'] = int(settings.DATABASE_PORT)
            kwargs.update(self.options)
            self.connection = Database.connect(**kwargs)
            cursor = self.connection.cursor()
        else:
            cursor = self.connection.cursor()
        if settings.DEBUG:
            filterwarnings("error", category=Database.Warning)
            return util.CursorDebugWrapper(cursor, self)
        return cursor

    def _commit(self):
        if self.connection is not None:
            self.connection.commit()

    def _rollback(self):
        if self.connection is not None:
            try:
                self.connection.rollback()
            except Database.NotSupportedError:
                pass

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def get_server_version(self):
        if not self.server_version:
            if not self._valid_connection():
                self.cursor()
            m = server_version_re.match(self.connection.get_server_info())
            if not m:
                raise Exception('Unable to determine MySQL version from version string %r' % self.connection.get_server_info())
            self.server_version = tuple([int(x) for x in m.groups()])
        return self.server_version

allows_group_by_ordinal = True
allows_unique_and_pk = True
needs_datetime_string_cast = True     # MySQLdb requires a typecast for dates
supports_constraints = True
uses_case_insensitive_names = False

def quote_name(name):
    if name.startswith("`") and name.endswith("`"):
        return name # Quoting once is enough.
    return "`%s`" % name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    return cursor.lastrowid

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
    return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
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

def get_datetime_cast_sql():
    return None

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT "
    if offset and offset != 0:
        sql += "%s," % offset
    return sql + str(limit)

def get_random_function_sql():
    return "RAND()"

def get_deferrable_sql():
    return ""

def get_fulltext_search_sql(field_name):
    return 'MATCH (%s) AGAINST (%%s IN BOOLEAN MODE)' % field_name

def get_drop_foreignkey_sql():
    return "DROP FOREIGN KEY"

def get_pk_default_value():
    return "DEFAULT"

def get_max_name_length():
    return 64;

def get_autoinc_sql(table):
    return None

def get_sql_flush(style, tables, sequences):
    """Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state

    """
    # NB: The generated SQL below is specific to MySQL
    # 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
    # to clear all tables of all data
    if tables:
        sql = ['SET FOREIGN_KEY_CHECKS = 0;'] + \
              ['%s %s;' % \
                (style.SQL_KEYWORD('TRUNCATE'),
                 style.SQL_FIELD(quote_name(table))
                )  for table in tables] + \
              ['SET FOREIGN_KEY_CHECKS = 1;']

        # 'ALTER TABLE table AUTO_INCREMENT = 1;'... style SQL statements
        # to reset sequence indices
        sql.extend(["%s %s %s %s %s;" % \
            (style.SQL_KEYWORD('ALTER'),
             style.SQL_KEYWORD('TABLE'),
             style.SQL_TABLE(quote_name(sequence['table'])),
             style.SQL_KEYWORD('AUTO_INCREMENT'),
             style.SQL_FIELD('= 1'),
            ) for sequence in sequences])
        return sql
    else:
        return []

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'LIKE %s',
    'contains': 'LIKE BINARY %s',
    'icontains': 'LIKE %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE BINARY %s',
    'endswith': 'LIKE BINARY %s',
    'istartswith': 'LIKE %s',
    'iendswith': 'LIKE %s',
}
