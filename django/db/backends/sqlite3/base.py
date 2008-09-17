"""
SQLite3 backend for django.

Python 2.3 and 2.4 require pysqlite2 (http://pysqlite.org/).

Python 2.5 and later use the sqlite3 module in the standard library.
"""

from django.db.backends import *
from django.db.backends.sqlite3.client import DatabaseClient
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.db.backends.sqlite3.introspection import DatabaseIntrospection

try:
    try:
        from sqlite3 import dbapi2 as Database
    except ImportError, e1:
        from pysqlite2 import dbapi2 as Database
except ImportError, exc:
    import sys
    from django.core.exceptions import ImproperlyConfigured
    if sys.version_info < (2, 5, 0):
        module = 'pysqlite2'
    else:
        module = 'sqlite3'
        exc = e1
    raise ImproperlyConfigured, "Error loading %s module: %s" % (module, exc)

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal # for Python 2.3

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

Database.register_converter("bool", lambda s: str(s) == '1')
Database.register_converter("time", util.typecast_time)
Database.register_converter("date", util.typecast_date)
Database.register_converter("datetime", util.typecast_timestamp)
Database.register_converter("timestamp", util.typecast_timestamp)
Database.register_converter("TIMESTAMP", util.typecast_timestamp)
Database.register_converter("decimal", util.typecast_decimal)
Database.register_adapter(decimal.Decimal, util.rev_typecast_decimal)
if Database.version_info >= (2,4,1):
    # Starting in 2.4.1, the str type is not accepted anymore, therefore,
    # we convert all str objects to Unicode
    # As registering a adapter for a primitive type causes a small
    # slow-down, this adapter is only registered for sqlite3 versions
    # needing it.
    Database.register_adapter(str, lambda s:s.decode('utf-8'))

class DatabaseFeatures(BaseDatabaseFeatures):
    # SQLite cannot handle us only partially reading from a cursor's result set
    # and then writing the same rows to the database in another cursor. This
    # setting ensures we always read result sets fully into memory all in one
    # go.
    can_use_chunked_reads = False

class DatabaseOperations(BaseDatabaseOperations):
    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_extract that's registered in connect().
        return 'django_extract("%s", %s)' % (lookup_type.lower(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect().
        return 'django_date_trunc("%s", %s)' % (lookup_type.lower(), field_name)

    def drop_foreignkey_sql(self):
        return ""

    def pk_default_value(self):
        return 'NULL'

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name # Quoting once is enough.
        return '"%s"' % name

    def no_limit_value(self):
        return -1

    def sql_flush(self, style, tables, sequences):
        # NB: The generated SQL below is specific to SQLite
        # Note: The DELETE FROM... SQL generated below works for SQLite databases
        # because constraints don't exist
        sql = ['%s %s %s;' % \
                (style.SQL_KEYWORD('DELETE'),
                 style.SQL_KEYWORD('FROM'),
                 style.SQL_FIELD(self.quote_name(table))
                 ) for table in tables]
        # Note: No requirement for reset of auto-incremented indices (cf. other
        # sql_flush() implementations). Just return SQL at this point
        return sql

    def year_lookup_bounds(self, value):
        first = '%s-01-01'
        second = '%s-12-31 23:59:59.999999'
        return [first % value, second % value]

class DatabaseWrapper(BaseDatabaseWrapper):
    
    # SQLite requires LIKE statements to include an ESCAPE clause if the value
    # being escaped has a percent or underscore in it.
    # See http://www.sqlite.org/lang_expr.html for an explanation.
    operators = {
        'exact': '= %s',
        'iexact': "LIKE %s ESCAPE '\\'",
        'contains': "LIKE %s ESCAPE '\\'",
        'icontains': "LIKE %s ESCAPE '\\'",
        'regex': 'REGEXP %s',
        'iregex': "REGEXP '(?i)' || %s",
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': "LIKE %s ESCAPE '\\'",
        'endswith': "LIKE %s ESCAPE '\\'",
        'istartswith': "LIKE %s ESCAPE '\\'",
        'iendswith': "LIKE %s ESCAPE '\\'",
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        
        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.client = DatabaseClient()
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation()

    def _cursor(self, settings):
        if self.connection is None:
            if not settings.DATABASE_NAME:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured, "Please fill out DATABASE_NAME in the settings module before using the database."
            kwargs = {
                'database': settings.DATABASE_NAME,
                'detect_types': Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
            }
            kwargs.update(self.options)
            self.connection = Database.connect(**kwargs)
            # Register extract, date_trunc, and regexp functions.
            self.connection.create_function("django_extract", 2, _sqlite_extract)
            self.connection.create_function("django_date_trunc", 2, _sqlite_date_trunc)
            self.connection.create_function("regexp", 2, _sqlite_regexp)
        return self.connection.cursor(factory=SQLiteCursorWrapper)

    def close(self):
        from django.conf import settings
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if settings.DATABASE_NAME != ":memory:":
            BaseDatabaseWrapper.close(self)

class SQLiteCursorWrapper(Database.Cursor):
    """
    Django uses "format" style placeholders, but pysqlite2 uses "qmark" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def execute(self, query, params=()):
        query = self.convert_query(query, len(params))
        return Database.Cursor.execute(self, query, params)

    def executemany(self, query, param_list):
        try:
          query = self.convert_query(query, len(param_list[0]))
          return Database.Cursor.executemany(self, query, param_list)
        except (IndexError,TypeError):
          # No parameter list provided
          return None

    def convert_query(self, query, num_params):
        return query % tuple("?" * num_params)

def _sqlite_extract(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    return unicode(getattr(dt, lookup_type))

def _sqlite_date_trunc(lookup_type, dt):
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'year':
        return "%i-01-01 00:00:00" % dt.year
    elif lookup_type == 'month':
        return "%i-%02i-01 00:00:00" % (dt.year, dt.month)
    elif lookup_type == 'day':
        return "%i-%02i-%02i 00:00:00" % (dt.year, dt.month, dt.day)

def _sqlite_regexp(re_pattern, re_string):
    import re
    try:
        return bool(re.search(re_pattern, re_string))
    except:
        return False
