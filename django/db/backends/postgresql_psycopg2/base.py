"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

from django.conf import settings
from django.db.backends import *
from django.db.backends.postgresql.operations import DatabaseOperations as PostgresqlDatabaseOperations
from django.db.backends.postgresql.client import DatabaseClient
from django.db.backends.postgresql.creation import DatabaseCreation
from django.db.backends.postgresql.version import get_version
from django.db.backends.postgresql_psycopg2.introspection import DatabaseIntrospection
from django.utils.safestring import SafeUnicode, SafeString

try:
    import psycopg2 as Database
    import psycopg2.extensions
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg2 module: %s" % e)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_adapter(SafeString, psycopg2.extensions.QuotedString)
psycopg2.extensions.register_adapter(SafeUnicode, psycopg2.extensions.QuotedString)

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True

class DatabaseOperations(PostgresqlDatabaseOperations):
    def last_executed_query(self, cursor, sql, params):
        # With psycopg2, cursor objects have a "query" attribute that is the
        # exact query sent to the database. See docs here:
        # http://www.initd.org/tracker/psycopg/wiki/psycopg2_documentation#postgresql-status-message-and-executed-query
        return cursor.query

    def return_insert_id(self):
        return "RETURNING %s"

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
        if settings.DATABASE_OPTIONS.get('autocommit', False):
          self.features.uses_autocommit = True
          self._iso_level_0()
        else:
          self.features.uses_autocommit = False
          self._iso_level_1()
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
            conn_params = {
                'database': settings_dict['DATABASE_NAME'],
            }
            conn_params.update(settings_dict['DATABASE_OPTIONS'])
            if 'autocommit' in conn_params:
                del conn_params['autocommit']
            if settings_dict['DATABASE_USER']:
                conn_params['user'] = settings_dict['DATABASE_USER']
            if settings_dict['DATABASE_PASSWORD']:
                conn_params['password'] = settings_dict['DATABASE_PASSWORD']
            if settings_dict['DATABASE_HOST']:
                conn_params['host'] = settings_dict['DATABASE_HOST']
            if settings_dict['DATABASE_PORT']:
                conn_params['port'] = settings_dict['DATABASE_PORT']
            self.connection = Database.connect(**conn_params)
            self.connection.set_client_encoding('UTF8')
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = None
        if set_tz:
            cursor.execute("SET TIME ZONE %s", [settings_dict['TIME_ZONE']])
            if not hasattr(self, '_version'):
                self.__class__._version = get_version(cursor)
            if self._version < (8, 0):
                # No savepoint support for earlier version of PostgreSQL.
                self.features.uses_savepoints = False
        return cursor

    def _enter_transaction_management(self, managed):
        """
        Switch the isolation level when needing transaction support, so that
        the same transaction is visible across all the queries.
        """
        if self.features.uses_autocommit and managed and not self.isolation_level:
            self._iso_level_1()

    def _leave_transaction_management(self, managed):
        """
        If the normal operating mode is "autocommit", switch back to that when
        leaving transaction management.
        """
        if self.features.uses_autocommit and not managed and self.isolation_level:
            self._iso_level_0()

    def _iso_level_0(self):
        """
        Do all the related feature configurations for isolation level 0. This
        doesn't touch the uses_autocommit feature, since that controls the
        movement *between* isolation levels.
        """
        try:
            if self.connection is not None:
                self.connection.set_isolation_level(0)
        finally:
            self.isolation_level = 0
            self.features.uses_savepoints = False

    def _iso_level_1(self):
        """
        The "isolation level 1" version of _iso_level_0().
        """
        try:
            if self.connection is not None:
                self.connection.set_isolation_level(1)
        finally:
            self.isolation_level = 1
            self.features.uses_savepoints = True

