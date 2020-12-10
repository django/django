import operator

from django.db import InterfaceError
from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    allows_group_by_selected_pks = True
    can_return_columns_from_insert = True
    can_return_rows_from_bulk_insert = True
    has_real_datatype = True
    has_native_uuid_field = True
    has_native_duration_field = True
    has_native_json_field = True
    can_defer_constraint_checks = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_select_for_update_of = True
    has_select_for_update_skip_locked = True
    has_select_for_no_key_update = True
    can_release_savepoints = True
    supports_tablespaces = True
    supports_transactions = True
    can_introspect_materialized_views = True
    can_distinct_on_fields = True
    can_rollback_ddl = True
    supports_combined_alters = True
    nulls_order_largest = True
    closed_cursor_error_class = InterfaceError
    has_case_insensitive_like = False
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
    requires_casted_case_in_updates = True
    supports_over_clause = True
    only_supports_unbounded_with_preceding_and_following = True
    supports_aggregate_filter_clause = True
    supported_explain_formats = {'JSON', 'TEXT', 'XML', 'YAML'}
    validates_explain_options = False  # A query will error on invalid options.
    supports_deferrable_unique_constraints = True
    has_json_operators = True
    json_key_contains_list_matching_requires_list = True

    django_test_skips = {
        'opclasses are PostgreSQL only.': {
            'indexes.tests.SchemaIndexesNotPostgreSQLTests.test_create_index_ignores_opclasses',
        },
    }

    @cached_property
    def test_collations(self):
        # PostgreSQL < 10 doesn't support ICU collations.
        if self.is_postgresql_10:
            return {
                'non_default': 'sv-x-icu',
                'swedish_ci': 'sv-x-icu',
            }
        return {}

    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            'PositiveBigIntegerField': 'BigIntegerField',
            'PositiveIntegerField': 'IntegerField',
            'PositiveSmallIntegerField': 'SmallIntegerField',
        }

    @cached_property
    def is_postgresql_10(self):
        return self.connection.pg_version >= 100000

    @cached_property
    def is_postgresql_11(self):
        return self.connection.pg_version >= 110000

    @cached_property
    def is_postgresql_12(self):
        return self.connection.pg_version >= 120000

    @cached_property
    def is_postgresql_13(self):
        return self.connection.pg_version >= 130000

    has_brin_autosummarize = property(operator.attrgetter('is_postgresql_10'))
    has_websearch_to_tsquery = property(operator.attrgetter('is_postgresql_11'))
    supports_table_partitions = property(operator.attrgetter('is_postgresql_10'))
    supports_covering_indexes = property(operator.attrgetter('is_postgresql_11'))
    supports_covering_gist_indexes = property(operator.attrgetter('is_postgresql_12'))
    supports_non_deterministic_collations = property(operator.attrgetter('is_postgresql_12'))
    supports_alternate_collation_providers = property(operator.attrgetter('is_postgresql_10'))
