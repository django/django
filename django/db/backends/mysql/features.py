from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property

from .base import Database


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
    supports_index_column_ordering = False
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    allows_auto_pk_0 = False
    uses_savepoints = True
    can_release_savepoints = True
    atomic_transactions = False
    supports_column_check_constraints = False
    can_clone_databases = True
    supports_temporal_subtraction = True
    supports_select_intersection = False
    supports_select_difference = False
    supports_slicing_ordering_in_compound = True

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
        # Test if the time zone definitions are installed.
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM mysql.time_zone LIMIT 1")
            return cursor.fetchone() is not None

    def introspected_boolean_field_type(self, *args, **kwargs):
        return 'IntegerField'

    @cached_property
    def is_sql_auto_is_null_enabled(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT @@SQL_AUTO_IS_NULL')
            result = cursor.fetchone()
            return result and result[0] == 1

    @cached_property
    def supports_transactions(self):
        """
        All storage engines except MyISAM support transactions.
        """
        return self._mysql_storage_engine != 'MyISAM'

    @cached_property
    def ignores_table_name_case(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT @@LOWER_CASE_TABLE_NAMES')
            result = cursor.fetchone()
            return result and result[0] != 0
