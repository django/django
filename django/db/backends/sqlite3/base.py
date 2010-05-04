"""
SQLite3 backend for django.

Python 2.4 requires pysqlite2 (http://pysqlite.org/).

Python 2.5 and later can use a pysqlite2 module or the sqlite3 module in the
standard library.
"""

import re
import sys

from django.db import utils
from django.db.backends import *
from django.db.backends.signals import connection_created
from django.db.backends.sqlite3.client import DatabaseClient
from django.db.backends.sqlite3.creation import DatabaseCreation
from django.db.backends.sqlite3.introspection import DatabaseIntrospection
from django.utils.safestring import SafeString

try:
    try:
        from pysqlite2 import dbapi2 as Database
    except ImportError, e1:
        from sqlite3 import dbapi2 as Database
except ImportError, exc:
    import sys
    from django.core.exceptions import ImproperlyConfigured
    if sys.version_info < (2, 5, 0):
        module = 'pysqlite2 module'
        exc = e1
    else:
        module = 'either pysqlite2 or sqlite3 modules (tried in that order)'
    raise ImproperlyConfigured("Error loading %s: %s" % (module, exc))


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
    Database.register_adapter(SafeString, lambda s:s.decode('utf-8'))

class DatabaseFeatures(BaseDatabaseFeatures):
    # SQLite cannot handle us only partially reading from a cursor's result set
    # and then writing the same rows to the database in another cursor. This
    # setting ensures we always read result sets fully into memory all in one
    # go.
    can_use_chunked_reads = False

class DatabaseOperations(BaseDatabaseOperations):
    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_extract that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_extract('%s', %s)" % (lookup_type.lower(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_trunc('%s', %s)" % (lookup_type.lower(), field_name)

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

    def convert_values(self, value, field):
        """SQLite returns floats when it should be returning decimals,
        and gets dates and datetimes wrong.
        For consistency with other backends, coerce when required.
        """
        internal_type = field.get_internal_type()
        if internal_type == 'DecimalField':
            return util.typecast_decimal(field.format_number(value))
        elif internal_type and internal_type.endswith('IntegerField') or internal_type == 'AutoField':
            return int(value)
        elif internal_type == 'DateField':
            return util.typecast_date(value)
        elif internal_type == 'DateTimeField':
            return util.typecast_timestamp(value)
        elif internal_type == 'TimeField':
            return util.typecast_time(value)

        # No field, or the field isn't known to be a decimal or integer
        return value

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
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def _cursor(self):
        if self.connection is None:
            settings_dict = self.settings_dict
            if not settings_dict['NAME']:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("Please fill out the database NAME in the settings module before using the database.")
            kwargs = {
                'database': settings_dict['NAME'],
                'detect_types': Database.PARSE_DECLTYPES | Database.PARSE_COLNAMES,
            }
            kwargs.update(settings_dict['OPTIONS'])
            self.connection = Database.connect(**kwargs)
            # Register extract, date_trunc, and regexp functions.
            self.connection.create_function("django_extract", 2, _sqlite_extract)
            self.connection.create_function("django_date_trunc", 2, _sqlite_date_trunc)
            self.connection.create_function("regexp", 2, _sqlite_regexp)
            connection_created.send(sender=self.__class__)
        return self.connection.cursor(factory=SQLiteCursorWrapper)

    def close(self):
        # If database is in memory, closing the connection destroys the
        # database. To prevent accidental data loss, ignore close requests on
        # an in-memory db.
        if self.settings_dict['NAME'] != ":memory:":
            BaseDatabaseWrapper.close(self)

FORMAT_QMARK_REGEX = re.compile(r'(?![^%])%s')

class SQLiteCursorWrapper(Database.Cursor):
    """
    Django uses "format" style placeholders, but pysqlite2 uses "qmark" style.
    This fixes it -- but note that if you want to use a literal "%s" in a query,
    you'll need to use "%%s".
    """
    def execute(self, query, params=()):
        query = self.convert_query(query)
        try:
            return Database.Cursor.execute(self, query, params)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def executemany(self, query, param_list):
        query = self.convert_query(query)
        try:
            return Database.Cursor.executemany(self, query, param_list)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def convert_query(self, query):
        return FORMAT_QMARK_REGEX.sub('?', query).replace('%%','%')

def _sqlite_extract(lookup_type, dt):
    if dt is None:
        return None
    try:
        dt = util.typecast_timestamp(dt)
    except (ValueError, TypeError):
        return None
    if lookup_type == 'week_day':
        return (dt.isoweekday() % 7) + 1
    else:
        return getattr(dt, lookup_type)

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
