from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import InterfaceError

try:
    import pytz
except ImportError:
    pytz = None


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    interprets_empty_strings_as_nulls = True
    uses_savepoints = True
    has_select_for_update = True
    has_select_for_update_nowait = True
    can_return_id_from_insert = True
    allow_sliced_subqueries = False
    supports_subqueries_in_group_by = False
    supports_transactions = True
    supports_timezones = False
    has_zoneinfo_database = pytz is not None
    supports_bitwise_or = False
    has_native_duration_field = True
    can_defer_constraint_checks = True
    supports_partially_nullable_unique_constraints = False
    truncates_names = True
    has_bulk_insert = True
    supports_tablespaces = True
    supports_sequence_reset = False
    can_introspect_default = False  # Pending implementation by an interested person.
    can_introspect_max_length = False
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

    def introspected_boolean_field_type(self, field=None, created_separately=False):
        """
        Some versions of Oracle -- we've seen this on 11.2.0.1 and suspect
        it goes back -- have a weird bug where, when an integer column is
        added to an existing table with a default, its precision is later
        reported on introspection as 0, regardless of the real precision.
        For Django introspection, this means that such columns are reported
        as IntegerField even if they are really BigIntegerField or BooleanField.

        The bug is solved in Oracle 11.2.0.2 and up.
        """
        if self.connection.oracle_full_version < '11.2.0.2' and field and field.has_default() and created_separately:
            return 'IntegerField'
        return super(DatabaseFeatures, self).introspected_boolean_field_type(field, created_separately)
