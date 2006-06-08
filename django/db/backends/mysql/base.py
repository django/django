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
from MySQLdb.converters import conversions
from MySQLdb.constants import FIELD_TYPE
import types

DatabaseError = Database.DatabaseError

django_conversions = conversions.copy()
django_conversions.update({
    types.BooleanType: util.rev_typecast_boolean,
    FIELD_TYPE.DATETIME: util.typecast_timestamp,
    FIELD_TYPE.DATE: util.typecast_date,
    FIELD_TYPE.TIME: util.typecast_time,
})

# This is an extra debug layer over MySQL queries, to display warnings.
# It's only used when DEBUG=True.
class MysqlDebugWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=()):
        try:
            return self.cursor.execute(sql, params)
        except Database.Warning, w:
            self.cursor.execute("SHOW WARNINGS")
            raise Database.Warning, "%s: %s" % (w, self.cursor.fetchall())

    def executemany(self, sql, param_list):
        try:
            return self.cursor.executemany(sql, param_list)
        except Database.Warning:
            self.cursor.execute("SHOW WARNINGS")
            raise Database.Warning, "%s: %s" % (w, self.cursor.fetchall())

    def __getattr__(self, attr):
        if self.__dict__.has_key(attr):
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

class DatabaseWrapper(local):
    def __init__(self):
        self.connection = None
        self.queries = []

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
        if not self._valid_connection():
            kwargs = {
                'user': settings.DATABASE_USER,
                'db': settings.DATABASE_NAME,
                'passwd': settings.DATABASE_PASSWORD,
                'conv': django_conversions,
            }
            if settings.DATABASE_HOST.startswith('/'):
                kwargs['unix_socket'] = settings.DATABASE_HOST
            else:
                kwargs['host'] = settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                kwargs['port'] = int(settings.DATABASE_PORT)
            self.connection = Database.connect(**kwargs)
        cursor = self.connection.cursor()
        if self.connection.get_server_info() >= '4.1':
            cursor.execute("SET NAMES 'utf8'")
        if settings.DEBUG:
            return util.CursorDebugWrapper(MysqlDebugWrapper(cursor), self)
        return cursor

    def _commit(self):
        self.connection.commit()

    def _rollback(self):
        if self.connection:
            try:
                self.connection.rollback()
            except Database.NotSupportedError:
                pass

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

supports_constraints = True

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

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT "
    if offset and offset != 0:
        sql += "%s," % offset
    return sql + str(limit)

def get_random_function_sql():
    return "RAND()"

def get_fulltext_search_sql(field_name):
    return 'MATCH (%s) AGAINST (%%s IN BOOLEAN MODE)' % field_name

def get_drop_foreignkey_sql():
    return "DROP FOREIGN KEY"

def get_pk_default_value():
    return "DEFAULT"

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
