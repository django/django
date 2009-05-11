"""
PostgreSQL database backend for Django.

Requires psycopg 1: http://initd.org/projects/psycopg1
"""

from django.db.backends import *
from django.db.backends.signals import connection_created
from django.db.backends.postgresql.client import DatabaseClient
from django.db.backends.postgresql.creation import DatabaseCreation
from django.db.backends.postgresql.introspection import DatabaseIntrospection
from django.db.backends.postgresql.operations import DatabaseOperations
from django.db.backends.postgresql.version import get_version
from django.utils.encoding import smart_str, smart_unicode

try:
    import psycopg as Database
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg module: %s" % e)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

class UnicodeCursorWrapper(object):
    """
    A thin wrapper around psycopg cursors that allows them to accept Unicode
    strings as params.

    This is necessary because psycopg doesn't apply any DB quoting to
    parameters that are Unicode strings. If a param is Unicode, this will
    convert it to a bytestring using database client's encoding before passing
    it to psycopg.

    All results retrieved from the database are converted into Unicode strings
    before being returned to the caller.
    """
    def __init__(self, cursor, charset):
        self.cursor = cursor
        self.charset = charset

    def format_params(self, params):
        if isinstance(params, dict):
            result = {}
            charset = self.charset
            for key, value in params.items():
                result[smart_str(key, charset)] = smart_str(value, charset)
            return result
        else:
            return tuple([smart_str(p, self.charset, True) for p in params])

    def execute(self, sql, params=()):
        return self.cursor.execute(smart_str(sql, self.charset), self.format_params(params))

    def executemany(self, sql, param_list):
        new_param_list = [self.format_params(params) for params in param_list]
        return self.cursor.executemany(sql, new_param_list)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)

class DatabaseFeatures(BaseDatabaseFeatures):
    uses_savepoints = True

class DatabaseWrapper(BaseDatabaseWrapper):
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'LIKE UPPER(%s)',
        'regex': '~ %s',
        'iregex': '~* %s',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'LIKE UPPER(%s)',
        'iendswith': 'LIKE UPPER(%s)',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures()
        self.ops = DatabaseOperations()
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation()

    def _cursor(self):
        set_tz = False
        settings_dict = self.settings_dict
        if self.connection is None:
            set_tz = True
            if settings_dict['DATABASE_NAME'] == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("You need to specify DATABASE_NAME in your Django settings file.")
            conn_string = "dbname=%s" % settings_dict['DATABASE_NAME']
            if settings_dict['DATABASE_USER']:
                conn_string = "user=%s %s" % (settings_dict['DATABASE_USER'], conn_string)
            if settings_dict['DATABASE_PASSWORD']:
                conn_string += " password='%s'" % settings_dict['DATABASE_PASSWORD']
            if settings_dict['DATABASE_HOST']:
                conn_string += " host=%s" % settings_dict['DATABASE_HOST']
            if settings_dict['DATABASE_PORT']:
                conn_string += " port=%s" % settings_dict['DATABASE_PORT']
            self.connection = Database.connect(conn_string, **settings_dict['DATABASE_OPTIONS'])
            self.connection.set_isolation_level(1) # make transactions transparent to all cursors
            connection_created.send(sender=self.__class__)
        cursor = self.connection.cursor()
        if set_tz:
            cursor.execute("SET TIME ZONE %s", [settings_dict['TIME_ZONE']])
            if not hasattr(self, '_version'):
                self.__class__._version = get_version(cursor)
            if self._version[0:2] < (8, 0):
                # No savepoint support for earlier version of PostgreSQL.
                self.features.uses_savepoints = False
        cursor.execute("SET client_encoding to 'UNICODE'")
        cursor = UnicodeCursorWrapper(cursor, 'utf-8')
        return cursor

def typecast_string(s):
    """
    Cast all returned strings to unicode strings.
    """
    if not s and not isinstance(s, str):
        return s
    return smart_unicode(s)

# Register these custom typecasts, because Django expects dates/times to be
# in Python's native (standard-library) datetime/time format, whereas psycopg
# use mx.DateTime by default.
try:
    Database.register_type(Database.new_type((1082,), "DATE", util.typecast_date))
except AttributeError:
    raise Exception("You appear to be using psycopg version 2. Set your DATABASE_ENGINE to 'postgresql_psycopg2' instead of 'postgresql'.")
Database.register_type(Database.new_type((1083,1266), "TIME", util.typecast_time))
Database.register_type(Database.new_type((1114,1184), "TIMESTAMP", util.typecast_timestamp))
Database.register_type(Database.new_type((16,), "BOOLEAN", util.typecast_boolean))
Database.register_type(Database.new_type((1700,), "NUMERIC", util.typecast_decimal))
Database.register_type(Database.new_type(Database.types[1043].values, 'STRING', typecast_string))
