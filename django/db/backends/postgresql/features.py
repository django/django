from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import InterfaceError
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    allows_group_by_selected_pks = True
    can_return_id_from_insert = True
    can_return_ids_from_bulk_insert = True
    has_real_datatype = True
    has_native_uuid_field = True
    has_native_duration_field = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_select_for_update_of = True
    has_bulk_insert = True
    uses_savepoints = True
    can_release_savepoints = True
    supports_tablespaces = True
    supports_transactions = True
    can_introspect_autofield = True
    can_introspect_ip_address_field = True
    can_introspect_small_integer_field = True
    can_distinct_on_fields = True
    can_rollback_ddl = True
    supports_combined_alters = True
    nulls_order_largest = True
    closed_cursor_error_class = InterfaceError
    has_case_insensitive_like = False
    requires_sqlparse_for_splitting = False
    greatest_least_ignores_nulls = True
    can_clone_databases = True
    supports_temporal_subtraction = True
    supports_slicing_ordering_in_compound = True
    create_test_procedure_without_params_sql = """
        CREATE FUNCTION test_procedure () RETURNS void AS $$
        DECLARE
            V_I INTEGER;
        BEGIN
            V_I := 1;
        END;
    $$ LANGUAGE plpgsql;"""
    create_test_procedure_with_int_param_sql = """
        CREATE FUNCTION test_procedure (P_I INTEGER) RETURNS void AS $$
        DECLARE
            V_I INTEGER;
        BEGIN
            V_I := P_I;
        END;
    $$ LANGUAGE plpgsql;"""

    @cached_property
    def supports_aggregate_filter_clause(self):
        return self.connection.pg_version >= 90400

    @cached_property
    def has_select_for_update_skip_locked(self):
        return self.connection.pg_version >= 90500

    @cached_property
    def has_brin_index_support(self):
        return self.connection.pg_version >= 90500

    @cached_property
    def has_jsonb_datatype(self):
        return self.connection.pg_version >= 90400

    @cached_property
    def has_jsonb_agg(self):
        return self.connection.pg_version >= 90500

    @cached_property
    def has_gin_pending_list_limit(self):
        return self.connection.pg_version >= 90500
