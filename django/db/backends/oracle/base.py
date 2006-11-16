"""
Oracle database backend for Django.

Requires cx_Oracle: http://www.python.net/crew/atuining/cx_Oracle/
"""

from django.db.backends import util
try:
    import cx_Oracle as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading cx_Oracle module: %s" % e

DatabaseError = Database.Error

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
        self.options = kwargs

    def _valid_connection(self):
        return self.connection is not None

    def cursor(self):
        from django.conf import settings
        if not self._valid_connection():
            if len(settings.DATABASE_HOST.strip()) == 0:
                settings.DATABASE_HOST = 'localhost'
            if len(settings.DATABASE_PORT.strip()) != 0:
                dsn = Database.makedsn(settings.DATABASE_HOST, int(settings.DATABASE_PORT), settings.DATABASE_NAME)
                self.connection = Database.connect(settings.DATABASE_USER, settings.DATABASE_PASSWORD, dsn, **self.options)
            else:
                conn_string = "%s/%s@%s" % (settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME)
                self.connection = Database.connect(conn_string, **self.options)
        # set oracle date to ansi date format
        cursor = self.connection.cursor()
        cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'")
        cursor.close()
        return FormatStylePlaceholderCursor(self.connection)

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
uses_case_insensitive_names = True

class FormatStylePlaceholderCursor(Database.Cursor):
    """
    Django uses "format" (e.g. '%s') style placeholders, but Oracle uses ":var" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def _rewrite_args(self, query, params=None):
        if params is None:
            params = []
        args = [(':arg%d' % i) for i in range(len(params))]
        query = query % tuple(args)
        # cx_Oracle cannot execute a query with the closing ';'
        if query.endswith(';'):
            query = query[:-1]
        return query, params

    def execute(self, query, params=None):
        query, params = self._rewrite_args(query, params)
        self.arraysize = 200
        return Database.Cursor.execute(self, query, params)

    def executemany(self, query, params=None):
        query, params = self._rewrite_args(query, params)
        self.arraysize = 200
        return Database.Cursor.executemany(self, query, params)


def quote_name(name):
    # Oracle requires that quoted names be uppercase.
    name = name.upper()
    if not name.startswith('"') and not name.endswith('"'):
        name = '"%s"' % util.truncate_name(name.upper(), get_max_name_length())
    return name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute('SELECT %s_sq.currval FROM dual' % table_name)
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://download-east.oracle.com/docs/cd/B10501_01/server.920/a96540/functions42a.htm#1017163
    return "EXTRACT(%s FROM %s)" % (lookup_type, table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # Oracle uses TRUNC() for both dates and numbers.
    # http://download-east.oracle.com/docs/cd/B10501_01/server.920/a96540/functions155a.htm#SQLRF06151
    if lookup_type == 'day':
        sql = 'TRUNC(%s)' % (field_name,)
    else:
        sql = "TRUNC(%s, '%s')" % (field_name, lookup_type)
    return sql

def get_limit_offset_sql(limit, offset=None):
    # Limits and offset are too complicated to be handled here.
    # Instead, they are handled in django/db/backends/oracle/query.py.
    raise NotImplementedError

def get_random_function_sql():
    return "DBMS_RANDOM.RANDOM"

def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return "DROP FOREIGN KEY"

def get_pk_default_value():
    return "DEFAULT"

def get_max_name_length():
    return 30

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': "LIKE %s ESCAPE '\\'",
    'contains': "LIKE %s ESCAPE '\\'",
    'icontains': "LIKE %s ESCAPE '\\'",
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': "LIKE %s ESCAPE '\\'",
    'endswith': "LIKE %s ESCAPE '\\'",
    'istartswith': "LIKE %s ESCAPE '\\'",
    'iendswith': "LIKE %s ESCAPE '\\'",
}
