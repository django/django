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

def utf8rowFactory(cursor, row):
    def utf8(s):
        if type(s) == unicode:
            return s.encode("utf-8")
        else:
            return s
    return [utf8(r) for r in row]

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
        cursor = self.connection.cursor(factory=SQLiteCursorWrapper)
        cursor.row_factory = utf8rowFactory
        if DEBUG:
            return base.CursorDebugWrapper(cursor, self)
        else:
            return cursor

    def commit(self):
        self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

class SQLiteCursorWrapper(Database.Cursor):
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

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT %s" % limit
    if offset and offset != 0:
        sql += " OFFSET %s" % offset
    return sql

def get_random_function_sql():
    return "RANDOM()"

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

def get_table_list(cursor):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def get_table_description(cursor, table_name):
    cursor.execute("PRAGMA table_info(%s)" % DatabaseWrapper().quote_name(table_name))
    return [(row[1], row[2], None, None) for row in cursor.fetchall()]

def get_relations(cursor, table_name):
    raise NotImplementedError

# Operators and fields ########################################################

# SQLite requires LIKE statements to include an ESCAPE clause if the value
# being escaped has a percent or underscore in it.
# See http://www.sqlite.org/lang_expr.html for an explanation.
OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': "LIKE %s ESCAPE '\\'",
    'contains': "LIKE %s ESCAPE '\\'",
    'icontains': "LIKE %s ESCAPE '\\'",
    'ne': '!= %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': "LIKE %s ESCAPE '\\'",
    'endswith': "LIKE %s ESCAPE '\\'",
    'istartswith': "LIKE %s ESCAPE '\\'",
    'iendswith': "LIKE %s ESCAPE '\\'",
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
    'FileField':                    'varchar(100)',
    'FilePathField':                'varchar(100)',
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
}

# Maps SQL types to Django Field types. Some of the SQL types have multiple
# entries here because SQLite allows for anything and doesn't normalize the
# field type; it uses whatever was given.
BASE_DATA_TYPES_REVERSE = {
    'bool': 'BooleanField',
    'boolean': 'BooleanField',
    'smallint': 'SmallIntegerField',
    'smallinteger': 'SmallIntegerField',
    'int': 'IntegerField',
    'integer': 'IntegerField',
    'text': 'TextField',
    'char': 'CharField',
    'date': 'DateField',
    'datetime': 'DateTimeField',
    'time': 'TimeField',
}

# This light wrapper "fakes" a dictionary interface, because some SQLite data
# types include variables in them -- e.g. "varchar(30)" -- and can't be matched
# as a simple dictionary lookup.
class FlexibleFieldLookupDict:
    def __getitem__(self, key):
        key = key.lower()
        try:
            return BASE_DATA_TYPES_REVERSE[key]
        except KeyError:
            import re
            m = re.search(r'^\s*(?:var)?char\s*\(\s*(\d+)\s*\)\s*$', key)
            if m:
                return ('CharField', {'maxlength': int(m.group(1))})
            raise KeyError

DATA_TYPES_REVERSE = FlexibleFieldLookupDict()
