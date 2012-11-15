from django.db.utils import DatabaseError

try:
    import thread
except ImportError:
    import dummy_thread as thread
from contextlib import contextmanager

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.backends import util
from django.db.transaction import TransactionManagementError
from django.utils.importlib import import_module
from django.utils.timezone import is_aware


class BaseDatabaseWrapper(object):
    """
    Represents a database connection.
    """
    ops = None
    vendor = 'unknown'

    def __init__(self, settings_dict, alias=DEFAULT_DB_ALIAS,
                 allow_thread_sharing=False):
        # `settings_dict` should be a dictionary containing keys such as
        # NAME, USER, etc. It's called `settings_dict` instead of `settings`
        # to disambiguate it from Django settings modules.
        self.connection = None
        self.queries = []
        self.settings_dict = settings_dict
        self.alias = alias
        self.use_debug_cursor = None

        # Transaction related attributes
        self.transaction_state = []
        self.savepoint_state = 0
        self._dirty = None
        self._thread_ident = thread.get_ident()
        self.allow_thread_sharing = allow_thread_sharing

    def __eq__(self, other):
        return self.alias == other.alias

    def __ne__(self, other):
        return not self == other

    def _commit(self):
        if self.connection is not None:
            return self.connection.commit()

    def _rollback(self):
        if self.connection is not None:
            return self.connection.rollback()

    def _enter_transaction_management(self, managed):
        """
        A hook for backend-specific changes required when entering manual
        transaction handling.
        """
        pass

    def _leave_transaction_management(self, managed):
        """
        A hook for backend-specific changes required when leaving manual
        transaction handling. Will usually be implemented only when
        _enter_transaction_management() is also required.
        """
        pass

    def _savepoint(self, sid):
        if not self.features.uses_savepoints:
            return
        self.cursor().execute(self.ops.savepoint_create_sql(sid))

    def _savepoint_rollback(self, sid):
        if not self.features.uses_savepoints:
            return
        self.cursor().execute(self.ops.savepoint_rollback_sql(sid))

    def _savepoint_commit(self, sid):
        if not self.features.uses_savepoints:
            return
        self.cursor().execute(self.ops.savepoint_commit_sql(sid))

    def enter_transaction_management(self, managed=True):
        """
        Enters transaction management for a running thread. It must be balanced with
        the appropriate leave_transaction_management call, since the actual state is
        managed as a stack.

        The state and dirty flag are carried over from the surrounding block or
        from the settings, if there is no surrounding block (dirty is always false
        when no current block is running).
        """
        if self.transaction_state:
            self.transaction_state.append(self.transaction_state[-1])
        else:
            self.transaction_state.append(settings.TRANSACTIONS_MANAGED)

        if self._dirty is None:
            self._dirty = False
        self._enter_transaction_management(managed)

    def leave_transaction_management(self):
        """
        Leaves transaction management for a running thread. A dirty flag is carried
        over to the surrounding block, as a commit will commit all changes, even
        those from outside. (Commits are on connection level.)
        """
        self._leave_transaction_management(self.is_managed())
        if self.transaction_state:
            del self.transaction_state[-1]
        else:
            raise TransactionManagementError("This code isn't under transaction "
                "management")
        if self._dirty:
            self.rollback()
            raise TransactionManagementError("Transaction managed block ended with "
                "pending COMMIT/ROLLBACK")
        self._dirty = False

    def validate_thread_sharing(self):
        """
        Validates that the connection isn't accessed by another thread than the
        one which originally created it, unless the connection was explicitly
        authorized to be shared between threads (via the `allow_thread_sharing`
        property). Raises an exception if the validation fails.
        """
        if (not self.allow_thread_sharing
            and self._thread_ident != thread.get_ident()):
                raise DatabaseError("DatabaseWrapper objects created in a "
                    "thread can only be used in that same thread. The object "
                    "with alias '%s' was created in thread id %s and this is "
                    "thread id %s."
                    % (self.alias, self._thread_ident, thread.get_ident()))

    def is_dirty(self):
        """
        Returns True if the current transaction requires a commit for changes to
        happen.
        """
        return self._dirty

    def set_dirty(self):
        """
        Sets a dirty flag for the current thread and code streak. This can be used
        to decide in a managed block of code to decide whether there are open
        changes waiting for commit.
        """
        if self._dirty is not None:
            self._dirty = True
        else:
            raise TransactionManagementError("This code isn't under transaction "
                "management")

    def set_clean(self):
        """
        Resets a dirty flag for the current thread and code streak. This can be used
        to decide in a managed block of code to decide whether a commit or rollback
        should happen.
        """
        if self._dirty is not None:
            self._dirty = False
        else:
            raise TransactionManagementError("This code isn't under transaction management")
        self.clean_savepoints()

    def clean_savepoints(self):
        self.savepoint_state = 0

    def is_managed(self):
        """
        Checks whether the transaction manager is in manual or in auto state.
        """
        if self.transaction_state:
            return self.transaction_state[-1]
        return settings.TRANSACTIONS_MANAGED

    def managed(self, flag=True):
        """
        Puts the transaction manager into a manual state: managed transactions have
        to be committed explicitly by the user. If you switch off transaction
        management and there is a pending commit/rollback, the data will be
        commited.
        """
        top = self.transaction_state
        if top:
            top[-1] = flag
            if not flag and self.is_dirty():
                self._commit()
                self.set_clean()
        else:
            raise TransactionManagementError("This code isn't under transaction "
                "management")

    def commit_unless_managed(self):
        """
        Commits changes if the system is not in managed transaction mode.
        """
        self.validate_thread_sharing()
        if not self.is_managed():
            self._commit()
            self.clean_savepoints()
        else:
            self.set_dirty()

    def rollback_unless_managed(self):
        """
        Rolls back changes if the system is not in managed transaction mode.
        """
        self.validate_thread_sharing()
        if not self.is_managed():
            self._rollback()
        else:
            self.set_dirty()

    def commit(self):
        """
        Does the commit itself and resets the dirty flag.
        """
        self.validate_thread_sharing()
        self._commit()
        self.set_clean()

    def rollback(self):
        """
        This function does the rollback itself and resets the dirty flag.
        """
        self.validate_thread_sharing()
        self._rollback()
        self.set_clean()

    def savepoint(self):
        """
        Creates a savepoint (if supported and required by the backend) inside the
        current transaction. Returns an identifier for the savepoint that will be
        used for the subsequent rollback or commit.
        """
        thread_ident = thread.get_ident()

        self.savepoint_state += 1

        tid = str(thread_ident).replace('-', '')
        sid = "s%s_x%d" % (tid, self.savepoint_state)
        self._savepoint(sid)
        return sid

    def savepoint_rollback(self, sid):
        """
        Rolls back the most recent savepoint (if one exists). Does nothing if
        savepoints are not supported.
        """
        self.validate_thread_sharing()
        if self.savepoint_state:
            self._savepoint_rollback(sid)

    def savepoint_commit(self, sid):
        """
        Commits the most recent savepoint (if one exists). Does nothing if
        savepoints are not supported.
        """
        self.validate_thread_sharing()
        if self.savepoint_state:
            self._savepoint_commit(sid)

    @contextmanager
    def constraint_checks_disabled(self):
        disabled = self.disable_constraint_checking()
        try:
            yield
        finally:
            if disabled:
                self.enable_constraint_checking()

    def disable_constraint_checking(self):
        """
        Backends can implement as needed to temporarily disable foreign key constraint
        checking.
        """
        pass

    def enable_constraint_checking(self):
        """
        Backends can implement as needed to re-enable foreign key constraint checking.
        """
        pass

    def check_constraints(self, table_names=None):
        """
        Backends can override this method if they can apply constraint checking (e.g. via "SET CONSTRAINTS
        ALL IMMEDIATE"). Should raise an IntegrityError if any invalid foreign key references are encountered.
        """
        pass

    def close(self):
        self.validate_thread_sharing()
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def cursor(self):
        self.validate_thread_sharing()
        if (self.use_debug_cursor or
            (self.use_debug_cursor is None and settings.DEBUG)):
            cursor = self.make_debug_cursor(self._cursor())
        else:
            cursor = util.CursorWrapper(self._cursor(), self)
        return cursor

    def make_debug_cursor(self, cursor):
        return util.CursorDebugWrapper(cursor, self)

