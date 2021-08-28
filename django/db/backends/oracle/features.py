from django.db import DatabaseError, InterfaceError
from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    # Oracle crashes with "ORA-00932: inconsistent datatypes: expected - got
    # BLOB" when grouping by LOBs (#24096).
    allows_group_by_lob = False
    interprets_empty_strings_as_nulls = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_select_for_update_skip_locked = True
    has_select_for_update_of = True
    select_for_update_of_column = True
    can_return_columns_from_insert = True
    supports_subqueries_in_group_by = False
    ignores_unnecessary_order_by_in_subqueries = False
    supports_transactions = True
    supports_timezones = False
    has_native_duration_field = True
    can_defer_constraint_checks = True
    supports_partially_nullable_unique_constraints = False
    supports_deferrable_unique_constraints = True
    truncates_names = True
    supports_tablespaces = True
    supports_sequence_reset = False
    can_introspect_materialized_views = True
    atomic_transactions = False
    supports_combined_alters = False
    nulls_order_largest = True
    requires_literal_defaults = True
    closed_cursor_error_class = InterfaceError
    bare_select_suffix = " FROM DUAL"
    # select for update with limit can be achieved on Oracle, but not with the current backend.
    supports_select_for_update_with_limit = False
    supports_temporal_subtraction = True
    # Oracle doesn't ignore quoted identifiers case but the current backend
    # does by uppercasing all identifiers.
    ignores_table_name_case = True
    supports_index_on_text_field = False
    has_case_insensitive_like = False
    create_test_procedure_without_params_sql = """
        CREATE PROCEDURE "TEST_PROCEDURE" AS
            V_I INTEGER;
        BEGIN
            V_I := 1;
        END;
    """
    create_test_procedure_with_int_param_sql = """
        CREATE PROCEDURE "TEST_PROCEDURE" (P_I INTEGER) AS
            V_I INTEGER;
        BEGIN
            V_I := P_I;
        END;
    """
    supports_callproc_kwargs = True
    supports_over_clause = True
    supports_frame_range_fixed_distance = True
    supports_ignore_conflicts = False
    max_query_params = 2**16 - 1
    supports_partial_indexes = False
    supports_slicing_ordering_in_compound = True
    allows_multiple_constraints_on_same_fields = False
    supports_boolean_expr_in_select_clause = False
    supports_primitives_in_json_field = False
    supports_json_field_contains = False
    supports_collation_on_textfield = False
    test_collations = {
        'ci': 'BINARY_CI',
        'cs': 'BINARY',
        'non_default': 'SWEDISH_CI',
        'swedish_ci': 'SWEDISH_CI',
    }
    test_now_utc_template = "CURRENT_TIMESTAMP AT TIME ZONE 'UTC'"

    django_test_skips = {
        "Oracle doesn't support SHA224.": {
            'db_functions.text.test_sha224.SHA224Tests.test_basic',
            'db_functions.text.test_sha224.SHA224Tests.test_transform',
        },
        "Oracle doesn't support bitwise XOR.": {
            'expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_xor',
            'expressions.tests.ExpressionOperatorTests.test_lefthand_bitwise_xor_null',
        },
        "Oracle requires ORDER BY in row_number, ANSI:SQL doesn't.": {
            'expressions_window.tests.WindowFunctionTests.test_row_number_no_ordering',
        },
        'Raises ORA-00600: internal error code.': {
            'model_fields.test_jsonfield.TestQuerying.test_usage_in_subquery',
        },
    }
    django_test_expected_failures = {
        # A bug in Django/cx_Oracle with respect to string handling (#23843).
        'annotations.tests.NonAggregateAnnotationTestCase.test_custom_functions',
        'annotations.tests.NonAggregateAnnotationTestCase.test_custom_functions_can_ref_other_functions',
    }

    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            'GenericIPAddressField': 'CharField',
            'PositiveBigIntegerField': 'BigIntegerField',
            'PositiveIntegerField': 'IntegerField',
            'PositiveSmallIntegerField': 'IntegerField',
            'SmallIntegerField': 'IntegerField',
            'TimeField': 'DateTimeField',
        }

    @cached_property
    def supports_collation_on_charfield(self):
        with self.connection.cursor() as cursor:
            try:
                cursor.execute("SELECT CAST('a' AS VARCHAR2(4001)) FROM dual")
            except DatabaseError as e:
                if e.args[0].code == 910:
                    return False
                raise
            return True
