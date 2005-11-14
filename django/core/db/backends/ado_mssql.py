"""
ADO MSSQL database backend for Django.

Requires adodbapi 2.0.1: http://adodbapi.sourceforge.net/
"""

from django.core.db import base
from django.core.db.dicthelpers import *
import adodbapi as Database
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

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_USER, DATABASE_NAME, DATABASE_HOST, DATABASE_PORT, DATABASE_PASSWORD, DEBUG
        if self.connection is None:
            if DATABASE_NAME == '' or DATABASE_USER == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "You need to specify both DATABASE_NAME and DATABASE_USER in your Django settings file."
            if not DATABASE_HOST:
                DATABASE_HOST = "127.0.0.1"
            # TODO: Handle DATABASE_PORT.
            conn_string = "PROVIDER=SQLOLEDB;DATA SOURCE=%s;UID=%s;PWD=%s;DATABASE=%s" % (DATABASE_HOST, DATABASE_USER, DATABASE_PASSWORD, DATABASE_NAME)
            self.connection = Database.connect(conn_string)
        cursor = self.connection.cursor()
        if DEBUG:
            return base.CursorDebugWrapper(cursor, self)
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

    def quote_name(self, name):
        if name.startswith('[') and name.endswith(']'):
            return name # Quoting once is enough.
        return '[%s]' % name

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

def get_limit_offset_sql(limit, offset=None):
    # TODO: This is a guess. Make sure this is correct.
    sql = "LIMIT %s" % limit
    if offset and offset != 0:
        sql += " OFFSET %s" % offset
    return sql

def get_random_function_sql():
    return "RAND()"

def get_table_list(cursor):
    raise NotImplementedError

def get_relations(cursor, table_name):
    raise NotImplementedError

OPERATOR_MAPPING = {
    'exact': '=',
    'iexact': 'LIKE',
    'contains': 'LIKE',
    'icontains': 'LIKE',
    'ne': '!=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'startswith': 'LIKE',
    'endswith': 'LIKE',
    'istartswith': 'LIKE',
    'iendswith': 'LIKE',
}

DATA_TYPES = {
    'AutoField':         'int IDENTITY (1, 1)',
    'BooleanField':      'bit',
    'CharField':         'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField': 'varchar(%(maxlength)s)',
    'DateField':         'smalldatetime',
    'DateTimeField':     'smalldatetime',
    'EmailField':        'varchar(75)',
    'FileField':         'varchar(100)',
    'FilePathField':     'varchar(100)',
    'FloatField':        'numeric(%(max_digits)s, %(decimal_places)s)',
    'ImageField':        'varchar(100)',
    'IntegerField':      'int',
    'IPAddressField':    'char(15)',
    'ManyToManyField':   None,
    'NullBooleanField':  'bit',
    'OneToOneField':     'int',
    'PhoneNumberField':  'varchar(20)',
    'PositiveIntegerField': 'int CONSTRAINT [CK_int_pos_%(name)s] CHECK ([%(name)s] > 0)',
    'PositiveSmallIntegerField': 'smallint CONSTRAINT [CK_smallint_pos_%(name)s] CHECK ([%(name)s] > 0)',
    'SlugField':         'varchar(50)',
    'SmallIntegerField': 'smallint',
    'TextField':         'text',
    'TimeField':         'time',
    'URLField':          'varchar(200)',
    'USStateField':      'varchar(2)',
}

DATA_TYPES_REVERSE = {}
