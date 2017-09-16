from django.db import utils
from django.db.backends.base.features import BaseDatabaseFeatures
from django.utils.functional import cached_property

from .base import Database


class DatabaseFeatures(BaseDatabaseFeatures):
    # SQLite cannot handle us only partially reading from a cursor's result set
    # and then writing the same rows to the database in another cursor. This
    # setting ensures we always read result sets fully into memory all in one
    # go.
    can_use_chunked_reads = False
    test_db_allows_multiple_connections = False
    supports_unspecified_pk = True
    supports_timezones = False
    max_query_params = 999
    supports_mixed_date_datetime_comparisons = False
    supports_column_check_constraints = False
    autocommits_when_autocommit_is_off = True
    can_introspect_decimal_field = False
    can_introspect_positive_integer_field = True
    can_introspect_small_integer_field = True
    supports_transactions = True
    atomic_transactions = False
    can_rollback_ddl = True
    supports_paramstyle_pyformat = False
    supports_sequence_reset = False
    can_clone_databases = True
    supports_temporal_subtraction = True
    ignores_table_name_case = True
    supports_cast_with_precision = False
    uses_savepoints = Database.sqlite_version_info >= (3, 6, 8)
    supports_index_column_ordering = Database.sqlite_version_info >= (3, 3, 0)
    can_release_savepoints = uses_savepoints
    can_share_in_memory_db = (
        Database.__name__ == 'sqlite3.dbapi2' and
        Database.sqlite_version_info >= (3, 7, 13)
    )

    @cached_property
    def supports_stddev(self):
        """
        Confirm support for STDDEV and related stats functions.

        SQLite supports STDDEV as an extension package; so
        connection.ops.check_expression_support() can't unilaterally
        rule out support for STDDEV. Manually check whether the call works.
        """
        with self.connection.cursor() as cursor:
            cursor.execute('CREATE TABLE STDDEV_TEST (X INT)')
            try:
                cursor.execute('SELECT STDDEV(*) FROM STDDEV_TEST')
                has_support = True
            except utils.DatabaseError:
                has_support = False
            cursor.execute('DROP TABLE STDDEV_TEST')
        return has_support
