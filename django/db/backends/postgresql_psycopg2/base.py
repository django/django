"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""
import logging
import sys

from django.db import utils
from django.db.backends import *
from django.db.backends.signals import connection_created
from django.db.backends.postgresql_psycopg2.operations import DatabaseOperations
from django.db.backends.postgresql_psycopg2.client import DatabaseClient
from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation
from django.db.backends.postgresql_psycopg2.version import get_version
from django.db.backends.postgresql_psycopg2.introspection import DatabaseIntrospection
from django.utils.encoding import force_str
from django.utils.safestring import SafeText, SafeBytes
from django.utils import six
from django.utils.timezone import utc

try:
    import psycopg2 as Database
    import psycopg2.extensions
except ImportError as e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg2 module: %s" % e)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_adapter(SafeBytes, psycopg2.extensions.QuotedString)
psycopg2.extensions.register_adapter(SafeText, psycopg2.extensions.QuotedString)

logger = logging.getLogger('django.db.backends')

def utc_tzinfo_factory(offset):
    if offset != 0:
        raise AssertionError("database connection isn't set to UTC")
    return utc

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
        except Database.IntegrityError as e:
            six.reraise(utils.IntegrityError, utils.IntegrityError(*tuple(e.args)), sys.exc_info()[2])
        except Database.DatabaseError as e:
            six.reraise(utils.DatabaseError, utils.DatabaseError(*tuple(e.args)), sys.exc_info()[2])

    def executemany(self, query, args):
        try:
            return self.cursor.executemany(query, args)
        except Database.IntegrityError as e:
            six.reraise(utils.IntegrityError, utils.IntegrityError(*tuple(e.args)), sys.exc_info()[2])
        except Database.DatabaseError as e:
            six.reraise(utils.DatabaseError, utils.DatabaseError(*tuple(e.args)), sys.exc_info()[2])

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_bulk_insert = True
    supports_tablespaces = True
    supports_transactions = True
    can_distinct_on_fields = True

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
        if autocommit:
            level = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
        else:
            level = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
        self._set_isolation_level(level)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)
        self._pg_version = None

    def check_constraints(self, table_names=None):
        """
        To check constraints, we set constraints to immediate. Then, when, we're done we must ensure they
        are returned to deferred.
        """
        self.cursor().execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.cursor().execute('SET CONSTRAINTS ALL DEFERRED')

    def close(self):
        self.validate_thread_sharing()
        if self.connection is None:
            return

        try:
            self.connection.close()
            self.connection = None
        except Database.Error:
            # In some cases (database restart, network connection lost etc...)
            # the connection to the database is lost without giving Django a
            # notification. If we don't set self.connection to None, the error
            # will occur a every request.
            self.connection = None
            logger.warning('psycopg2 error while closing the connection.',
                exc_info=sys.exc_info()
            )
            raise

    def _get_pg_version(self):
        if self._pg_version is None:
            self._pg_version = get_version(self.connection)
        return self._pg_version
    pg_version = property(_get_pg_version)

    def _cursor(self):
        settings_dict = self.settings_dict
        if self.connection is None:
            if not settings_dict['NAME']:
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured(
                    "settings.DATABASES is improperly configured. "
                    "Please supply the NAME value.")
            conn_params = {
                'database': settings_dict['NAME'],
            }
            conn_params.update(settings_dict['OPTIONS'])
            if 'autocommit' in conn_params:
                del conn_params['autocommit']
            if settings_dict['USER']:
                conn_params['user'] = settings_dict['USER']
            if settings_dict['PASSWORD']:
                conn_params['password'] = force_str(settings_dict['PASSWORD'])
            if settings_dict['HOST']:
                conn_params['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                conn_params['port'] = settings_dict['PORT']
            self.connection = Database.connect(**conn_params)
            self.connection.set_client_encoding('UTF8')
            tz = 'UTC' if settings.USE_TZ else settings_dict.get('TIME_ZONE')
            if tz:
                try:
                    get_parameter_status = self.connection.get_parameter_status
                except AttributeError:
                    # psycopg2 < 2.0.12 doesn't have get_parameter_status
                    conn_tz = None
                else:
                    conn_tz = get_parameter_status('TimeZone')

                if conn_tz != tz:
                    # Set the time zone in autocommit mode (see #17062)
                    self.connection.set_isolation_level(
                            psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
                    self.connection.cursor().execute(
                            self.ops.set_time_zone_sql(), [tz])
            self.connection.set_isolation_level(self.isolation_level)
            self._get_pg_version()
            connection_created.send(sender=self.__class__, connection=self)
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        return CursorWrapper(cursor)

    def _enter_transaction_management(self, managed):
        """
        Switch the isolation level when needing transaction support, so that
        the same transaction is visible across all the queries.
        """
        if self.features.uses_autocommit and managed and not self.isolation_level:
            self._set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def _leave_transaction_management(self, managed):
        """
        If the normal operating mode is "autocommit", switch back to that when
        leaving transaction management.
        """
        if self.features.uses_autocommit and not managed and self.isolation_level:
            self._set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    def _set_isolation_level(self, level):
        """
        Do all the related feature configurations for changing isolation
        levels. This doesn't touch the uses_autocommit feature, since that
        controls the movement *between* isolation levels.
        """
        assert level in range(5)
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
            except Database.IntegrityError as e:
                six.reraise(utils.IntegrityError, utils.IntegrityError(*tuple(e.args)), sys.exc_info()[2])
