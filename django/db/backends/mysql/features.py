import operator

from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    related_fields_match_type = True
    # MySQL doesn't support sliced subqueries with IN/ALL/ANY/SOME.
    allow_sliced_subqueries_with_in = False
    has_select_for_update = True
    has_select_for_update_nowait = True
    has_select_for_update_skip_locked = True
    supports_forward_references = False
    supports_regex_backreferencing = False
    supports_date_lookup_using_string = False
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    atomic_transactions = False
    can_clone_databases = True
    supports_aggregate_order_by_clause = True
    supports_comments = True
    supports_comments_inline = True
    supports_temporal_subtraction = True
    supports_slicing_ordering_in_compound = True
    supports_index_on_text_field = False
    supports_over_clause = True
    supports_frame_range_fixed_distance = True
    supports_update_conflicts = True
    can_rename_index = True
    delete_can_self_reference_subquery = False
    create_test_procedure_without_params_sql = """
        CREATE PROCEDURE test_procedure ()
        BEGIN
            DECLARE V_I INTEGER;
            SET V_I = 1;
        END;
    """
    create_test_procedure_with_int_param_sql = """
        CREATE PROCEDURE test_procedure (P_I INTEGER)
        BEGIN
            DECLARE V_I INTEGER;
            SET V_I = P_I;
        END;
    """
    # Neither MySQL nor MariaDB support partial indexes.
    supports_partial_indexes = False
    # COLLATE must be wrapped in parentheses because MySQL treats COLLATE as an
    # indexed expression.
    collate_as_index_expression = True
    insert_test_table_with_defaults = "INSERT INTO {} () VALUES ()"

    supports_order_by_nulls_modifier = False
    order_by_nulls_first = True
    supports_logical_xor = True

    supports_stored_generated_columns = True
    supports_virtual_generated_columns = True

    supports_json_negative_indexing = False

    @cached_property
    def minimum_database_version(self):
        if self.connection.mysql_is_mariadb:
            return (10, 6)
        else:
            return (8, 0, 11)

    @cached_property
    def test_collations(self):
        return {
            "ci": "utf8mb4_general_ci",
            "non_default": "utf8mb4_esperanto_ci",
            "swedish_ci": "utf8mb4_swedish_ci",
            "virtual": "utf8mb4_esperanto_ci",
        }

    test_now_utc_template = "UTC_TIMESTAMP(6)"

    @cached_property
    def django_test_skips(self):
        skips = {
            "This doesn't work on MySQL.": {
                "db_functions.comparison.test_greatest.GreatestTests."
                "test_coalesce_workaround",
                "db_functions.comparison.test_least.LeastTests."
                "test_coalesce_workaround",
            },
            "MySQL doesn't support functional indexes on a function that "
            "returns JSON": {
                "schema.tests.SchemaTests.test_func_index_json_key_transform",
            },
            "MySQL supports multiplying and dividing DurationFields by a "
            "scalar value but it's not implemented (#25287).": {
                "expressions.tests.FTimeDeltaTests.test_durationfield_multiply_divide",
            },
            "UPDATE ... ORDER BY syntax on MySQL/MariaDB does not support ordering by"
            "related fields.": {
                "update.tests.AdvancedTests."
                "test_update_ordered_by_inline_m2m_annotation",
                "update.tests.AdvancedTests.test_update_ordered_by_m2m_annotation",
                "update.tests.AdvancedTests.test_update_ordered_by_m2m_annotation_desc",
            },
        }
        if not self.supports_explain_analyze:
            skips.update(
                {
                    "MariaDB and MySQL >= 8.0.18 specific.": {
                        "queries.test_explain.ExplainTests.test_mysql_analyze",
                    },
                }
            )
        if self.connection.mysql_version < (8, 0, 31):
            skips.update(
                {
                    "Nesting of UNIONs at the right-hand side is not supported on "
                    "MySQL < 8.0.31": {
                        "queries.test_qs_combinators.QuerySetSetOperationTests."
                        "test_union_nested"
                    },
                }
            )
        if not self.connection.mysql_is_mariadb:
            skips.update(
                {
                    "MySQL doesn't allow renaming columns referenced by generated "
                    "columns": {
                        "migrations.test_operations.OperationTests."
                        "test_invalid_generated_field_changes_on_rename_stored",
                        "migrations.test_operations.OperationTests."
                        "test_invalid_generated_field_changes_on_rename_virtual",
                    },
                }
            )
        return skips

    @cached_property
    def _mysql_storage_engine(self):
        """
        Internal method used in Django tests. Don't rely on this from your code
        """
        return self.connection.mysql_server_data["default_storage_engine"]

    @cached_property
    def allows_auto_pk_0(self):
        """
        Autoincrement primary key can be set to 0 if it doesn't generate new
        autoincrement values.
        """
        return "NO_AUTO_VALUE_ON_ZERO" in self.connection.sql_mode

    @cached_property
    def update_can_self_select(self):
        return self.connection.mysql_is_mariadb

    @cached_property
    def can_introspect_foreign_keys(self):
        "Confirm support for introspected foreign keys"
        return self._mysql_storage_engine != "MyISAM"

    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            "BinaryField": "TextField",
            "BooleanField": "IntegerField",
            "DurationField": "BigIntegerField",
            "GenericIPAddressField": "CharField",
        }

    @cached_property
    def can_return_columns_from_insert(self):
        return self.connection.mysql_is_mariadb

    can_return_rows_from_bulk_insert = property(
        operator.attrgetter("can_return_columns_from_insert")
    )

    @cached_property
    def has_zoneinfo_database(self):
        return self.connection.mysql_server_data["has_zoneinfo_database"]

    @cached_property
    def is_sql_auto_is_null_enabled(self):
        return self.connection.mysql_server_data["sql_auto_is_null"]

    @cached_property
    def supports_column_check_constraints(self):
        if self.connection.mysql_is_mariadb:
            return True
        return self.connection.mysql_version >= (8, 0, 16)

    supports_table_check_constraints = property(
        operator.attrgetter("supports_column_check_constraints")
    )

    @cached_property
    def can_introspect_check_constraints(self):
        if self.connection.mysql_is_mariadb:
            return True
        return self.connection.mysql_version >= (8, 0, 16)

    @cached_property
    def has_select_for_update_of(self):
        return not self.connection.mysql_is_mariadb

    @cached_property
    def supports_explain_analyze(self):
        return self.connection.mysql_is_mariadb or self.connection.mysql_version >= (
            8,
            0,
            18,
        )

    @cached_property
    def supported_explain_formats(self):
        # Alias MySQL's TRADITIONAL to TEXT for consistency with other
        # backends.
        formats = {"JSON", "TEXT", "TRADITIONAL"}
        if not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (
            8,
            0,
            16,
        ):
            formats.add("TREE")
        return formats

    @cached_property
    def supports_transactions(self):
        """
        All storage engines except MyISAM support transactions.
        """
        return self._mysql_storage_engine != "MyISAM"

    @cached_property
    def ignores_table_name_case(self):
        return self.connection.mysql_server_data["lower_case_table_names"]

    @cached_property
    def supports_default_in_lead_lag(self):
        # To be added in https://jira.mariadb.org/browse/MDEV-12981.
        return not self.connection.mysql_is_mariadb

    @cached_property
    def can_introspect_json_field(self):
        if self.connection.mysql_is_mariadb:
            return self.can_introspect_check_constraints
        return True

    @cached_property
    def supports_index_column_ordering(self):
        if self._mysql_storage_engine != "InnoDB":
            return False
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 8)
        return True

    @cached_property
    def supports_expression_indexes(self):
        return (
            not self.connection.mysql_is_mariadb
            and self._mysql_storage_engine != "MyISAM"
            and self.connection.mysql_version >= (8, 0, 13)
        )

    @cached_property
    def supports_select_intersection(self):
        is_mariadb = self.connection.mysql_is_mariadb
        return is_mariadb or self.connection.mysql_version >= (8, 0, 31)

    supports_select_difference = property(
        operator.attrgetter("supports_select_intersection")
    )

    @cached_property
    def supports_expression_defaults(self):
        if self.connection.mysql_is_mariadb:
            return True
        return self.connection.mysql_version >= (8, 0, 13)

    @cached_property
    def has_native_uuid_field(self):
        is_mariadb = self.connection.mysql_is_mariadb
        return is_mariadb and self.connection.mysql_version >= (10, 7)

    @cached_property
    def allows_group_by_selected_pks(self):
        if self.connection.mysql_is_mariadb:
            return "ONLY_FULL_GROUP_BY" not in self.connection.sql_mode
        return True

    @cached_property
    def supports_any_value(self):
        return not self.connection.mysql_is_mariadb
