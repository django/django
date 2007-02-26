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

class FormatStylePlaceholderCursor(Database.Cursor):
    """
    Django uses "format" (e.g. '%s') style placeholders, but Oracle uses ":var" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def execute(self, query, params=None):
        if params is None: params = []
        query = self.convert_arguments(query, len(params))
        return Database.Cursor.execute(self, query, params)

    def executemany(self, query, params=None):
        if params is None: params = []
        query = self.convert_arguments(query, len(params[0]))
        return Database.Cursor.executemany(self, query, params)

    def convert_arguments(self, query, num_params):
        # replace occurances of "%s" with ":arg" - Oracle requires colons for parameter placeholders.
        args = [':arg' for i in range(num_params)]
        return query % tuple(args)

def quote_name(name):
    return name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    query = "SELECT %s_sq.currval from dual" % table_name
    cursor.execute(query)
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://www.psoug.org/reference/date_func.html
    return "EXTRACT(%s FROM %s)" % (lookup_type, table_name)

def get_date_trunc_sql(lookup_type, field_name):
    return "EXTRACT(%s FROM TRUNC(%s))" % (lookup_type, field_name)

def get_limit_offset_sql(limit, offset=None):
    # Limits and offset are too complicated to be handled here.
    # Instead, they are handled in django/db/query.py.
    pass

def get_random_function_sql():
    return "DBMS_RANDOM.RANDOM"

def get_deferrable_sql():
    return " DEFERRABLE INITIALLY DEFERRED"

def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return "DROP FOREIGN KEY"

def get_pk_default_value():
    return "DEFAULT"

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'LIKE %s',
    'contains': 'LIKE %s',
    'icontains': 'LIKE %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE %s',
    'endswith': 'LIKE %s',
    'istartswith': 'LIKE %s',
    'iendswith': 'LIKE %s',
}
