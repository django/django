import sys

from django.db.backends.base.features import BaseDatabaseFeatures

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
    autocommits_when_autocommit_is_off = sys.version_info < (3, 6)
    can_introspect_autofield = True
    can_introspect_decimal_field = False
    can_introspect_duration_field = False
    can_introspect_positive_integer_field = True
    can_introspect_small_integer_field = True
    introspected_big_auto_field_type = 'AutoField'
    supports_transactions = True
    atomic_transactions = False
    can_rollback_ddl = True
    supports_atomic_references_rename = Database.sqlite_version_info >= (3, 26, 0)
    supports_paramstyle_pyformat = False
    supports_sequence_reset = False
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
