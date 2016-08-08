from django.db.models.aggregates import StdDev
from django.db.utils import ProgrammingError
from django.utils.functional import cached_property


class BaseDatabaseFeatures(object):
    gis_enabled = False
    allows_group_by_pk = False
    allows_group_by_selected_pks = False
    empty_fetchmany_value = []
    update_can_self_select = True

    # Does the backend distinguish between '' and None?
    interprets_empty_strings_as_nulls = False

    # Does the backend allow inserting duplicate NULL rows in a nullable
    # unique field? All core backends implement this correctly, but other
    # databases such as SQL Server do not.
    supports_nullable_unique_constraints = True

    # Does the backend allow inserting duplicate rows when a unique_together
    # constraint exists and some fields are nullable but not all of them?
    supports_partially_nullable_unique_constraints = True

    can_use_chunked_reads = True
    can_return_id_from_insert = False
    can_return_ids_from_bulk_insert = False
    has_bulk_insert = False
    uses_savepoints = False
    can_release_savepoints = False
    can_combine_inserts_with_and_without_auto_increment_pk = False

    # If True, don't use integer foreign keys referring to, e.g., positive
    # integer primary keys.
    related_fields_match_type = False
    allow_sliced_subqueries = True
    has_select_for_update = False
    has_select_for_update_nowait = False
    has_select_for_update_skip_locked = False

    supports_select_related = True

    # Does the default test database allow multiple connections?
    # Usually an indication that the test database is in-memory
    test_db_allows_multiple_connections = True

    # Can an object be saved without an explicit primary key?
    supports_unspecified_pk = False

    # Can a fixture contain forward references? i.e., are
    # FK constraints checked at the end of transaction, or
    # at the end of each save operation?
    supports_forward_references = True

    # Does the backend truncate names properly when they are too long?
    truncates_names = False

    # Is there a REAL datatype in addition to floats/doubles?
    has_real_datatype = False
    supports_subqueries_in_group_by = True
    supports_bitwise_or = True

    # Is there a true datatype for uuid?
    has_native_uuid_field = False

    # Is there a true datatype for timedeltas?
    has_native_duration_field = False

    # Does the database driver supports same type temporal data subtraction
    # by returning the type used to store duration field?
    supports_temporal_subtraction = False

    # Does the database driver support timedeltas as arguments?
    # This is only relevant when there is a native duration field.
    # Specifically, there is a bug with cx_Oracle:
    # https://bitbucket.org/anthony_tuininga/cx_oracle/issue/7/
    driver_supports_timedelta_args = False

    # Do time/datetime fields have microsecond precision?
    supports_microsecond_precision = True

    # Does the __regex lookup support backreferencing and grouping?
    supports_regex_backreferencing = True

    # Can date/datetime lookups be performed using a string?
    supports_date_lookup_using_string = True

    # Can datetimes with timezones be used?
    supports_timezones = True

    # Does the database have a copy of the zoneinfo database?
    has_zoneinfo_database = True

    # When performing a GROUP BY, is an ORDER BY NULL required
    # to remove any ordering?
    requires_explicit_null_ordering_when_grouping = False

    # Does the backend order NULL values as largest or smallest?
    nulls_order_largest = False

    # Is there a 1000 item limit on query parameters?
    supports_1000_query_parameters = True

    # Can an object have an autoincrement primary key of 0? MySQL says No.
    allows_auto_pk_0 = True

    # Do we need to NULL a ForeignKey out, or can the constraint check be
    # deferred
    can_defer_constraint_checks = False

    # date_interval_sql can properly handle mixed Date/DateTime fields and timedeltas
    supports_mixed_date_datetime_comparisons = True

    # Does the backend support tablespaces? Default to False because it isn't
    # in the SQL standard.
    supports_tablespaces = False

    # Does the backend reset sequences between tests?
    supports_sequence_reset = True

    # Can the backend determine reliably the length of a CharField?
    can_introspect_max_length = True

    # Can the backend determine reliably if a field is nullable?
    # Note that this is separate from interprets_empty_strings_as_nulls,
    # although the latter feature, when true, interferes with correct
    # setting (and introspection) of CharFields' nullability.
    # This is True for all core backends.
    can_introspect_null = True

    # Can the backend introspect the default value of a column?
    can_introspect_default = True

    # Confirm support for introspected foreign keys
    # Every database can do this reliably, except MySQL,
    # which can't do it for MyISAM tables
    can_introspect_foreign_keys = True

    # Can the backend introspect an AutoField, instead of an IntegerField?
    can_introspect_autofield = False

    # Can the backend introspect a BigIntegerField, instead of an IntegerField?
    can_introspect_big_integer_field = True

    # Can the backend introspect an BinaryField, instead of an TextField?
    can_introspect_binary_field = True

    # Can the backend introspect an DecimalField, instead of an FloatField?
    can_introspect_decimal_field = True

    # Can the backend introspect an IPAddressField, instead of an CharField?
    can_introspect_ip_address_field = False

    # Can the backend introspect a PositiveIntegerField, instead of an IntegerField?
    can_introspect_positive_integer_field = False

    # Can the backend introspect a SmallIntegerField, instead of an IntegerField?
    can_introspect_small_integer_field = False

    # Can the backend introspect a TimeField, instead of a DateTimeField?
    can_introspect_time_field = True

    # Can the backend introspect the type of index created e.g. btree, gin, etc.
    can_introspect_index_type = False

    # Support for the DISTINCT ON clause
    can_distinct_on_fields = False

    # Does the backend decide to commit before SAVEPOINT statements
    # when autocommit is disabled? http://bugs.python.org/issue8145#msg109965
    autocommits_when_autocommit_is_off = False

    # Does the backend prevent running SQL queries in broken transactions?
    atomic_transactions = True

    # Can we roll back DDL in a transaction?
    can_rollback_ddl = False

    # Can we issue more than one ALTER COLUMN clause in an ALTER TABLE?
    supports_combined_alters = False

    # Does it support foreign keys?
    supports_foreign_keys = True

    # Does it support CHECK constraints?
    supports_column_check_constraints = True

    # Does the backend support 'pyformat' style ("... %(name)s ...", {'name': value})
    # parameter passing? Note this can be provided by the backend even if not
    # supported by the Python driver
    supports_paramstyle_pyformat = True

    # Does the backend require literal defaults, rather than parameterized ones?
    requires_literal_defaults = False

    # Does the backend require a connection reset after each material schema change?
    connection_persists_old_columns = False

    # What kind of error does the backend throw when accessing closed cursor?
    closed_cursor_error_class = ProgrammingError

    # Does 'a' LIKE 'A' match?
    has_case_insensitive_like = True

    # Does the backend require the sqlparse library for splitting multi-line
    # statements before executing them?
    requires_sqlparse_for_splitting = True

    # Suffix for backends that don't support "SELECT xxx;" queries.
    bare_select_suffix = ''

    # If NULL is implied on columns without needing to be explicitly specified
    implied_column_null = False

    uppercases_column_names = False

    # Does the backend support "select for update" queries with limit (and offset)?
    supports_select_for_update_with_limit = True

    # Does the backend ignore null expressions in GREATEST and LEAST queries unless
    # every expression is null?
    greatest_least_ignores_nulls = False

    # Can the backend clone databases for parallel test execution?
    # Defaults to False to allow third-party backends to opt-in.
    can_clone_databases = False

    # Does the backend consider quoted identifiers with different casing to
    # be equal?
    ignores_quoted_identifier_case = False

    def __init__(self, connection):
        self.connection = connection

    @cached_property
    def supports_transactions(self):
        """Confirm support for transactions."""
        with self.connection.cursor() as cursor:
            cursor.execute('CREATE TABLE ROLLBACK_TEST (X INT)')
            self.connection.set_autocommit(False)
            cursor.execute('INSERT INTO ROLLBACK_TEST (X) VALUES (8)')
            self.connection.rollback()
            self.connection.set_autocommit(True)
            cursor.execute('SELECT COUNT(X) FROM ROLLBACK_TEST')
            count, = cursor.fetchone()
            cursor.execute('DROP TABLE ROLLBACK_TEST')
        return count == 0

    @cached_property
    def supports_stddev(self):
        """Confirm support for STDDEV and related stats functions."""
        try:
            self.connection.ops.check_expression_support(StdDev(1))
            return True
        except NotImplementedError:
            return False

    def introspected_boolean_field_type(self, field=None, created_separately=False):
        """
        What is the type returned when the backend introspects a BooleanField?
        The optional arguments may be used to give further details of the field to be
        introspected; in particular, they are provided by Django's test suite:
        field -- the field definition
        created_separately -- True if the field was added via a SchemaEditor's AddField,
                              False if the field was created with the model

        Note that return value from this function is compared by tests against actual
        introspection results; it should provide expectations, not run an introspection
        itself.
        """
        if self.can_introspect_null and field and field.null:
            return 'NullBooleanField'
        return 'BooleanField'
