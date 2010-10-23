"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

import sys

from django.db import utils
from django.db.backends import *
from django.db.backends.signals import connection_created
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

class CursorWrapper(object):
    """
    A thin wrapper around psycopg2's normal cursor class so that we can catch
    particular exception instances and reraise them with the right types.
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, args=None):
        try:
            return self.cursor.execute(query, args)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def executemany(self, query, args):
        try:
            return self.cursor.executemany(query, args)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = False
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True

class DatabaseOperations(PostgresqlDatabaseOperations):
    def last_executed_query(self, cursor, sql, params):
        # With psycopg2, cursor objects have a "query" attribute that is the
        # exact query sent to the database. See docs here:
        # http://www.initd.org/tracker/psycopg/wiki/psycopg2_documentation#postgresql-status-message-and-executed-query
        return cursor.query

    def return_insert_id(self):
        return "RETURNING %s", ()

class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'postgresql'
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

        self.features = DatabaseFeatures(self)
        autocommit = self.settings_dict["OPTIONS"].get('autocommit', False)
        self.features.uses_autocommit = autocommit
        self._set_isolation_level(int(not autocommit))
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def _cursor(self):
        new_connection = False
        set_tz = False
        settings_dict = self.settings_dict
        if self.connection is None:
            new_connection = True
            set_tz = settings_dict.get('TIME_ZONE')
            if settings_dict['NAME'] == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("You need to specify NAME in your Django settings file.")
            conn_params = {
                'database': settings_dict['NAME'],
            }
            conn_params.update(settings_dict['OPTIONS'])
            if 'autocommit' in conn_params:
                del conn_params['autocommit']
            if settings_dict['USER']:
                conn_params['user'] = settings_dict['USER']
            if settings_dict['PASSWORD']:
                conn_params['password'] = settings_dict['PASSWORD']
            if settings_dict['HOST']:
                conn_params['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                conn_params['port'] = settings_dict['PORT']
            self.connection = Database.connect(**conn_params)
            self.connection.set_client_encoding('UTF8')
            self.connection.set_isolation_level(self.isolation_level)
            connection_created.send(sender=self.__class__, connection=self)
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = None
        if new_connection:
            if set_tz:
                cursor.execute("SET TIME ZONE %s", [settings_dict['TIME_ZONE']])
            if not hasattr(self, '_version'):
                self.__class__._version = get_version(cursor)
            if self._version[0:2] < (8, 0):
                # No savepoint support for earlier version of PostgreSQL.
                self.features.uses_savepoints = False
            if self.features.uses_autocommit:
                if self._version[0:2] < (8, 2):
                    # FIXME: Needs extra code to do reliable model insert
                    # handling, so we forbid it for now.
                    from django.core.exceptions import ImproperlyConfigured
                    raise ImproperlyConfigured("You cannot use autocommit=True with PostgreSQL prior to 8.2 at the moment.")
                else:
                    # FIXME: Eventually we're enable this by default for
                    # versions that support it, but, right now, that's hard to
                    # do without breaking other things (#10509).
                    self.features.can_return_id_from_insert = True
        return CursorWrapper(cursor)

    def _enter_transaction_management(self, managed):
        """
        Switch the isolation level when needing transaction support, so that
        the same transaction is visible across all the queries.
        """
        if self.features.uses_autocommit and managed and not self.isolation_level:
            self._set_isolation_level(1)

    def _leave_transaction_management(self, managed):
        """
        If the normal operating mode is "autocommit", switch back to that when
        leaving transaction management.
        """
        if self.features.uses_autocommit and not managed and self.isolation_level:
            self._set_isolation_level(0)

    def _set_isolation_level(self, level):
        """
        Do all the related feature configurations for changing isolation
        levels. This doesn't touch the uses_autocommit feature, since that
        controls the movement *between* isolation levels.
        """
        assert level in (0, 1)
        try:
            if self.connection is not None:
                self.connection.set_isolation_level(level)
        finally:
            self.isolation_level = level
            self.features.uses_savepoints = bool(level)

    def _commit(self):
        if self.connection is not None:
            try:
                return self.connection.commit()
            except Database.IntegrityError, e:
                raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
