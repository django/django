import operator
import platform

from django.db import transaction
from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import OperationalError
from django.utils.functional import cached_property

from .base import Database


class DatabaseFeatures(BaseDatabaseFeatures):
    # SQLite can read from a cursor since SQLite 3.6.5, subject to the caveat
    # that statements within a connection aren't isolated from each other. See
    # https://sqlite.org/isolation.html.
    can_use_chunked_reads = True
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True
    supports_timezones = False
    max_query_params = 999
    supports_mixed_date_datetime_comparisons = False
    supports_transactions = True
    atomic_transactions = False
    can_rollback_ddl = True
    can_create_inline_fk = False
    supports_paramstyle_pyformat = False
    can_clone_databases = True
    supports_temporal_subtraction = True
    ignores_table_name_case = True
    supports_cast_with_precision = False
    time_cast_precision = 3
    can_release_savepoints = True
    # Is "ALTER TABLE ... RENAME COLUMN" supported?
    can_alter_table_rename_column = Database.sqlite_version_info >= (3, 25, 0)
    supports_parentheses_in_compound = False
    # Deferred constraint checks can be emulated on SQLite < 3.20 but not in a
    # reasonably performant way.
    supports_pragma_foreign_key_check = Database.sqlite_version_info >= (3, 20, 0)
    can_defer_constraint_checks = supports_pragma_foreign_key_check
    supports_functions_in_partial_indexes = Database.sqlite_version_info >= (3, 15, 0)
    supports_over_clause = Database.sqlite_version_info >= (3, 25, 0)
    supports_frame_range_fixed_distance = Database.sqlite_version_info >= (3, 28, 0)
    supports_aggregate_filter_clause = Database.sqlite_version_info >= (3, 30, 1)
    supports_order_by_nulls_modifier = Database.sqlite_version_info >= (3, 30, 0)
    order_by_nulls_first = True
    supports_json_field_contains = False
    test_collations = {
        'ci': 'nocase',
        'cs': 'binary',
        'non_default': 'nocase',
    }

    @cached_property
    def supports_atomic_references_rename(self):
        # SQLite 3.28.0 bundled with MacOS 10.15 does not support renaming
        # references atomically.
        if platform.mac_ver()[0].startswith('10.15.') and Database.sqlite_version_info == (3, 28, 0):
            return False
        return Database.sqlite_version_info >= (3, 26, 0)

    @cached_property
    def introspected_field_types(self):
        return{
            **super().introspected_field_types,
            'BigAutoField': 'AutoField',
            'DurationField': 'BigIntegerField',
            'GenericIPAddressField': 'CharField',
            'SmallAutoField': 'AutoField',
        }

    @cached_property
    def supports_json_field(self):
        try:
            with self.connection.cursor() as cursor, transaction.atomic():
                cursor.execute('SELECT JSON(\'{"a": "b"}\')')
        except OperationalError:
            return False
        return True

    can_introspect_json_field = property(operator.attrgetter('supports_json_field'))