class BaseDatabaseFeatures(object):
    allows_group_by_pk = False
    # True if django.db.backend.utils.typecast_timestamp is used on values
    # returned from dates() calls.
    needs_datetime_string_cast = True
    empty_fetchmany_value = []
    update_can_self_select = True

    # Does the backend distinguish between '' and None?
    interprets_empty_strings_as_nulls = False

    # Does the backend allow inserting duplicate rows when a unique_together
    # constraint exists, but one of the unique_together columns is NULL?
    ignores_nulls_in_unique_constraints = True

    can_use_chunked_reads = True
    can_return_id_from_insert = False
    has_bulk_insert = False
    uses_autocommit = False
    uses_savepoints = False
    can_combine_inserts_with_and_without_auto_increment_pk = False

    # If True, don't use integer foreign keys referring to, e.g., positive
    # integer primary keys.
    related_fields_match_type = False
    allow_sliced_subqueries = True
    has_select_for_update = False
    has_select_for_update_nowait = False

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

    # Does a dirty transaction need to be rolled back
    # before the cursor can be used again?
    requires_rollback_on_dirty_transaction = False

    # Does the backend allow very long model names without error?
    supports_long_model_names = True

    # Is there a REAL datatype in addition to floats/doubles?
    has_real_datatype = False
    supports_subqueries_in_group_by = True
    supports_bitwise_or = True

    # Do time/datetime fields have microsecond precision?
    supports_microsecond_precision = True

    # Does the __regex lookup support backreferencing and grouping?
    supports_regex_backreferencing = True

    # Can date/datetime lookups be performed using a string?
    supports_date_lookup_using_string = True

    # Can datetimes with timezones be used?
    supports_timezones = True

    # When performing a GROUP BY, is an ORDER BY NULL required
    # to remove any ordering?
    requires_explicit_null_ordering_when_grouping = False

    # Is there a 1000 item limit on query parameters?
    supports_1000_query_parameters = True

    # Can an object have a primary key of 0? MySQL says No.
    allows_primary_key_0 = True

    # Do we need to NULL a ForeignKey out, or can the constraint check be
    # deferred
    can_defer_constraint_checks = False

    # date_interval_sql can properly handle mixed Date/DateTime fields and timedeltas
    supports_mixed_date_datetime_comparisons = True

    # Does the backend support tablespaces? Default to False because it isn't
    # in the SQL standard.
    supports_tablespaces = False

    # Features that need to be confirmed at runtime
    # Cache whether the confirmation has been performed.
    _confirmed = False
    supports_transactions = None
    supports_stddev = None
    can_introspect_foreign_keys = None

    # Support for the DISTINCT ON clause
    can_distinct_on_fields = False

    def __init__(self, connection):
        self.connection = connection

    def confirm(self):
        "Perform manual checks of any database features that might vary between installs"
        self._confirmed = True
        self.supports_transactions = self._supports_transactions()
        self.supports_stddev = self._supports_stddev()
        self.can_introspect_foreign_keys = self._can_introspect_foreign_keys()

    def _supports_transactions(self):
        "Confirm support for transactions"
        cursor = self.connection.cursor()
        cursor.execute('CREATE TABLE ROLLBACK_TEST (X INT)')
        self.connection._commit()
        cursor.execute('INSERT INTO ROLLBACK_TEST (X) VALUES (8)')
        self.connection._rollback()
        cursor.execute('SELECT COUNT(X) FROM ROLLBACK_TEST')
        count, = cursor.fetchone()
        cursor.execute('DROP TABLE ROLLBACK_TEST')
        self.connection._commit()
        return count == 0

    def _supports_stddev(self):
        "Confirm support for STDDEV and related stats functions"
        class StdDevPop(object):
            sql_function = 'STDDEV_POP'

        try:
            self.connection.ops.check_aggregate_support(StdDevPop())
        except NotImplementedError:
            self.supports_stddev = False

    def _can_introspect_foreign_keys(self):
        "Confirm support for introspected foreign keys"
        # Every database can do this reliably, except MySQL,
        # which can't do it for MyISAM tables
        return True


