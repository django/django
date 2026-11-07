"""
Features for DuckDB backend.
"""

from django.db.backends.base.features import BaseDatabaseFeatures


class DatabaseFeatures(BaseDatabaseFeatures):
    minimum_database_version = (2, 0)
    test_db_allows_multiple_connections = True
    supports_unspecified_pk = False
    supports_timezones = False
    supports_transactions = True
    uses_savepoints = False
    can_rollback_ddl = True
    can_create_inline_fk = True
    requires_literal_defaults = False
    can_clone_databases = False
    supports_temporal_subtraction = True
    ignores_table_name_case = False
    supports_cast_with_precision = True
    can_release_savepoints = True
    has_case_insensitive_like = True
    supports_parentheses_in_compound = True
    can_defer_constraint_checks = False
    supports_over_clause = True
    supports_frame_range_fixed_distance = True
    supports_frame_exclusion = True
    supports_aggregate_filter_clause = True
    supports_aggregate_order_by_clause = True
    supports_aggregate_distinct_multiple_argument = True
    supports_any_value = True
    order_by_nulls_first = True
    supports_json_field_contains = True
    supports_update_conflicts = True
    supports_update_conflicts_with_target = True
    supports_stored_generated_columns = True
    supports_virtual_generated_columns = True
    supports_default_keyword_in_insert = True
    supports_unlimited_charfield = True
    supports_no_precision_decimalfield = True
    can_return_columns_from_insert = True
    can_return_rows_from_bulk_insert = True
    can_return_rows_from_update = True
    supports_uuid4_function = False
    supports_json_field = True
    can_introspect_json_field = True
    has_json_object_function = True
    supports_deferrable_unique_constraints = False
    allows_group_by_pk = True
    supports_migrate_user = True
    supports_at_time_zone_in_portion = False
    supports_subqueries_in_group_by = True
    can_distinct_on_fields = False
    supports_temp_tables = True
    supports_slicing_ordering_in_compound = True
    supports_combined_alters = True
    related_fields_match_type = True
    supports_expression_defaults = True
    supports_intersect = True
    supports_difference = True
    supports_covering_indexes = False
    supports_partial_indexes = True
    supports_nulls_distinct_unique_constraints = True
    supports_index_on_expression = True
    supports_sequence_reset = False
    can_rename_columns = True
    can_rename_columns_atomic = True
    can_rename_index = True
    schema_editor_uses_db_defaults = True
    supports_bare_select_union = True
    supports_deferrable_unique_constraints = False
    test_collations = {
        "virtual": "unicode",
    }
    test_collations_with_casing = {
        "virtual": "unicode",
    }
    insert_test_table_with_defaults = 'INSERT INTO {} DEFAULT VALUES'
