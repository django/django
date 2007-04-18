"""
ADO MSSQL database backend for Django.

Requires adodbapi 2.0.1: http://adodbapi.sourceforge.net/
"""

from django.db.backends import util
try:
    import adodbapi as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading adodbapi module: %s" % e
import datetime
try:
    import mx
except ImportError:
    mx = None

DatabaseError = Database.DatabaseError

# We need to use a special Cursor class because adodbapi expects question-mark
# param style, but Django expects "%s". This cursor converts question marks to
# format-string style.
class Cursor(Database.Cursor):
    def executeHelper(self, operation, isStoredProcedureCall, parameters=None):
        if parameters is not None and "%s" in operation:
            operation = operation.replace("%s", "?")
        Database.Cursor.executeHelper(self, operation, isStoredProcedureCall, parameters)

class Connection(Database.Connection):
    def cursor(self):
        return Cursor(self)
Database.Connection = Connection

origCVtoP = Database.convertVariantToPython
def variantToPython(variant, adType):
    if type(variant) == bool and adType == 11:
        return variant  # bool not 1/0
    res = origCVtoP(variant, adType)
    if mx is not None and type(res) == mx.DateTime.mxDateTime.DateTimeType:
        # Convert ms.DateTime objects to Python datetime.datetime objects.
        tv = list(res.tuple()[:7])
        tv[-2] = int(tv[-2])
        return datetime.datetime(*tuple(tv))
    if type(res) == float and str(res)[-2:] == ".0":
        return int(res) # If float but int, then int.
    return res
Database.convertVariantToPython = variantToPython

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

    def cursor(self):
        from django.conf import settings
        if self.connection is None:
            if settings.DATABASE_NAME == '' or settings.DATABASE_USER == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "You need to specify both DATABASE_NAME and DATABASE_USER in your Django settings file."
            if not settings.DATABASE_HOST:
                settings.DATABASE_HOST = "127.0.0.1"
            # TODO: Handle DATABASE_PORT.
            conn_string = "PROVIDER=SQLOLEDB;DATA SOURCE=%s;UID=%s;PWD=%s;DATABASE=%s" % (settings.DATABASE_HOST, settings.DATABASE_USER, settings.DATABASE_PASSWORD, settings.DATABASE_NAME)
            self.connection = Database.connect(conn_string)
        cursor = self.connection.cursor()
        if settings.DEBUG:
            return util.CursorDebugWrapper(cursor, self)
        return cursor

    def _commit(self):
        if self.connection is not None:
            return self.connection.commit()

    def _rollback(self):
        if self.connection is not None:
            return self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

allows_group_by_ordinal = True
allows_unique_and_pk = True
autoindexes_primary_keys = True
needs_datetime_string_cast = True
needs_upper_for_iops = False
supports_constraints = True
supports_tablespaces = True
uses_case_insensitive_names = False

def quote_name(name):
    if name.startswith('[') and name.endswith(']'):
        return name # Quoting once is enough.
    return '[%s]' % name

dictfetchone = util.dictfetchone
dictfetchmany = util.dictfetchmany
dictfetchall  = util.dictfetchall

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute("SELECT %s FROM %s WHERE %s = @@IDENTITY" % (pk_name, table_name, pk_name))
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    return "DATEPART(%s, %s)" % (lookup_type, table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    if lookup_type=='year':
        return "Convert(datetime, Convert(varchar, DATEPART(year, %s)) + '/01/01')" % field_name
    if lookup_type=='month':
        return "Convert(datetime, Convert(varchar, DATEPART(year, %s)) + '/' + Convert(varchar, DATEPART(month, %s)) + '/01')" % (field_name, field_name)
    if lookup_type=='day':
        return "Convert(datetime, Convert(varchar(12), %s))" % field_name

def get_datetime_cast_sql():
    return None

def get_limit_offset_sql(limit, offset=None):
    # TODO: This is a guess. Make sure this is correct.
    sql = "LIMIT %s" % limit
    if offset and offset != 0:
        sql += " OFFSET %s" % offset
    return sql

def get_random_function_sql():
    return "RAND()"

def get_deferrable_sql():
    return " DEFERRABLE INITIALLY DEFERRED"

def get_fulltext_search_sql(field_name):
    raise NotImplementedError

def get_drop_foreignkey_sql():
    return "DROP CONSTRAINT"

def get_pk_default_value():
    return "DEFAULT"

def get_max_name_length():
    return None

def get_start_transaction_sql():
    return "BEGIN;"

def get_tablespace_sql():
    return "ON %s"

def get_autoinc_sql(table):
    return None

def get_sql_flush(style, tables, sequences):
    """Return a list of SQL statements required to remove all data from
    all tables in the database (without actually removing the tables
    themselves) and put the database in an empty 'initial' state
    """
    # Return a list of 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
    # TODO - SQL not actually tested against ADO MSSQL yet!
    # TODO - autoincrement indices reset required? See other get_sql_flush() implementations
    sql_list = ['%s %s;' % \
                (style.SQL_KEYWORD('TRUNCATE'),
                 style.SQL_FIELD(quote_name(table))
                 )  for table in tables]

def get_sql_sequence_reset(style, model_list):
    "Returns a list of the SQL statements to reset sequences for the given models."
    # No sequence reset required
    return []

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
