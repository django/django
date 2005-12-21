"""
MySQL database backend for Django.

Requires MySQLdb: http://sourceforge.net/projects/mysql-python
"""

from django.db.backends import util
import MySQLdb as Database
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

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_USER, DATABASE_NAME, DATABASE_HOST, DATABASE_PORT, DATABASE_PASSWORD, DEBUG
        if self.connection is None:
            kwargs = {
                'user': DATABASE_USER,
                'db': DATABASE_NAME,
                'passwd': DATABASE_PASSWORD,
                'host': DATABASE_HOST,
                'conv': django_conversions,
            }
            if DATABASE_PORT:
                kwargs['port'] = DATABASE_PORT
            self.connection = Database.connect(**kwargs)
        if DEBUG:
            return util.CursorDebugWrapper(MysqlDebugWrapper(self.connection.cursor()), self)
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
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
    cursor.execute("SELECT LAST_INSERT_ID()")
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
    return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
    # MySQL doesn't support DATE_TRUNC, so we fake it by subtracting intervals.
    # If you know of a better way to do this, please file a Django ticket.
    subtractions = ["interval (DATE_FORMAT(%s, '%%%%s')) second - interval (DATE_FORMAT(%s, '%%%%i')) minute - interval (DATE_FORMAT(%s, '%%%%H')) hour" % (field_name, field_name, field_name)]
    if lookup_type in ('year', 'month'):
        subtractions.append(" - interval (DATE_FORMAT(%s, '%%%%e')-1) day" % field_name)
    if lookup_type == 'year':
        subtractions.append(" - interval (DATE_FORMAT(%s, '%%%%m')-1) month" % field_name)
    return "(%s - %s)" % (field_name, ''.join(subtractions))

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT "
    if offset and offset != 0:
        sql += "%s," % offset
    return sql + str(limit)

def get_random_function_sql():
    return "RAND()"

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'LIKE %s',
    'contains': 'LIKE BINARY %s',
    'icontains': 'LIKE %s',
    'ne': '!= %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE BINARY %s',
    'endswith': 'LIKE BINARY %s',
    'istartswith': 'LIKE %s',
    'iendswith': 'LIKE %s',
}