class BaseDatabaseOperations(object):
    """
    This class encapsulates all backend-specific differences, such as the way
    a backend performs ordering or calculates the ID of a recently-inserted
    row.
    """
    compiler_module = "django.db.models.sql.compiler"

    def __init__(self, connection):
        self.connection = connection
        self._cache = None

    def autoinc_sql(self, table, column):
        """
        Returns any SQL needed to support auto-incrementing primary keys, or
        None if no SQL is necessary.

        This SQL is executed when a table is created.
        """
        return None

    def bulk_batch_size(self, fields, objs):
        """
        Returns the maximum allowed batch size for the backend. The fields
        are the fields going to be inserted in the batch, the objs contains
        all the objects to be inserted.
        """
        return len(objs)

    def date_extract_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month' or 'day', returns the SQL that
        extracts a value from the given date field field_name.
        """
        raise NotImplementedError()

    def date_interval_sql(self, sql, connector, timedelta):
        """
        Implements the date interval functionality for expressions
        """
        raise NotImplementedError()

    def date_trunc_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month' or 'day', returns the SQL that
        truncates the given date field field_name to a DATE object with only
        the given specificity.
        """
        raise NotImplementedError()

    def datetime_cast_sql(self):
        """
        Returns the SQL necessary to cast a datetime value so that it will be
        retrieved as a Python datetime object instead of a string.

        This SQL should include a '%s' in place of the field's name.
        """
        return "%s"

    def deferrable_sql(self):
        """
        Returns the SQL necessary to make a constraint "initially deferred"
        during a CREATE TABLE statement.
        """
        return ''

    def distinct_sql(self, fields):
        """
        Returns an SQL DISTINCT clause which removes duplicate rows from the
        result set. If any fields are given, only the given fields are being
        checked for duplicates.
        """
        if fields:
            raise NotImplementedError('DISTINCT ON fields is not supported by this database backend')
        else:
            return 'DISTINCT'

    def drop_foreignkey_sql(self):
        """
        Returns the SQL command that drops a foreign key.
        """
        return "DROP CONSTRAINT"

    def drop_sequence_sql(self, table):
        """
        Returns any SQL necessary to drop the sequence for the given table.
        Returns None if no SQL is necessary.
        """
        return None

    def fetch_returned_insert_id(self, cursor):
        """
        Given a cursor object that has just performed an INSERT...RETURNING
        statement into a table that has an auto-incrementing ID, returns the
        newly created ID.
        """
        return cursor.fetchone()[0]

    def field_cast_sql(self, db_type):
        """
        Given a column type (e.g. 'BLOB', 'VARCHAR'), returns the SQL necessary
        to cast it before using it in a WHERE statement. Note that the
        resulting string should contain a '%s' placeholder for the column being
        searched against.
        """
        return '%s'

    def force_no_ordering(self):
        """
        Returns a list used in the "ORDER BY" clause to force no ordering at
        all. Returning an empty list means that nothing will be included in the
        ordering.
        """
        return []

    def for_update_sql(self, nowait=False):
        """
        Returns the FOR UPDATE SQL clause to lock rows for an update operation.
        """
        if nowait:
            return 'FOR UPDATE NOWAIT'
        else:
            return 'FOR UPDATE'

    def fulltext_search_sql(self, field_name):
        """
        Returns the SQL WHERE clause to use in order to perform a full-text
        search of the given field_name. Note that the resulting string should
        contain a '%s' placeholder for the value being searched against.
        """
        raise NotImplementedError('Full-text search is not implemented for this database backend')

    def last_executed_query(self, cursor, sql, params):
        """
        Returns a string of the query last executed by the given cursor, with
        placeholders replaced with actual values.

        `sql` is the raw query containing placeholders, and `params` is the
        sequence of parameters. These are used by default, but this method
        exists for database backends to provide a better implementation
        according to their own quoting schemes.
        """
        from django.utils.encoding import smart_unicode, force_unicode

        # Convert params to contain Unicode values.
        to_unicode = lambda s: force_unicode(s, strings_only=True, errors='replace')
        if isinstance(params, (list, tuple)):
            u_params = tuple([to_unicode(val) for val in params])
        else:
            u_params = dict([(to_unicode(k), to_unicode(v)) for k, v in params.items()])

        return smart_unicode(sql) % u_params

    def last_insert_id(self, cursor, table_name, pk_name):
        """
        Given a cursor object that has just performed an INSERT statement into
        a table that has an auto-incrementing ID, returns the newly created ID.

        This method also receives the table name and the name of the primary-key
        column.
        """
        return cursor.lastrowid

    def lookup_cast(self, lookup_type):
        """
        Returns the string to use in a query when performing lookups
        ("contains", "like", etc). The resulting string should contain a '%s'
        placeholder for the column being searched against.
        """
        return "%s"

    def max_in_list_size(self):
        """
        Returns the maximum number of items that can be passed in a single 'IN'
        list condition, or None if the backend does not impose a limit.
        """
        return None

    def max_name_length(self):
        """
        Returns the maximum length of table and column names, or None if there
        is no limit.
        """
        return None

    def no_limit_value(self):
        """
        Returns the value to use for the LIMIT when we are wanting "LIMIT
        infinity". Returns None if the limit clause can be omitted in this case.
        """
        raise NotImplementedError

    def pk_default_value(self):
        """
        Returns the value to use during an INSERT statement to specify that
        the field should use its default value.
        """
        return 'DEFAULT'

    def process_clob(self, value):
        """
        Returns the value of a CLOB column, for backends that return a locator
        object that requires additional processing.
        """
        return value

    def return_insert_id(self):
        """
        For backends that support returning the last insert ID as part
        of an insert query, this method returns the SQL and params to
        append to the INSERT query. The returned fragment should
        contain a format string to hold the appropriate column.
        """
        pass

    def compiler(self, compiler_name):
        """
        Returns the SQLCompiler class corresponding to the given name,
        in the namespace corresponding to the `compiler_module` attribute
        on this backend.
        """
        if self._cache is None:
            self._cache = import_module(self.compiler_module)
        return getattr(self._cache, compiler_name)

    def quote_name(self, name):
        """
        Returns a quoted version of the given table, index or column name. Does
        not quote the given name if it's already been quoted.
        """
        raise NotImplementedError()

    def random_function_sql(self):
        """
        Returns a SQL expression that returns a random value.
        """
        return 'RANDOM()'

    def regex_lookup(self, lookup_type):
        """
        Returns the string to use in a query when performing regular expression
        lookups (using "regex" or "iregex"). The resulting string should
        contain a '%s' placeholder for the column being searched against.

        If the feature is not supported (or part of it is not supported), a
        NotImplementedError exception can be raised.
        """
        raise NotImplementedError

    def savepoint_create_sql(self, sid):
        """
        Returns the SQL for starting a new savepoint. Only required if the
        "uses_savepoints" feature is True. The "sid" parameter is a string
        for the savepoint id.
        """
        raise NotImplementedError

    def savepoint_commit_sql(self, sid):
        """
        Returns the SQL for committing the given savepoint.
        """
        raise NotImplementedError

    def savepoint_rollback_sql(self, sid):
        """
        Returns the SQL for rolling back the given savepoint.
        """
        raise NotImplementedError

    def set_time_zone_sql(self):
        """
        Returns the SQL that will set the connection's time zone.

        Returns '' if the backend doesn't support time zones.
        """
        return ''

    def sql_flush(self, style, tables, sequences):
        """
        Returns a list of SQL statements required to remove all data from
        the given database tables (without actually removing the tables
        themselves).

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        """
        raise NotImplementedError()

    def sequence_reset_sql(self, style, model_list):
        """
        Returns a list of the SQL statements required to reset sequences for
        the given models.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        """
        return [] # No sequence reset required by default.

    def start_transaction_sql(self):
        """
        Returns the SQL statement required to start a transaction.
        """
        return "BEGIN;"

    def end_transaction_sql(self, success=True):
        if not success:
            return "ROLLBACK;"
        return "COMMIT;"

    def tablespace_sql(self, tablespace, inline=False):
        """
        Returns the SQL that will be used in a query to define the tablespace.

        Returns '' if the backend doesn't support tablespaces.

        If inline is True, the SQL is appended to a row; otherwise it's appended
        to the entire CREATE TABLE or CREATE INDEX statement.
        """
        return ''

    def prep_for_like_query(self, x):
        """Prepares a value for use in a LIKE query."""
        from django.utils.encoding import smart_unicode
        return smart_unicode(x).replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")

    # Same as prep_for_like_query(), but called for "iexact" matches, which
    # need not necessarily be implemented using "LIKE" in the backend.
    prep_for_iexact_query = prep_for_like_query

    def value_to_db_date(self, value):
        """
        Transform a date value to an object compatible with what is expected
        by the backend driver for date columns.
        """
        if value is None:
            return None
        return unicode(value)

    def value_to_db_datetime(self, value):
        """
        Transform a datetime value to an object compatible with what is expected
        by the backend driver for datetime columns.
        """
        if value is None:
            return None
        return unicode(value)

    def value_to_db_time(self, value):
        """
        Transform a time value to an object compatible with what is expected
        by the backend driver for time columns.
        """
        if value is None:
            return None
        if is_aware(value):
            raise ValueError("Django does not support timezone-aware times.")
        return unicode(value)

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        """
        Transform a decimal.Decimal value to an object compatible with what is
        expected by the backend driver for decimal (numeric) columns.
        """
        if value is None:
            return None
        return util.format_number(value, max_digits, decimal_places)

    def year_lookup_bounds(self, value):
        """
        Returns a two-elements list with the lower and upper bound to be used
        with a BETWEEN operator to query a field value using a year lookup

        `value` is an int, containing the looked-up year.
        """
        first = '%s-01-01 00:00:00'
        second = '%s-12-31 23:59:59.999999'
        return [first % value, second % value]

    def year_lookup_bounds_for_date_field(self, value):
        """
        Returns a two-elements list with the lower and upper bound to be used
        with a BETWEEN operator to query a DateField value using a year lookup

        `value` is an int, containing the looked-up year.

        By default, it just calls `self.year_lookup_bounds`. Some backends need
        this hook because on their DB date fields can't be compared to values
        which include a time part.
        """
        return self.year_lookup_bounds(value)

    def convert_values(self, value, field):
        """Coerce the value returned by the database backend into a consistent type that
        is compatible with the field type.
        """
        internal_type = field.get_internal_type()
        if internal_type == 'DecimalField':
            return value
        elif internal_type and internal_type.endswith('IntegerField') or internal_type == 'AutoField':
            return int(value)
        elif internal_type in ('DateField', 'DateTimeField', 'TimeField'):
            return value
        # No field, or the field isn't known to be a decimal or integer
        # Default to a float
        return float(value)

    def check_aggregate_support(self, aggregate_func):
        """Check that the backend supports the provided aggregate

        This is used on specific backends to rule out known aggregates
        that are known to have faulty implementations. If the named
        aggregate function has a known problem, the backend should
        raise NotImplementedError.
        """
        pass

    def combine_expression(self, connector, sub_expressions):
        """Combine a list of subexpressions into a single expression, using
        the provided connecting operator. This is required because operators
        can vary between backends (e.g., Oracle with %% and &) and between
        subexpression types (e.g., date expressions)
        """
        conn = ' %s ' % connector
        return conn.join(sub_expressions)

    def modify_insert_params(self, placeholders, params):
        """Allow modification of insert parameters. Needed for Oracle Spatial
        backend due to #10888.
        """
        return params

