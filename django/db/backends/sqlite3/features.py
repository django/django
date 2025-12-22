import operator
import sqlite3

from django.db import transaction
from django.db.backends.base.features import BaseDatabaseFeatures
from django.db.utils import OperationalError
from django.utils.functional import cached_property

from .base import Database


class DatabaseFeatures(BaseDatabaseFeatures):
    minimum_database_version = (3, 31)
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True
    supports_timezones = False
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
    # Is "ALTER TABLE ... DROP COLUMN" supported?
    can_alter_table_drop_column = Database.sqlite_version_info >= (3, 35, 5)
    supports_parentheses_in_compound = False
    can_defer_constraint_checks = True
    supports_over_clause = True
    supports_frame_range_fixed_distance = True
    supports_frame_exclusion = True
    supports_aggregate_filter_clause = True
    supports_aggregate_order_by_clause = Database.sqlite_version_info >= (3, 44, 0)
    supports_aggregate_distinct_multiple_argument = False
    supports_any_value = True
    order_by_nulls_first = True
    supports_json_field_contains = False
    supports_update_conflicts = True
    supports_update_conflicts_with_target = True
    supports_stored_generated_columns = True
    supports_virtual_generated_columns = True
    test_collations = {
        "ci": "nocase",
        "cs": "binary",
        "non_default": "nocase",
        "virtual": "nocase",
    }
    django_test_expected_failures = {
        # The django_format_dtdelta() function doesn't properly handle mixed
        # Date/DateTime fields and timedeltas.
        "expressions.tests.FTimeDeltaTests.test_mixed_comparisons1",
    }
    insert_test_table_with_defaults = 'INSERT INTO {} ("null") VALUES (1)'
    supports_default_keyword_in_insert = False
    supports_unlimited_charfield = True

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
            "The actual query cannot be determined on SQLite": {
                "backends.base.test_base.ExecuteWrapperTests.test_wrapper_debug",
            },
        }
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
                    "For SQLite in-memory tests, closing the connection destroys "
                    "the database.": {
                        "test_utils.tests.AssertNumQueriesUponConnectionTests."
                        "test_ignores_connection_configuration_queries",
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
                    "multiprocessing's start method is checked only for in-memory "
                    "SQLite databases": {
                        "backends.sqlite.test_creation.TestDbSignatureTests."
                        "test_get_test_db_clone_settings_not_supported",
                    },
                }
            )
        if Database.sqlite_version_info < (3, 47):
            skips.update(
                {
                    "SQLite does not parse escaped double quotes in the JSON path "
                    "notation": {
                        "model_fields.test_jsonfield.TestQuerying."
                        "test_lookups_special_chars_double_quotes",
                    },
                }
            )
        return skips

    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            "BigAutoField": "AutoField",
            "DurationField": "BigIntegerField",
            "GenericIPAddressField": "CharField",
            "SmallAutoField": "AutoField",
        }

    @property
    def max_query_params(self):
        """
        SQLite has a variable limit per query. The limit can be changed using
        the SQLITE_MAX_VARIABLE_NUMBER compile-time option (which defaults to
        999 in versions < 3.32.0 or 32766 in newer versions) or lowered per
        connection at run-time with setlimit(SQLITE_LIMIT_VARIABLE_NUMBER, N).
        """
        self.connection.ensure_connection()
        return self.connection.connection.getlimit(sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER)

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

    can_return_rows_from_update = property(
        operator.attrgetter("can_return_columns_from_insert")
    )
