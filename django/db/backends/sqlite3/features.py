import operator

from django.db import transaction
from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import OperationalError
from django.utils.functional import cached_property

from .base import Database


class DatabaseFeatures(BaseDatabaseFeatures):
    minimum_database_version = (3, 9)
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True
    supports_timezones = False
    max_query_params = 999
    supports_transactions = True
    atomic_transactions = False
    can_rollback_ddl = True
    can_create_inline_fk = False
    requires_literal_defaults = True
    can_clone_databases = True
    supports_temporal_subtraction = True
    ignores_table_name_case = True
    supports_cast_with_precision = False
    time_cast_precision = 3
    can_release_savepoints = True
    has_case_insensitive_like = True
    # Is "ALTER TABLE ... RENAME COLUMN" supported?
    can_alter_table_rename_column = Database.sqlite_version_info >= (3, 25, 0)
    # Is "ALTER TABLE ... DROP COLUMN" supported?
    can_alter_table_drop_column = Database.sqlite_version_info >= (3, 35, 5)
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
    # NULLS LAST/FIRST emulation on < 3.30 requires subquery wrapping.
    requires_compound_order_by_subquery = Database.sqlite_version_info < (3, 30)
    order_by_nulls_first = True
    supports_json_field_contains = False
    supports_update_conflicts = Database.sqlite_version_info >= (3, 24, 0)
    supports_update_conflicts_with_target = supports_update_conflicts
    test_collations = {
        "ci": "nocase",
        "cs": "binary",
        "non_default": "nocase",
    }
    django_test_expected_failures = {
        # The django_format_dtdelta() function doesn't properly handle mixed
        # Date/DateTime fields and timedeltas.
        "expressions.tests.FTimeDeltaTests.test_mixed_comparisons1",
    }
    create_test_table_with_composite_primary_key = """
        CREATE TABLE test_table_composite_pk (
            column_1 INTEGER NOT NULL,
            column_2 INTEGER NOT NULL,
            PRIMARY KEY(column_1, column_2)
        )
    """

    @cached_property
    def django_test_skips(self):
        skips = {
            "SQLite stores values rounded to 15 significant digits.": {
                "model_fields.test_decimalfield.DecimalFieldTests."
                "test_fetch_from_db_without_float_rounding",
            },
            "SQLite naively remakes the table on field alteration.": {
                "schema.tests.SchemaTests.test_unique_no_unnecessary_fk_drops",
                "schema.tests.SchemaTests.test_unique_and_reverse_m2m",
                "schema.tests.SchemaTests."
                "test_alter_field_default_doesnt_perform_queries",
                "schema.tests.SchemaTests."
                "test_rename_column_renames_deferred_sql_references",
            },
            "SQLite doesn't support negative precision for ROUND().": {
                "db_functions.math.test_round.RoundTests."
                "test_null_with_negative_precision",
                "db_functions.math.test_round.RoundTests."
                "test_decimal_with_negative_precision",
                "db_functions.math.test_round.RoundTests."
                "test_float_with_negative_precision",
                "db_functions.math.test_round.RoundTests."
                "test_integer_with_negative_precision",
            },
        }
        if Database.sqlite_version_info < (3, 27):
            skips.update(
                {
                    "Nondeterministic failure on SQLite < 3.27.": {
                        "expressions_window.tests.WindowFunctionTests."
                        "test_subquery_row_range_rank",
                    },
                }
            )
        if self.connection.is_in_memory_db():
            skips.update(
                {
                    "the sqlite backend's close() method is a no-op when using an "
                    "in-memory database": {
                        "servers.test_liveserverthread.LiveServerThreadTest."
                        "test_closes_connections",
                        "servers.tests.LiveServerTestCloseConnectionTest."
                        "test_closes_connections",
                    },
                }
            )
        else:
            skips.update(
                {
                    "Only connections to in-memory SQLite databases are passed to the "
                    "server thread.": {
                        "servers.tests.LiveServerInMemoryDatabaseLockTest."
                        "test_in_memory_database_lock",
                    },
                }
            )
        return skips

    @cached_property
    def supports_atomic_references_rename(self):
        return Database.sqlite_version_info >= (3, 26, 0)

    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            "BigAutoField": "AutoField",
            "DurationField": "BigIntegerField",
            "GenericIPAddressField": "CharField",
            "SmallAutoField": "AutoField",
        }

    @cached_property
    def supports_json_field(self):
        with self.connection.cursor() as cursor:
            try:
                with transaction.atomic(self.connection.alias):
                    cursor.execute('SELECT JSON(\'{"a": "b"}\')')
            except OperationalError:
                return False
        return True

    can_introspect_json_field = property(operator.attrgetter("supports_json_field"))
    has_json_object_function = property(operator.attrgetter("supports_json_field"))

    @cached_property
    def can_return_columns_from_insert(self):
        return Database.sqlite_version_info >= (3, 35)

    can_return_rows_from_bulk_insert = property(
        operator.attrgetter("can_return_columns_from_insert")
    )
