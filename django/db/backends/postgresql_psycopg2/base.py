"""
PostgreSQL database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

from django.conf import settings
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.base.validation import BaseDatabaseValidation
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.safestring import SafeText, SafeBytes

try:
    import psycopg2 as Database
    import psycopg2.extensions
    import psycopg2.extras
except ImportError as e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg2 module: %s" % e)

# Some of these import psycopg2, so import them after checking if it's installed.
from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .schema import DatabaseSchemaEditor
from .utils import utc_tzinfo_factory
from .version import get_version

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
psycopg2.extensions.register_adapter(SafeBytes, psycopg2.extensions.QuotedString)
psycopg2.extensions.register_adapter(SafeText, psycopg2.extensions.QuotedString)
psycopg2.extras.register_uuid()

# Register support for inet[] manually so we don't have to handle the Inet()
# object on load all the time.
INETARRAY_OID = 1041
INETARRAY = psycopg2.extensions.new_array_type(
    (INETARRAY_OID,),
    'INETARRAY',
    psycopg2.extensions.UNICODE,
)
psycopg2.extensions.register_type(INETARRAY)


class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'postgresql'
    # This dictionary maps Field objects to their associated PostgreSQL column
    # types, as strings. Column-type strings can contain format strings; they'll
    # be interpolated against the values of Field.__dict__ before being output.
    # If a column type is set to None, it won't be included in the output.
    data_types = {
        'AutoField': 'serial',
        'BinaryField': 'bytea',
        'BooleanField': 'boolean',
        'CharField': 'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
        'DateField': 'date',
        'DateTimeField': 'timestamp with time zone',
        'DecimalField': 'numeric(%(max_digits)s, %(decimal_places)s)',
        'DurationField': 'interval',
        'FileField': 'varchar(%(max_length)s)',
        'FilePathField': 'varchar(%(max_length)s)',
        'FloatField': 'double precision',
        'IntegerField': 'integer',
        'BigIntegerField': 'bigint',
        'IPAddressField': 'inet',
        'GenericIPAddressField': 'inet',
        'NullBooleanField': 'boolean',
        'OneToOneField': 'integer',
        'PositiveIntegerField': 'integer',
        'PositiveSmallIntegerField': 'smallint',
        'SlugField': 'varchar(%(max_length)s)',
        'SmallIntegerField': 'smallint',
        'TextField': 'text',
        'TimeField': 'time',
        'UUIDField': 'uuid',
    }
    data_type_check_constraints = {
        'PositiveIntegerField': '"%(column)s" >= 0',
        'PositiveSmallIntegerField': '"%(column)s" >= 0',
    }
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

    # The patterns below are used to generate SQL pattern lookup clauses when
    # the right-hand side of the lookup isn't a raw string (it might be an expression
    # or the result of a bilateral transformation).
    # In those cases, special characters for LIKE operators (e.g. \, *, _) should be
    # escaped on database side.
    #
    # Note: we use str.format() here for readability as '%' is used as a wildcard for
    # the LIKE operator.
    pattern_esc = r"REPLACE(REPLACE(REPLACE({}, '\', '\\'), '%%', '\%%'), '_', '\_')"
    pattern_ops = {
        'contains': "LIKE '%%' || {} || '%%'",
        'icontains': "LIKE '%%' || UPPER({}) || '%%'",
        'startswith': "LIKE {} || '%%'",
        'istartswith': "LIKE UPPER({}) || '%%'",
        'endswith': "LIKE '%%' || {}",
        'iendswith': "LIKE '%%' || UPPER({})",
    }

    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor

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
        # None may be used to connect to the default 'postgres' db
        if settings_dict['NAME'] == '':
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value.")
        conn_params = {
            'database': settings_dict['NAME'] or 'postgres',
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
                cursor = self.connection.cursor()
                try:
                    cursor.execute(self.ops.set_time_zone_sql(), [tz])
                finally:
                    cursor.close()
                # Commit after setting the time zone (see #17062)
                if not self.get_autocommit():
                    self.connection.commit()

    def create_cursor(self):
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = utc_tzinfo_factory if settings.USE_TZ else None
        return cursor

    def _set_isolation_level(self, isolation_level):
        assert isolation_level in range(1, 5)     # Use set_autocommit for level = 0
        if self.psycopg2_version >= (2, 4, 2):
            self.connection.set_session(isolation_level=isolation_level)
        else:
            self.connection.set_isolation_level(isolation_level)

    def _set_autocommit(self, autocommit):
        with self.wrap_database_errors:
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
        except Database.Error:
            return False
        else:
            return True

    @cached_property
    def psycopg2_version(self):
        version = psycopg2.__version__.split(' ', 1)[0]
        return tuple(int(v) for v in version.split('.') if v.isdigit())

    @cached_property
    def pg_version(self):
        with self.temporary_connection():
            return get_version(self.connection)
