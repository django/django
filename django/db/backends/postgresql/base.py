"""
PostgreSQL database backend for Django.

Requires psycopg 1: http://initd.org/projects/psycopg1
"""

from django.db.backends import util
try:
    import psycopg as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading psycopg module: %s" % e

DatabaseError = Database.DatabaseError

try:
    # Only exists in Python 2.4+
    from threading import local
except ImportError:
    # Import copy of _thread_local.py from Python 2.4
    from django.utils._threading_local import local

def smart_basestring(s, charset):
    if isinstance(s, unicode):
        return s.encode(charset)
    return s

class UnicodeCursorWrapper(object):
    """
    A thin wrapper around psycopg cursors that allows them to accept Unicode
    strings as params.

    This is necessary because psycopg doesn't apply any DB quoting to
    parameters that are Unicode strings. If a param is Unicode, this will
    convert it to a bytestring using DEFAULT_CHARSET before passing it to
    psycopg.
    """
    def __init__(self, cursor, charset):
        self.cursor = cursor
        self.charset = charset

    def execute(self, sql, params=()):
        return self.cursor.execute(sql, [smart_basestring(p, self.charset) for p in params])

    def executemany(self, sql, param_list):
        new_param_list = [tuple([smart_basestring(p, self.charset) for p in params]) for params in param_list]
        return self.cursor.executemany(sql, new_param_list)

    def __getattr__(self, attr):
        if self.__dict__.has_key(attr):
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

postgres_version = None

class DatabaseWrapper(local):
    def __init__(self, **kwargs):
        self.connection = None
        self.queries = []
        self.options = kwargs

    def cursor(self):
        from django.conf import settings
        set_tz = False
        if self.connection is None:
            set_tz = True
            if settings.DATABASE_NAME == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "You need to specify DATABASE_NAME in your Django settings file."
            conn_string = "dbname=%s" % settings.DATABASE_NAME
            if settings.DATABASE_USER:
                conn_string = "user=%s %s" % (settings.DATABASE_USER, conn_string)
            if settings.DATABASE_PASSWORD:
                conn_string += " password='%s'" % settings.DATABASE_PASSWORD
            if settings.DATABASE_HOST:
                conn_string += " host=%s" % settings.DATABASE_HOST
            if settings.DATABASE_PORT:
                conn_string += " port=%s" % settings.DATABASE_PORT
            self.connection = Database.connect(conn_string, **self.options)
            self.connection.set_isolation_level(1) # make transactions transparent to all cursors
        cursor = self.connection.cursor()
        if set_tz:
            cursor.execute("SET TIME ZONE %s", [settings.TIME_ZONE])
        cursor = UnicodeCursorWrapper(cursor, settings.DEFAULT_CHARSET)
        global postgres_version
        if not postgres_version:
            cursor.execute("SELECT version()")
            postgres_version = [int(val) for val in cursor.fetchone()[0].split()[1].split('.')]        
        if settings.DEBUG:
            return util.CursorDebugWrapper(cursor, self)
        return cursor

    def _commit(self):
        return self.connection.commit()

    def _rollback(self):
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

def get_deferrable_sql():
    return " DEFERRABLE INITIALLY DEFERRED"
    
def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return "DROP CONSTRAINT"

def get_pk_default_value():
    return "DEFAULT"

def get_sql_flush(style, tables, sequences):
    """Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state
    
    """    
    if tables:
        if postgres_version[0] >= 8 and postgres_version[1] >= 1:
            # Postgres 8.1+ can do 'TRUNCATE x, y, z...;'. In fact, it *has to* in order to be able to
            # truncate tables referenced by a foreign key in any other table. The result is a
            # single SQL TRUNCATE statement.
            sql = ['%s %s;' % \
                (style.SQL_KEYWORD('TRUNCATE'),
                 style.SQL_FIELD(', '.join(quote_name(table) for table in tables))
            )]
        else:
            # Older versions of Postgres can't do TRUNCATE in a single call, so they must use 
            # a simple delete.
            sql = ['%s %s %s;' % \
                    (style.SQL_KEYWORD('DELETE'),
                     style.SQL_KEYWORD('FROM'),
                     style.SQL_FIELD(quote_name(table))
                     ) for table in tables]

        # 'ALTER SEQUENCE sequence_name RESTART WITH 1;'... style SQL statements
        # to reset sequence indices
        for sequence_info in sequences:
            table_name = sequence_info['table']
            column_name = sequence_info['column']
            if column_name and len(column_name)>0:
                # sequence name in this case will be <table>_<column>_seq
                sql.append("%s %s %s %s %s %s;" % \
                    (style.SQL_KEYWORD('ALTER'),
                    style.SQL_KEYWORD('SEQUENCE'),
                    style.SQL_FIELD('%s_%s_seq' % (table_name, column_name)),
                    style.SQL_KEYWORD('RESTART'),
                    style.SQL_KEYWORD('WITH'),
                    style.SQL_FIELD('1')
                    )
                )
            else:
                # sequence name in this case will be <table>_id_seq
                sql.append("%s %s %s %s %s %s;" % \
                    (style.SQL_KEYWORD('ALTER'),
                     style.SQL_KEYWORD('SEQUENCE'),
                     style.SQL_FIELD('%s_id_seq' % table_name),
                     style.SQL_KEYWORD('RESTART'),
                     style.SQL_KEYWORD('WITH'),
                     style.SQL_FIELD('1')
                     )
                )
        return sql
    else:
        return []

        
# Register these custom typecasts, because Django expects dates/times to be
# in Python's native (standard-library) datetime/time format, whereas psycopg
# use mx.DateTime by default.
try:
    Database.register_type(Database.new_type((1082,), "DATE", util.typecast_date))
except AttributeError:
    raise Exception, "You appear to be using psycopg version 2. Set your DATABASE_ENGINE to 'postgresql_psycopg2' instead of 'postgresql'."
Database.register_type(Database.new_type((1083,1266), "TIME", util.typecast_time))
Database.register_type(Database.new_type((1114,1184), "TIMESTAMP", util.typecast_timestamp))
Database.register_type(Database.new_type((16,), "BOOLEAN", util.typecast_boolean))

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'ILIKE %s',
    'contains': 'LIKE %s',
    'icontains': 'ILIKE %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE %s',
    'endswith': 'LIKE %s',
    'istartswith': 'ILIKE %s',
    'iendswith': 'ILIKE %s',
}
