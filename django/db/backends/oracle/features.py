from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import InterfaceError


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    interprets_empty_strings_as_nulls = True
    uses_savepoints = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_select_for_update_skip_locked = True
    has_select_for_update_of = True
    select_for_update_of_column = True
    can_return_id_from_insert = True
    allow_sliced_subqueries = False
    can_introspect_autofield = True
    supports_subqueries_in_group_by = False
    supports_transactions = True
    supports_timezones = False
    has_native_duration_field = True
    can_defer_constraint_checks = True
    supports_partially_nullable_unique_constraints = False
    truncates_names = True
    has_bulk_insert = True
    supports_tablespaces = True
    supports_sequence_reset = False
    can_introspect_time_field = False
    atomic_transactions = False
    supports_combined_alters = False
    nulls_order_largest = True
    requires_literal_defaults = True
    closed_cursor_error_class = InterfaceError
    bare_select_suffix = " FROM DUAL"
    uppercases_column_names = True
    # select for update with limit can be achieved on Oracle, but not with the current backend.
    supports_select_for_update_with_limit = False
    supports_temporal_subtraction = True
    # Oracle doesn't ignore quoted identifiers case but the current backend
    # does by uppercasing all identifiers.
    ignores_table_name_case = True
    supports_index_on_text_field = False
