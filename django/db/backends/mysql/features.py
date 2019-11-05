import operator

from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
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
    # Neither MySQL nor MariaDB support partial indexes.
    supports_partial_indexes = False
    supports_order_by_nulls_modifier = False

    @cached_property
    def _mysql_storage_engine(self):
        "Internal method used in Django tests. Don't rely on this from your code"
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT ENGINE FROM INFORMATION_SCHEMA.ENGINES WHERE SUPPORT = 'DEFAULT'")
            result = cursor.fetchone()
        return result[0]

    @cached_property
    def update_can_self_select(self):
        return self.connection.mysql_is_mariadb and self.connection.mysql_version >= (10, 3, 2)

    @cached_property
    def can_introspect_foreign_keys(self):
        "Confirm support for introspected foreign keys"
        return self._mysql_storage_engine != 'MyISAM'

    @cached_property
    def has_zoneinfo_database(self):
        # Test if the time zone definitions are installed. CONVERT_TZ returns
        # NULL if 'UTC' timezone isn't loaded into the mysql.time_zone.
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT CONVERT_TZ('2001-01-01 01:00:00', 'UTC', 'UTC')")
            return cursor.fetchone()[0] is not None

    @cached_property
    def is_sql_auto_is_null_enabled(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT @@SQL_AUTO_IS_NULL')
            result = cursor.fetchone()
            return result and result[0] == 1

    @cached_property
    def supports_over_clause(self):
        if self.connection.mysql_is_mariadb:
            return True
        return self.connection.mysql_version >= (8, 0, 2)

    supports_frame_range_fixed_distance = property(operator.attrgetter('supports_over_clause'))

    @cached_property
    def supports_column_check_constraints(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 2, 1)
        return self.connection.mysql_version >= (8, 0, 16)

    supports_table_check_constraints = property(operator.attrgetter('supports_column_check_constraints'))

    @cached_property
    def can_introspect_check_constraints(self):
        if self.connection.mysql_is_mariadb:
            version = self.connection.mysql_version
            return (version >= (10, 2, 22) and version < (10, 3)) or version >= (10, 3, 10)
        return self.connection.mysql_version >= (8, 0, 16)

    @cached_property
    def has_select_for_update_skip_locked(self):
        return not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (8, 0, 1)

    @cached_property
    def has_select_for_update_nowait(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 3, 0)
        return self.connection.mysql_version >= (8, 0, 1)

    @cached_property
    def needs_explain_extended(self):
        # EXTENDED is deprecated (and not required) in MySQL 5.7.
        return not self.connection.mysql_is_mariadb and self.connection.mysql_version < (5, 7)

    @cached_property
    def supports_explain_analyze(self):
        return self.connection.mysql_is_mariadb or self.connection.mysql_version >= (8, 0, 18)

    @cached_property
    def supported_explain_formats(self):
        # Alias MySQL's TRADITIONAL to TEXT for consistency with other
        # backends.
        formats = {'JSON', 'TEXT', 'TRADITIONAL'}
        if not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (8, 0, 16):
            formats.add('TREE')
        return formats

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
