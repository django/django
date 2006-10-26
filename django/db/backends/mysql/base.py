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
import re

DatabaseError = Database.DatabaseError

django_conversions = conversions.copy()
django_conversions.update({
    types.BooleanType: util.rev_typecast_boolean,
    FIELD_TYPE.DATETIME: util.typecast_timestamp,
    FIELD_TYPE.DATE: util.typecast_date,
    FIELD_TYPE.TIME: util.typecast_time,
})

# This should match the numerical portion of the version numbers (we can treat
# versions like 5.0.24 and 5.0.24a as the same). Based on the list of version
# at http://dev.mysql.com/doc/refman/4.1/en/news.html and
# http://dev.mysql.com/doc/refman/5.0/en/news.html .
server_version_re = re.compile(r'(\d{1,2})\.(\d{1,2})\.(\d{1,2})')

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
        except Database.Warning, w:
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
        self.server_version = None

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

    def get_server_version(self):
        if not self.server_version:
            if not self._valid_connection():
                self.cursor()
            m = server_version_re.match(self.connection.get_server_info())
            if not m:
                raise Exception('Unable to determine MySQL version from version string %r' % self.connection.get_server_info())
            self.server_version = tuple([int(x) for x in m.groups()])
        return self.server_version

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

def get_change_column_name_sql( table_name, indexes, old_col_name, new_col_name, col_def ):
    # mysql doesn't support column renames (AFAIK), so we fake it
    # TODO: only supports a single primary key so far
    pk_name = None
    for key in indexes.keys():
        if indexes[key]['primary_key']: pk_name = key
    output = []
    output.append( 'ALTER TABLE '+ quote_name(table_name) +' CHANGE COLUMN '+ quote_name(old_col_name) +' '+ quote_name(new_col_name) +' '+ col_def + ';' )
    return '\n'.join(output)

def get_change_column_def_sql( table_name, col_name, col_type, null, unique, primary_key ):
    output = []
    col_def = col_type +' '+ ('%sNULL' % (not null and 'NOT ' or ''))
    if unique:
        col_def += ' '+ 'UNIQUE'
    if primary_key:
        col_def += ' '+ 'PRIMARY KEY'
    output.append( 'ALTER TABLE '+ quote_name(table_name) +' MODIFY COLUMN '+ quote_name(col_name) +' '+ col_def + ';' )
    return '\n'.join(output)

def get_add_column_sql( table_name, col_name, col_type, null, unique, primary_key  ):
    output = []
    field_output = []
    field_output.append('ALTER TABLE')
    field_output.append(quote_name(table_name))
    field_output.append('ADD COLUMN')
    field_output.append(quote_name(col_name))
    field_output.append(col_type)
    field_output.append(('%sNULL' % (not null and 'NOT ' or '')))
    if unique:
        field_output.append(('UNIQUE'))
    if primary_key:
        field_output.append(('PRIMARY KEY'))
    output.append(' '.join(field_output) + ';')
    return '\n'.join(output)

def get_drop_column_sql( table_name, col_name ):
    output = []
    output.append( '-- ALTER TABLE '+ quote_name(table_name) +' DROP COLUMN '+ quote_name(col_name) + ';' )
    return '\n'.join(output)
    
    
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
