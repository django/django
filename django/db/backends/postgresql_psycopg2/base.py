"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

from django.db.backends import BaseDatabaseWrapper
from django.db.backends.postgresql.operations import DatabaseOperations
try:
    import psycopg2 as Database
    import psycopg2.extensions
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured, "Error loading psycopg2 module: %s" % e

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

class DatabaseWrapper(BaseDatabaseWrapper):
    ops = DatabaseOperations()

    def _cursor(self, settings):
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
            self.connection.set_client_encoding('UTF8')
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = None
        if set_tz:
            cursor.execute("SET TIME ZONE %s", [settings.TIME_ZONE])
        if self.ops.postgres_version is None:
            cursor.execute("SELECT version()")
            self.ops.postgres_version = [int(val) for val in cursor.fetchone()[0].split()[1].split('.')]
        return cursor

allows_group_by_ordinal = True
allows_unique_and_pk = True
autoindexes_primary_keys = True
needs_datetime_string_cast = False
needs_upper_for_iops = False
supports_constraints = True
supports_tablespaces = False
uses_case_insensitive_names = False

OPERATOR_MAPPING = {
    'exact': '= %s',
    'iexact': 'ILIKE %s',
    'contains': 'LIKE %s',
    'icontains': 'ILIKE %s',
    'regex': '~ %s',
    'iregex': '~* %s',
    'gt': '> %s',
    'gte': '>= %s',
    'lt': '< %s',
    'lte': '<= %s',
    'startswith': 'LIKE %s',
    'endswith': 'LIKE %s',
    'istartswith': 'ILIKE %s',
    'iendswith': 'ILIKE %s',
}