class BaseDatabaseIntrospection(object):
    """
    This class encapsulates all backend-specific introspection utilities
    """
    data_types_reverse = {}

    def __init__(self, connection):
        self.connection = connection

    def get_field_type(self, data_type, description):
        """Hook for a database backend to use the cursor description to
        match a Django field type to a database column.

        For Oracle, the column data_type on its own is insufficient to
        distinguish between a FloatField and IntegerField, for example."""
        return self.data_types_reverse[data_type]

    def table_name_converter(self, name):
        """Apply a conversion to the name for the purposes of comparison.

        The default table name converter is for case sensitive comparison.
        """
        return name

    def table_names(self):
        "Returns a list of names of all tables that exist in the database."
        cursor = self.connection.cursor()
        return self.get_table_list(cursor)

    def django_table_names(self, only_existing=False):
        """
        Returns a list of all table names that have associated Django models and
        are in INSTALLED_APPS.

        If only_existing is True, the resulting list will only include the tables
        that actually exist in the database.
        """
        from django.db import models, router
        tables = set()
        for app in models.get_apps():
            for model in models.get_models(app):
                if not model._meta.managed:
                    continue
                if not router.allow_syncdb(self.connection.alias, model):
                    continue
                tables.add(model._meta.db_table)
                tables.update([f.m2m_db_table() for f in model._meta.local_many_to_many])
        tables = list(tables)
        if only_existing:
            existing_tables = self.table_names()
            tables = [
                t
                for t in tables
                if self.table_name_converter(t) in existing_tables
            ]
        return tables

    def installed_models(self, tables):
        "Returns a set of all models represented by the provided list of table names."
        from django.db import models, router
        all_models = []
        for app in models.get_apps():
            for model in models.get_models(app):
                if router.allow_syncdb(self.connection.alias, model):
                    all_models.append(model)
        tables = map(self.table_name_converter, tables)
        return set([
            m for m in all_models
            if self.table_name_converter(m._meta.db_table) in tables
        ])

    def sequence_list(self):
        "Returns a list of information about all DB sequences for all models in all apps."
        from django.db import models, router

        apps = models.get_apps()
        sequence_list = []

        for app in apps:
            for model in models.get_models(app):
                if not model._meta.managed:
                    continue
                if not router.allow_syncdb(self.connection.alias, model):
                    continue
                for f in model._meta.local_fields:
                    if isinstance(f, models.AutoField):
                        sequence_list.append({'table': model._meta.db_table, 'column': f.column})
                        break # Only one AutoField is allowed per model, so don't bother continuing.

                for f in model._meta.local_many_to_many:
                    # If this is an m2m using an intermediate table,
                    # we don't need to reset the sequence.
                    if f.rel.through is None:
                        sequence_list.append({'table': f.m2m_db_table(), 'column': None})

        return sequence_list

    def get_key_columns(self, cursor, table_name):
        """
        Backends can override this to return a list of (column_name, referenced_table_name,
        referenced_column_name) for all key columns in given table.
        """
        raise NotImplementedError

    def get_primary_key_column(self, cursor, table_name):
        """
        Backends can override this to return the column name of the primary key for the given table.
        """
        raise NotImplementedError

class BaseDatabaseClient(object):
    """
    This class encapsulates all backend-specific methods for opening a
    client shell.
    """
    # This should be a string representing the name of the executable
    # (e.g., "psql"). Subclasses must override this.
    executable_name = None

    def __init__(self, connection):
        # connection is an instance of BaseDatabaseWrapper.
        self.connection = connection

    def runshell(self):
        raise NotImplementedError()

class BaseDatabaseValidation(object):
    """
    This class encapsualtes all backend-specific model validation.
    """
    def __init__(self, connection):
        self.connection = connection

    def validate_field(self, errors, opts, f):
        "By default, there is no backend-specific validation"
        pass
