import operator

from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property


class DatabaseFeatures(BaseDatabaseFeatures):
    empty_fetchmany_value = ()
    allows_group_by_pk = True
    related_fields_match_type = True
    # MySQL doesn't support sliced subqueries with IN/ALL/ANY/SOME.
    allow_sliced_subqueries_with_in = False
    has_select_for_update = True
    supports_forward_references = False
    supports_regex_backreferencing = False
    supports_date_lookup_using_string = False
    supports_timezones = False
    requires_explicit_null_ordering_when_grouping = True
    can_release_savepoints = True
    atomic_transactions = False
    can_clone_databases = True
    supports_temporal_subtraction = True
    supports_select_intersection = False
    supports_select_difference = False
    supports_slicing_ordering_in_compound = True
    supports_index_on_text_field = False
    has_case_insensitive_like = False
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

    supports_order_by_nulls_modifier = False
    order_by_nulls_first = True

    @cached_property
    def test_collations(self):
        charset = 'utf8'
        if self.connection.mysql_is_mariadb and self.connection.mysql_version >= (10, 6):
            # utf8 is an alias for utf8mb3 in MariaDB 10.6+.
            charset = 'utf8mb3'
        return {
            'ci': f'{charset}_general_ci',
            'non_default': f'{charset}_esperanto_ci',
            'swedish_ci': f'{charset}_swedish_ci',
        }

    @cached_property
    def django_test_skips(self):
        skips = {
            "This doesn't work on MySQL.": {
                'db_functions.comparison.test_greatest.GreatestTests.test_coalesce_workaround',
                'db_functions.comparison.test_least.LeastTests.test_coalesce_workaround',
            },
            'Running on MySQL requires utf8mb4 encoding (#18392).': {
                'model_fields.test_textfield.TextFieldTests.test_emoji',
                'model_fields.test_charfield.TestCharField.test_emoji',
            },
            "MySQL doesn't support functional indexes on a function that "
            "returns JSON": {
                'schema.tests.SchemaTests.test_func_index_json_key_transform',
            },
        }
        if 'ONLY_FULL_GROUP_BY' in self.connection.sql_mode:
            skips.update({
                'GROUP BY optimization does not work properly when '
                'ONLY_FULL_GROUP_BY mode is enabled on MySQL, see #31331.': {
                    'aggregation.tests.AggregateTestCase.test_aggregation_subquery_annotation_multivalued',
                    'annotations.tests.NonAggregateAnnotationTestCase.test_annotation_aggregate_with_m2o',
                },
            })
        if (
            self.connection.mysql_is_mariadb and
            (10, 4, 3) < self.connection.mysql_version < (10, 5, 2)
        ):
            skips.update({
                'https://jira.mariadb.org/browse/MDEV-19598': {
                    'schema.tests.SchemaTests.test_alter_not_unique_field_to_primary_key',
                },
            })
        if (
            self.connection.mysql_is_mariadb and
            (10, 4, 12) < self.connection.mysql_version < (10, 5)
        ):
            skips.update({
                'https://jira.mariadb.org/browse/MDEV-22775': {
                    'schema.tests.SchemaTests.test_alter_pk_with_self_referential_field',
                },
            })
        if not self.supports_explain_analyze:
            skips.update({
                'MariaDB and MySQL >= 8.0.18 specific.': {
                    'queries.test_explain.ExplainTests.test_mysql_analyze',
                },
            })
        return skips

    @cached_property
    def _mysql_storage_engine(self):
        "Internal method used in Django tests. Don't rely on this from your code"
        return self.connection.mysql_server_data['default_storage_engine']

    @cached_property
    def allows_auto_pk_0(self):
        """
        Autoincrement primary key can be set to 0 if it doesn't generate new
        autoincrement values.
        """
        return 'NO_AUTO_VALUE_ON_ZERO' in self.connection.sql_mode

    @cached_property
    def update_can_self_select(self):
        return self.connection.mysql_is_mariadb and self.connection.mysql_version >= (10, 3, 2)

    @cached_property
    def can_introspect_foreign_keys(self):
        "Confirm support for introspected foreign keys"
        return self._mysql_storage_engine != 'MyISAM'

    @cached_property
    def introspected_field_types(self):
        return {
            **super().introspected_field_types,
            'BinaryField': 'TextField',
            'BooleanField': 'IntegerField',
            'DurationField': 'BigIntegerField',
            'GenericIPAddressField': 'CharField',
        }

    @cached_property
    def can_return_columns_from_insert(self):
        return self.connection.mysql_is_mariadb and self.connection.mysql_version >= (10, 5, 0)

    can_return_rows_from_bulk_insert = property(operator.attrgetter('can_return_columns_from_insert'))

    @cached_property
    def has_zoneinfo_database(self):
        return self.connection.mysql_server_data['has_zoneinfo_database']

    @cached_property
    def is_sql_auto_is_null_enabled(self):
        return self.connection.mysql_server_data['sql_auto_is_null']

    @cached_property
    def supports_over_clause(self):
        if self.connection.mysql_is_mariadb:
            return True
        return self.connection.mysql_version >= (8, 0, 2)

    supports_frame_range_fixed_distance = property(operator.attrgetter('supports_over_clause'))

    @cached_property
    def supports_column_check_constraints(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 2, 1)
        return self.connection.mysql_version >= (8, 0, 16)

    supports_table_check_constraints = property(operator.attrgetter('supports_column_check_constraints'))

    @cached_property
    def can_introspect_check_constraints(self):
        if self.connection.mysql_is_mariadb:
            version = self.connection.mysql_version
            return (version >= (10, 2, 22) and version < (10, 3)) or version >= (10, 3, 10)
        return self.connection.mysql_version >= (8, 0, 16)

    @cached_property
    def has_select_for_update_skip_locked(self):
        return not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (8, 0, 1)

    @cached_property
    def has_select_for_update_nowait(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 3, 0)
        return self.connection.mysql_version >= (8, 0, 1)

    @cached_property
    def has_select_for_update_of(self):
        return not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (8, 0, 1)

    @cached_property
    def supports_explain_analyze(self):
        return self.connection.mysql_is_mariadb or self.connection.mysql_version >= (8, 0, 18)

    @cached_property
    def supported_explain_formats(self):
        # Alias MySQL's TRADITIONAL to TEXT for consistency with other
        # backends.
        formats = {'JSON', 'TEXT', 'TRADITIONAL'}
        if not self.connection.mysql_is_mariadb and self.connection.mysql_version >= (8, 0, 16):
            formats.add('TREE')
        return formats

    @cached_property
    def supports_transactions(self):
        """
        All storage engines except MyISAM support transactions.
        """
        return self._mysql_storage_engine != 'MyISAM'

    @cached_property
    def ignores_table_name_case(self):
        return self.connection.mysql_server_data['lower_case_table_names']

    @cached_property
    def supports_default_in_lead_lag(self):
        # To be added in https://jira.mariadb.org/browse/MDEV-12981.
        return not self.connection.mysql_is_mariadb

    @cached_property
    def supports_json_field(self):
        if self.connection.mysql_is_mariadb:
            return self.connection.mysql_version >= (10, 2, 7)
        return self.connection.mysql_version >= (5, 7, 8)

    @cached_property
    def can_introspect_json_field(self):
        if self.connection.mysql_is_mariadb:
            return self.supports_json_field and self.can_introspect_check_constraints
        return self.supports_json_field

    @cached_property
    def supports_index_column_ordering(self):
        return (
            not self.connection.mysql_is_mariadb and
            self.connection.mysql_version >= (8, 0, 1)
        )

    @cached_property
    def supports_expression_indexes(self):
        return (
            not self.connection.mysql_is_mariadb and
            self.connection.mysql_version >= (8, 0, 13)
        )
