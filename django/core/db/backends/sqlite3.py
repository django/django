"""
SQLite3 backend for django.  Requires pysqlite2 (http://pysqlite.org/).
"""

from django.core.db import base, typecasts
from django.core.db.dicthelpers import *
from pysqlite2 import dbapi2 as Database
DatabaseError = Database.DatabaseError

# Register adaptors ###########################################################

Database.register_converter("bool", lambda s: str(s) == '1')
Database.register_converter("time", typecasts.typecast_time)
Database.register_converter("date", typecasts.typecast_date)
Database.register_converter("datetime", typecasts.typecast_timestamp)

# Database wrapper ############################################################

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_NAME, DEBUG
        if self.connection is None:
            self.connection = Database.connect(DATABASE_NAME, detect_types=Database.PARSE_DECLTYPES)
            # register extract and date_trun functions
            self.connection.create_function("django_extract", 2, _sqlite_extract)
            self.connection.create_function("django_date_trunc", 2, _sqlite_date_trunc)
        if DEBUG:
            return base.CursorDebugWrapper(FormatStylePlaceholderCursor(self.connection), self)
        return FormatStylePlaceholderCursor(self.connection)

    def commit(self):
        self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

class FormatStylePlaceholderCursor(Database.Cursor):
    """
    Django uses "format" style placeholders, but pysqlite2 uses "qmark" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s" (which I belive is true of other wrappers as well).
    """
    
    def execute(self, query, params=[]):
        query = self.convert_query(query, len(params))
        return Database.Cursor.execute(self, query, params)
        
    def executemany(self, query, params=[]):
        query = self.convert_query(query, len(params[0]))
        return Database.Cursor.executemany(self, query, params)
        
    def convert_query(self, query, num_params):
        # XXX this seems too simple to be correct... is this right?
        return query % tuple("?" * num_params)

# Helper functions ############################################################

def get_last_insert_id(cursor, table_name, pk_name):
    return cursor.lastrowid
    
def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # sqlite doesn't support extract, so we fake it with the user-defined 
    # function _sqlite_extract that's registered in connect(), above.
    return 'django_extract("%s", %s)' % (lookup_type.lower(), table_name)

def _sqlite_extract(lookup_type, dt):
    try:
        dt = typecasts.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    return str(getattr(dt, lookup_type))

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # sqlite doesn't support DATE_TRUNC, so we fake it as above.
    return 'django_date_trunc("%s", %s)' % (lookup_type.lower(), field_name)

def _sqlite_date_trunc(lookup_type, dt):
    try:
        dt = typecasts.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)

# Operators and fields ########################################################
        
OPERATOR_MAPPING = {
    'exact':        '=',
    'iexact':       'LIKE',
    'contains':     'LIKE',
    'icontains':    'LIKE',
    'ne':           '!=',
    'gt':           '>',
    'gte':          '>=',
    'lt':           '<',
    'lte':          '<=',
    'startswith':   'LIKE',
    'endswith':     'LIKE',
    'istartswith':  'LIKE',
    'iendswith':    'LIKE',
}

# SQLite doesn't actually support most of these types, but it "does the right 
# thing" given more verbose field definitions, so leave them as is so that
# schema inspection is more useful.
DATA_TYPES = {
    'AutoField':                    'integer',
    'BooleanField':                 'bool',
    'CharField':                    'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField':   'varchar(%(maxlength)s)',
    'DateField':                    'date',
    'DateTimeField':                'datetime',
    'EmailField':                   'varchar(75)',
    'FileField':                    'varchar(100)',
    'FloatField':                   'numeric(%(max_digits)s, %(decimal_places)s)',
    'ImageField':                   'varchar(100)',
    'IntegerField':                 'integer',
    'IPAddressField':               'char(15)',
    'ManyToManyField':              None,
    'NullBooleanField':             'bool',
    'OneToOneField':                'integer',
    'PhoneNumberField':             'varchar(20)',
    'PositiveIntegerField':         'integer unsigned',
    'PositiveSmallIntegerField':    'smallint unsigned',
    'SlugField':                    'varchar(50)',
    'SmallIntegerField':            'smallint',
    'TextField':                    'text',
    'TimeField':                    'time',
    'URLField':                     'varchar(200)',
    'USStateField':                 'varchar(2)',
    'XMLField':                     'text',
}
