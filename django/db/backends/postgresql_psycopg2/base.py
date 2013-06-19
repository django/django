"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""
import logging
import sys

from django.db.backends import *
from django.db.backends.postgresql_psycopg2.operations import DatabaseOperations
from django.db.backends.postgresql_psycopg2.client import DatabaseClient
from django.db.backends.postgresql_psycopg2.creation import DatabaseCreation
from django.db.backends.postgresql_psycopg2.version import get_version
from django.db.backends.postgresql_psycopg2.introspection import DatabaseIntrospection
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.safestring import SafeText, SafeBytes
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

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_bulk_insert = True
    uses_savepoints = True
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

    Database = Database

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        opts = self.settings_dict["OPTIONS"]
        RC = psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED
        self.isolation_level = opts.get('isolation_level', RC)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def get_connection_params(self):
        settings_dict = self.settings_dict
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
        if 'isolation_level' in conn_params:
            del conn_params['isolation_level']
        if settings_dict['USER']:
            conn_params['user'] = settings_dict['USER']
        if settings_dict['PASSWORD']:
            conn_params['password'] = force_str(settings_dict['PASSWORD'])
        if settings_dict['HOST']:
            conn_params['host'] = settings_dict['HOST']
        if settings_dict['PORT']:
            conn_params['port'] = settings_dict['PORT']
        return conn_params

    def get_new_connection(self, conn_params):
        return Database.connect(**conn_params)

    def init_connection_state(self):
        settings_dict = self.settings_dict
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
                self.set_autocommit(True)
                self.connection.cursor().execute(
                        self.ops.set_time_zone_sql(), [tz])
        self.connection.set_isolation_level(self.isolation_level)

    def create_cursor(self):
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        return cursor

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
        finally:
            self.set_clean()

    def _set_isolation_level(self, isolation_level):
        assert isolation_level in range(1, 5)     # Use set_autocommit for level = 0
        if self.psycopg2_version >= (2, 4, 2):
            self.connection.set_session(isolation_level=isolation_level)
        else:
            self.connection.set_isolation_level(isolation_level)

    def _set_autocommit(self, autocommit):
        if self.psycopg2_version >= (2, 4, 2):
            self.connection.autocommit = autocommit
        else:
            if autocommit:
                level = psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
            else:
                level = self.isolation_level
            self.connection.set_isolation_level(level)

    def check_constraints(self, table_names=None):
        """
        To check constraints, we set constraints to immediate. Then, when, we're done we must ensure they
        are returned to deferred.
        """
        self.cursor().execute('SET CONSTRAINTS ALL IMMEDIATE')
        self.cursor().execute('SET CONSTRAINTS ALL DEFERRED')

    def is_usable(self):
        try:
            # Use a psycopg cursor directly, bypassing Django's utilities.
            self.connection.cursor().execute("SELECT 1")
        except DatabaseError:
            return False
        else:
            return True

    @cached_property
    def psycopg2_version(self):
        version = psycopg2.__version__.split(' ', 1)[0]
        return tuple(int(v) for v in version.split('.'))

    @cached_property
    def pg_version(self):
        with self.temporary_connection():
            return get_version(self.connection)
