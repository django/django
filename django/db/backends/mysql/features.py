from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property

from .base import Database

try:
    import pytz
except ImportError:
    pytz = None


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    update_can_self_select = False
    allows_group_by_pk = True
    related_fields_match_type = True
    allow_sliced_subqueries = False
    has_bulk_insert = True
    has_select_for_update = True
    has_select_for_update_nowait = False
    supports_forward_references = False
    supports_regex_backreferencing = False
    supports_date_lookup_using_string = False
    can_introspect_autofield = True
    can_introspect_binary_field = False
    can_introspect_small_integer_field = True
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    allows_auto_pk_0 = False
    uses_savepoints = True
    can_release_savepoints = True
    atomic_transactions = False
    supports_column_check_constraints = False

    @cached_property
    def _mysql_storage_engine(self):
        "Internal method used in Django tests. Don't rely on this from your code"
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT ENGINE FROM INFORMATION_SCHEMA.ENGINES WHERE SUPPORT = 'DEFAULT'")
            result = cursor.fetchone()
        return result[0]

    @cached_property
    def can_introspect_foreign_keys(self):
        "Confirm support for introspected foreign keys"
        return self._mysql_storage_engine != 'MyISAM'

    @cached_property
    def supports_microsecond_precision(self):
        # See https://github.com/farcepest/MySQLdb1/issues/24 for the reason
        # about requiring MySQLdb 1.2.5
        return self.connection.mysql_version >= (5, 6, 4) and Database.version_info >= (1, 2, 5)

    @cached_property
    def has_zoneinfo_database(self):
        # MySQL accepts full time zones names (eg. Africa/Nairobi) but rejects
        # abbreviations (eg. EAT). When pytz isn't installed and the current
        # time zone is LocalTimezone (the only sensible value in this
        # context), the current time zone name will be an abbreviation. As a
        # consequence, MySQL cannot perform time zone conversions reliably.
        if pytz is None:
            return False

        # Test if the time zone definitions are installed.
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM mysql.time_zone LIMIT 1")
            return cursor.fetchone() is not None

    def introspected_boolean_field_type(self, *args, **kwargs):
        return 'IntegerField'
