"""
PostgreSQL database backend for Django.

Requires psycopg 1: http://initd.org/projects/psycopg1
"""

from django.db.backends import util
import psycopg as Database

DatabaseError = Database.DatabaseError

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_USER, DATABASE_NAME, DATABASE_HOST, DATABASE_PORT, DATABASE_PASSWORD, DEBUG, TIME_ZONE
        if self.connection is None:
            if DATABASE_NAME == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "You need to specify DATABASE_NAME in your Django settings file."
            conn_string = "dbname=%s" % DATABASE_NAME
            if DATABASE_USER:
                conn_string = "user=%s %s" % (DATABASE_USER, conn_string)
            if DATABASE_PASSWORD:
                conn_string += " password='%s'" % DATABASE_PASSWORD
            if DATABASE_HOST:
                conn_string += " host=%s" % DATABASE_HOST
            if DATABASE_PORT:
                conn_string += " port=%s" % DATABASE_PORT
            self.connection = Database.connect(conn_string)
            self.connection.set_isolation_level(1) # make transactions transparent to all cursors
        cursor = self.connection.cursor()
        cursor.execute("SET TIME ZONE %s", [TIME_ZONE])
        if DEBUG:
            return util.CursorDebugWrapper(cursor, self)
        return cursor

    def commit(self):
        return self.connection.commit()

    def rollback(self):
        if self.connection:
            return self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

supports_constraints = True

def quote_name(name):
    if name.startswith('"') and name.endswith('"'):
        return name # Quoting once is enough.
    return '"%s"' % name

def dictfetchone(cursor):
    "Returns a row from the cursor as a dict"
    return cursor.dictfetchone()

def dictfetchmany(cursor, number):
    "Returns a certain number of rows from a cursor as a dict"
    return cursor.dictfetchmany(number)

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    return cursor.dictfetchall()

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute("SELECT CURRVAL('\"%s_%s_seq\"')" % (table_name, pk_name))
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-EXTRACT
    return "EXTRACT('%s' FROM %s)" % (lookup_type, table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # http://www.postgresql.org/docs/8.0/static/functions-datetime.html#FUNCTIONS-DATETIME-TRUNC
    return "DATE_TRUNC('%s', %s)" % (lookup_type, field_name)

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT %s" % limit
    if offset and offset != 0:
        sql += " OFFSET %s" % offset
    return sql

def get_random_function_sql():
    return "RANDOM()"

# Register these custom typecasts, because Django expects dates/times to be
# in Python's native (standard-library) datetime/time format, whereas psycopg
# use mx.DateTime by default.
try:
    Database.register_type(Database.new_type((1082,), "DATE", util.typecast_date))
except AttributeError:
    raise Exception, "You appear to be using psycopg version 2, which isn't supported yet, because it's still in beta. Use psycopg version 1 instead: http://initd.org/projects/psycopg1"
Database.register_type(Database.new_type((1083,1266), "TIME", util.typecast_time))
Database.register_type(Database.new_type((1114,1184), "TIMESTAMP", util.typecast_timestamp))
Database.register_type(Database.new_type((16,), "BOOLEAN", util.typecast_boolean))

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'ILIKE %s',
    'contains': 'LIKE %s',
    'icontains': 'ILIKE %s',
    'ne': '!= %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE %s',
    'endswith': 'LIKE %s',
    'istartswith': 'ILIKE %s',
    'iendswith': 'ILIKE %s',
}
