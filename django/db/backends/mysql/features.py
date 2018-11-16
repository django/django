import operator

from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    update_can_self_select = False
    allows_group_by_pk = True
    related_fields_match_type = True
    # MySQL doesn't support sliced subqueries with IN/ALL/ANY/SOME.
    allow_sliced_subqueries_with_in = False
    has_select_for_update = True
    supports_forward_references = False
    supports_regex_backreferencing = False
    supports_date_lookup_using_string = False
    can_introspect_autofield = True
    can_introspect_binary_field = False
    can_introspect_duration_field = False
    can_introspect_small_integer_field = True
    can_introspect_positive_integer_field = True
    introspected_boolean_field_type = 'IntegerField'
    supports_index_column_ordering = False
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    allows_auto_pk_0 = False
    can_release_savepoints = True
    atomic_transactions = False
    supports_column_check_constraints = False
    supports_table_check_constraints = False
    can_clone_databases = True
    supports_temporal_subtraction = True
    supports_select_intersection = False
    supports_select_difference = False
    supports_slicing_ordering_in_compound = True
    supports_index_on_text_field = False
    has_case_insensitive_like = False
    create_test_procedure_without_params_sql = """
        CREATE PROCEDURE test_procedure ()
        BEGIN
            DECLARE V_I INTEGER;
            SET V_I = 1;
        END;
    """
    create_test_procedure_with_int_param_sql = """
        CREATE PROCEDURE test_procedure (P_I INTEGER)
        BEGIN
            DECLARE V_I INTEGER;
            SET V_I = P_I;
        END;
    """
    db_functions_convert_bytes_to_str = True
    # Alias MySQL's TRADITIONAL to TEXT for consistency with other backends.
    supported_explain_formats = {'JSON', 'TEXT', 'TRADITIONAL'}
    # Neither MySQL nor MariaDB support partial indexes.
    supports_partial_indexes = False

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
    def has_zoneinfo_database(self):
        # Test if the time zone definitions are installed.
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM mysql.time_zone LIMIT 1")
            return cursor.fetchone() is not None

    @cached_property
    def is_sql_auto_is_null_enabled(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT @@SQL_AUTO_IS_NULL')
            result = cursor.fetchone()
            return result and result[0] == 1

    @cached_property
    def supports_over_clause(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 2)
        return self.connection.mysql_version >= (8, 0, 2)

    @cached_property
    def has_select_for_update_skip_locked(self):
        return not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (8, 0, 1)

    has_select_for_update_nowait = property(operator.attrgetter('has_select_for_update_skip_locked'))

    @cached_property
    def needs_explain_extended(self):
        # EXTENDED is deprecated (and not required) in MySQL 5.7.
        return not self.connection.mysql_is_mariadb and self.connection.mysql_version < (5, 7)

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

    @cached_property
    def supports_default_in_lead_lag(self):
        # To be added in https://jira.mariadb.org/browse/MDEV-12981.
        return not self.connection.mysql_is_mariadb
