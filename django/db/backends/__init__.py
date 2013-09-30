import datetime
import time

from django.db.utils import DatabaseError

try:
    from django.utils.six.moves import _thread as thread
except ImportError:
    from django.utils.six.moves import _dummy_thread as thread
from collections import namedtuple
from contextlib import contextmanager

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS
from django.db.backends.signals import connection_created
from django.db.backends import util
from django.db.transaction import TransactionManagementError
from django.db.utils import DatabaseErrorWrapper
from django.utils.functional import cached_property
from django.utils.importlib import import_module
from django.utils import six
from django.utils import timezone


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

        # Savepoint management related attributes
        self.savepoint_state = 0

        # Transaction management related attributes
        self.autocommit = False
        self.transaction_state = []
        # Tracks if the connection is believed to be in transaction. This is
        # set somewhat aggressively, as the DBAPI doesn't make it easy to
        # deduce if the connection is in transaction or not.
        self._dirty = False
        # Tracks if the connection is in a transaction managed by 'atomic'.
        self.in_atomic_block = False
        # List of savepoints created by 'atomic'
        self.savepoint_ids = []
        # Tracks if the outermost 'atomic' block should commit on exit,
        # ie. if autocommit was active on entry.
        self.commit_on_exit = True
        # Tracks if the transaction should be rolled back to the next
        # available savepoint because of an exception in an inner block.
        self.needs_rollback = False

        # Connection termination related attributes
        self.close_at = None
        self.errors_occurred = False

        # Thread-safety related attributes
        self.allow_thread_sharing = allow_thread_sharing
        self._thread_ident = thread.get_ident()

    def __eq__(self, other):
        return self.alias == other.alias

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.alias)

    ##### Backend-specific methods for creating connections and cursors #####

    def get_connection_params(self):
        """Returns a dict of parameters suitable for get_new_connection."""
        raise NotImplementedError

    def get_new_connection(self, conn_params):
        """Opens a connection to the database."""
        raise NotImplementedError

    def init_connection_state(self):
        """Initializes the database connection settings."""
        raise NotImplementedError

    def create_cursor(self):
        """Creates a cursor. Assumes that a connection is established."""
        raise NotImplementedError

    ##### Backend-specific methods for creating connections #####

    def connect(self):
        """Connects to the database. Assumes that the connection is closed."""
        # In case the previous connection was closed while in an atomic block
        self.in_atomic_block = False
        self.savepoint_ids = []
        # Reset parameters defining when to close the connection
        max_age = self.settings_dict['CONN_MAX_AGE']
        self.close_at = None if max_age is None else time.time() + max_age
        self.errors_occurred = False
        # Establish the connection
        conn_params = self.get_connection_params()
        self.connection = self.get_new_connection(conn_params)
        self.init_connection_state()
        if self.settings_dict['AUTOCOMMIT']:
            self.set_autocommit(True)
        connection_created.send(sender=self.__class__, connection=self)

    def ensure_connection(self):
        """
        Guarantees that a connection to the database is established.
        """
        if self.connection is None:
            with self.wrap_database_errors:
                self.connect()

    ##### Backend-specific wrappers for PEP-249 connection methods #####

    def _cursor(self):
        self.ensure_connection()
        with self.wrap_database_errors:
            return self.create_cursor()

    def _commit(self):
        if self.connection is not None:
            with self.wrap_database_errors:
                return self.connection.commit()

    def _rollback(self):
        if self.connection is not None:
            with self.wrap_database_errors:
                return self.connection.rollback()

    def _close(self):
        if self.connection is not None:
            with self.wrap_database_errors:
                return self.connection.close()

    ##### Generic wrappers for PEP-249 connection methods #####

    def cursor(self):
        """
        Creates a cursor, opening a connection if necessary.
        """
        self.validate_thread_sharing()
        if (self.use_debug_cursor or
            (self.use_debug_cursor is None and settings.DEBUG)):
            cursor = self.make_debug_cursor(self._cursor())
        else:
            cursor = util.CursorWrapper(self._cursor(), self)
        return cursor

    def commit(self):
        """
        Commits a transaction and resets the dirty flag.
        """
        self.validate_thread_sharing()
        self.validate_no_atomic_block()
        self._commit()
        self.set_clean()

    def rollback(self):
        """
        Rolls back a transaction and resets the dirty flag.
        """
        self.validate_thread_sharing()
        self.validate_no_atomic_block()
        self._rollback()
        self.set_clean()

    def close(self):
        """
        Closes the connection to the database.
        """
        self.validate_thread_sharing()
        # Don't call validate_no_atomic_block() to avoid making it difficult
        # to get rid of a connection in an invalid state. The next connect()
        # will reset the transaction state anyway.
        try:
            self._close()
        finally:
            self.connection = None
        self.set_clean()

    ##### Backend-specific savepoint management methods #####

    def _savepoint(self, sid):
        self.cursor().execute(self.ops.savepoint_create_sql(sid))

    def _savepoint_rollback(self, sid):
        self.cursor().execute(self.ops.savepoint_rollback_sql(sid))

    def _savepoint_commit(self, sid):
        self.cursor().execute(self.ops.savepoint_commit_sql(sid))

    def _savepoint_allowed(self):
        # Savepoints cannot be created outside a transaction
        return self.features.uses_savepoints and not self.get_autocommit()

    ##### Generic savepoint management methods #####

    def savepoint(self):
        """
        Creates a savepoint inside the current transaction. Returns an
        identifier for the savepoint that will be used for the subsequent
        rollback or commit. Does nothing if savepoints are not supported.
        """
        if not self._savepoint_allowed():
            return

        thread_ident = thread.get_ident()
        tid = str(thread_ident).replace('-', '')

        self.savepoint_state += 1
        sid = "s%s_x%d" % (tid, self.savepoint_state)

        self.validate_thread_sharing()
        self._savepoint(sid)

        return sid

    def savepoint_rollback(self, sid):
        """
        Rolls back to a savepoint. Does nothing if savepoints are not supported.
        """
        if not self._savepoint_allowed():
            return

        self.validate_thread_sharing()
        self._savepoint_rollback(sid)

    def savepoint_commit(self, sid):
        """
        Releases a savepoint. Does nothing if savepoints are not supported.
        """
        if not self._savepoint_allowed():
            return

        self.validate_thread_sharing()
        self._savepoint_commit(sid)

    def clean_savepoints(self):
        """
        Resets the counter used to generate unique savepoint ids in this thread.
        """
        self.savepoint_state = 0

    ##### Backend-specific transaction management methods #####

    def _set_autocommit(self, autocommit):
        """
        Backend-specific implementation to enable or disable autocommit.
        """
        raise NotImplementedError

    ##### Generic transaction management methods #####

    def enter_transaction_management(self, managed=True, forced=False):
        """
        Enters transaction management for a running thread. It must be balanced with
        the appropriate leave_transaction_management call, since the actual state is
        managed as a stack.

        The state and dirty flag are carried over from the surrounding block or
        from the settings, if there is no surrounding block (dirty is always false
        when no current block is running).

        If you switch off transaction management and there is a pending
        commit/rollback, the data will be commited, unless "forced" is True.
        """
        self.validate_no_atomic_block()

        self.transaction_state.append(managed)

        if not managed and self.is_dirty() and not forced:
            self.commit()
            self.set_clean()

        if managed == self.get_autocommit():
            self.set_autocommit(not managed)

    def leave_transaction_management(self):
        """
        Leaves transaction management for a running thread. A dirty flag is carried
        over to the surrounding block, as a commit will commit all changes, even
        those from outside. (Commits are on connection level.)
        """
        self.validate_no_atomic_block()

        if self.transaction_state:
            del self.transaction_state[-1]
        else:
            raise TransactionManagementError(
                "This code isn't under transaction management")

        if self.transaction_state:
            managed = self.transaction_state[-1]
        else:
            managed = not self.settings_dict['AUTOCOMMIT']

        if self._dirty:
            self.rollback()
            if managed == self.get_autocommit():
                self.set_autocommit(not managed)
            raise TransactionManagementError(
                "Transaction managed block ended with pending COMMIT/ROLLBACK")

        if managed == self.get_autocommit():
            self.set_autocommit(not managed)

    def get_autocommit(self):
        """
        Check the autocommit state.
        """
        self.ensure_connection()
        return self.autocommit

    def set_autocommit(self, autocommit):
        """
        Enable or disable autocommit.
        """
        self.validate_no_atomic_block()
        self.ensure_connection()
        self._set_autocommit(autocommit)
        self.autocommit = autocommit

    def get_rollback(self):
        """
        Get the "needs rollback" flag -- for *advanced use* only.
        """
        if not self.in_atomic_block:
            raise TransactionManagementError(
                "The rollback flag doesn't work outside of an 'atomic' block.")
        return self.needs_rollback

    def set_rollback(self, rollback):
        """
        Set or unset the "needs rollback" flag -- for *advanced use* only.
        """
        if not self.in_atomic_block:
            raise TransactionManagementError(
                "The rollback flag doesn't work outside of an 'atomic' block.")
        self.needs_rollback = rollback

    def validate_no_atomic_block(self):
        """
        Raise an error if an atomic block is active.
        """
        if self.in_atomic_block:
            raise TransactionManagementError(
                "This is forbidden when an 'atomic' block is active.")

    def validate_no_broken_transaction(self):
        if self.needs_rollback:
            raise TransactionManagementError(
                "An error occurred in the current transaction. You can't "
                "execute queries until the end of the 'atomic' block.")

    def abort(self):
        """
        Roll back any ongoing transaction and clean the transaction state
        stack.
        """
        if self._dirty:
            self.rollback()
        while self.transaction_state:
            self.leave_transaction_management()

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
        if not self.get_autocommit():
            self._dirty = True

    def set_clean(self):
        """
        Resets a dirty flag for the current thread and code streak. This can be used
        to decide in a managed block of code to decide whether a commit or rollback
        should happen.
        """
        self._dirty = False
        self.clean_savepoints()

    ##### Foreign key constraints checks handling #####

    @contextmanager
    def constraint_checks_disabled(self):
        """
        Context manager that disables foreign key constraint checking.
        """
        disabled = self.disable_constraint_checking()
        try:
            yield
        finally:
            if disabled:
                self.enable_constraint_checking()

    def disable_constraint_checking(self):
        """
        Backends can implement as needed to temporarily disable foreign key
        constraint checking. Should return True if the constraints were
        disabled and will need to be reenabled.
        """
        return False

    def enable_constraint_checking(self):
        """
        Backends can implement as needed to re-enable foreign key constraint
        checking.
        """
        pass

    def check_constraints(self, table_names=None):
        """
        Backends can override this method if they can apply constraint
        checking (e.g. via "SET CONSTRAINTS ALL IMMEDIATE"). Should raise an
        IntegrityError if any invalid foreign key references are encountered.
        """
        pass

    ##### Connection termination handling #####

    def is_usable(self):
        """
        Tests if the database connection is usable.
        This function may assume that self.connection is not None.
        """
        raise NotImplementedError

    def close_if_unusable_or_obsolete(self):
        """
        Closes the current connection if unrecoverable errors have occurred,
        or if it outlived its maximum age.
        """
        if self.connection is not None:
            # If the application didn't restore the original autocommit setting,
            # don't take chances, drop the connection.
            if self.get_autocommit() != self.settings_dict['AUTOCOMMIT']:
                self.close()
                return

            if self.errors_occurred:
                if self.is_usable():
                    self.errors_occurred = False
                else:
                    self.close()
                    return

            if self.close_at is not None and time.time() >= self.close_at:
                self.close()
                return

    ##### Thread safety handling #####

    def validate_thread_sharing(self):
        """
        Validates that the connection isn't accessed by another thread than the
        one which originally created it, unless the connection was explicitly
        authorized to be shared between threads (via the `allow_thread_sharing`
        property). Raises an exception if the validation fails.
        """
        if not (self.allow_thread_sharing
                or self._thread_ident == thread.get_ident()):
            raise DatabaseError("DatabaseWrapper objects created in a "
                "thread can only be used in that same thread. The object "
                "with alias '%s' was created in thread id %s and this is "
                "thread id %s."
                % (self.alias, self._thread_ident, thread.get_ident()))

    ##### Miscellaneous #####

    @cached_property
    def wrap_database_errors(self):
        """
        Context manager and decorator that re-throws backend-specific database
        exceptions using Django's common wrappers.
        """
        return DatabaseErrorWrapper(self)

    def make_debug_cursor(self, cursor):
        """
        Creates a cursor that logs all queries in self.queries.
        """
        return util.CursorDebugWrapper(cursor, self)

    @contextmanager
    def temporary_connection(self):
        """
        Context manager that ensures that a connection is established, and
        if it opened one, closes it to avoid leaving a dangling connection.
        This is useful for operations outside of the request-response cycle.

        Provides a cursor: with self.temporary_connection() as cursor: ...
        """
        must_close = self.connection is None
        cursor = self.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
            if must_close:
                self.close()

    def _start_transaction_under_autocommit(self):
        """
        Only required when autocommits_when_autocommit_is_off = True.
        """
        raise NotImplementedError


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

    # Does the database have a copy of the zoneinfo database?
    has_zoneinfo_database = True

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

    # Does the backend reset sequences between tests?
    supports_sequence_reset = True

    # Confirm support for introspected foreign keys
    # Every database can do this reliably, except MySQL,
    # which can't do it for MyISAM tables
    can_introspect_foreign_keys = True

    # Support for the DISTINCT ON clause
    can_distinct_on_fields = False

    # Does the backend decide to commit before SAVEPOINT statements
    # when autocommit is disabled? http://bugs.python.org/issue8145#msg109965
    autocommits_when_autocommit_is_off = False

    # Does the backend prevent running SQL queries in broken transactions?
    atomic_transactions = True

    # Does the backend support 'pyformat' style ("... %(name)s ...", {'name': value})
    # parameter passing? Note this can be provided by the backend even if not
    # supported by the Python driver
    supports_paramstyle_pyformat = True

    def __init__(self, connection):
        self.connection = connection

    @cached_property
    def supports_transactions(self):
        "Confirm support for transactions"
        try:
            # Make sure to run inside a managed transaction block,
            # otherwise autocommit will cause the confimation to
            # fail.
            self.connection.enter_transaction_management()
            cursor = self.connection.cursor()
            cursor.execute('CREATE TABLE ROLLBACK_TEST (X INT)')
            self.connection.commit()
            cursor.execute('INSERT INTO ROLLBACK_TEST (X) VALUES (8)')
            self.connection.rollback()
            cursor.execute('SELECT COUNT(X) FROM ROLLBACK_TEST')
            count, = cursor.fetchone()
            cursor.execute('DROP TABLE ROLLBACK_TEST')
            self.connection.commit()
        finally:
            self.connection.leave_transaction_management()
        return count == 0

    @cached_property
    def supports_stddev(self):
        "Confirm support for STDDEV and related stats functions"
        class StdDevPop(object):
            sql_function = 'STDDEV_POP'

        try:
            self.connection.ops.check_aggregate_support(StdDevPop())
            return True
        except NotImplementedError:
            return False


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

    def cache_key_culling_sql(self):
        """
        Returns an SQL query that retrieves the first cache key greater than the
        n smallest.

        This is used by the 'db' cache backend to determine where to start
        culling.
        """
        return "SELECT cache_key FROM %s ORDER BY cache_key LIMIT 1 OFFSET %%s"

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
        truncates the given date field field_name to a date object with only
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

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute' or
        'second', returns the SQL that extracts a value from the given
        datetime field field_name, and a tuple of parameters.
        """
        raise NotImplementedError()

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute' or
        'second', returns the SQL that truncates the given datetime field
        field_name to a datetime object with only the given specificity, and
        a tuple of parameters.
        """
        raise NotImplementedError()

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

    def field_cast_sql(self, db_type, internal_type):
        """
        Given a column type (e.g. 'BLOB', 'VARCHAR'), and an internal type
        (e.g. 'GenericIPAddressField'), returns the SQL necessary to cast it
        before using it in a WHERE statement. Note that the resulting string
        should contain a '%s' placeholder for the column being searched against.
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
        from django.utils.encoding import force_text

        # Convert params to contain Unicode values.
        to_unicode = lambda s: force_text(s, strings_only=True, errors='replace')
        if isinstance(params, (list, tuple)):
            u_params = tuple(to_unicode(val) for val in params)
        elif params is None:
            u_params = ()
        else:
            u_params = dict((to_unicode(k), to_unicode(v)) for k, v in params.items())

        return six.text_type("QUERY = %r - PARAMS = %r") % (sql, u_params)

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
        Returns an SQL expression that returns a random value.
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
        return "SAVEPOINT %s" % self.quote_name(sid)

    def savepoint_commit_sql(self, sid):
        """
        Returns the SQL for committing the given savepoint.
        """
        return "RELEASE SAVEPOINT %s" % self.quote_name(sid)

    def savepoint_rollback_sql(self, sid):
        """
        Returns the SQL for rolling back the given savepoint.
        """
        return "ROLLBACK TO SAVEPOINT %s" % self.quote_name(sid)

    def set_time_zone_sql(self):
        """
        Returns the SQL that will set the connection's time zone.

        Returns '' if the backend doesn't support time zones.
        """
        return ''

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        """
        Returns a list of SQL statements required to remove all data from
        the given database tables (without actually removing the tables
        themselves).

        The returned value also includes SQL statements required to reset DB
        sequences passed in :param sequences:.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.

        The `allow_cascade` argument determines whether truncation may cascade
        to tables with foreign keys pointing the tables being truncated.
        PostgreSQL requires a cascade even if these tables are empty.
        """
        raise NotImplementedError()

    def sequence_reset_by_name_sql(self, style, sequences):
        """
        Returns a list of the SQL statements required to reset sequences
        passed in :param sequences:.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        """
        return []

    def sequence_reset_sql(self, style, model_list):
        """
        Returns a list of the SQL statements required to reset sequences for
        the given models.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        """
        return []  # No sequence reset required by default.

    def start_transaction_sql(self):
        """
        Returns the SQL statement required to start a transaction.
        """
        return "BEGIN;"

    def end_transaction_sql(self, success=True):
        """
        Returns the SQL statement required to end a transaction.
        """
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
        from django.utils.encoding import force_text
        return force_text(x).replace("\\", "\\\\").replace("%", "\%").replace("_", "\_")

    # Same as prep_for_like_query(), but called for "iexact" matches, which
    # need not necessarily be implemented using "LIKE" in the backend.
    prep_for_iexact_query = prep_for_like_query

    def validate_autopk_value(self, value):
        """
        Certain backends do not accept some values for "serial" fields
        (for example zero in MySQL). This method will raise a ValueError
        if the value is invalid, otherwise returns validated value.
        """
        return value

    def value_to_db_date(self, value):
        """
        Transform a date value to an object compatible with what is expected
        by the backend driver for date columns.
        """
        if value is None:
            return None
        return six.text_type(value)

    def value_to_db_datetime(self, value):
        """
        Transform a datetime value to an object compatible with what is expected
        by the backend driver for datetime columns.
        """
        if value is None:
            return None
        return six.text_type(value)

    def value_to_db_time(self, value):
        """
        Transform a time value to an object compatible with what is expected
        by the backend driver for time columns.
        """
        if value is None:
            return None
        if timezone.is_aware(value):
            raise ValueError("Django does not support timezone-aware times.")
        return six.text_type(value)

    def value_to_db_decimal(self, value, max_digits, decimal_places):
        """
        Transform a decimal.Decimal value to an object compatible with what is
        expected by the backend driver for decimal (numeric) columns.
        """
        if value is None:
            return None
        return util.format_number(value, max_digits, decimal_places)

    def year_lookup_bounds_for_date_field(self, value):
        """
        Returns a two-elements list with the lower and upper bound to be used
        with a BETWEEN operator to query a DateField value using a year
        lookup.

        `value` is an int, containing the looked-up year.
        """
        first = datetime.date(value, 1, 1)
        second = datetime.date(value, 12, 31)
        return [first, second]

    def year_lookup_bounds_for_datetime_field(self, value):
        """
        Returns a two-elements list with the lower and upper bound to be used
        with a BETWEEN operator to query a DateTimeField value using a year
        lookup.

        `value` is an int, containing the looked-up year.
        """
        first = datetime.datetime(value, 1, 1)
        second = datetime.datetime(value, 12, 31, 23, 59, 59, 999999)
        if settings.USE_TZ:
            tz = timezone.get_current_timezone()
            first = timezone.make_aware(first, tz)
            second = timezone.make_aware(second, tz)
        return [first, second]

    def convert_values(self, value, field):
        """
        Coerce the value returned by the database backend into a consistent type
        that is compatible with the field type.
        """
        if value is None or field is None:
            return value
        internal_type = field.get_internal_type()
        if internal_type == 'FloatField':
            return float(value)
        elif (internal_type and (internal_type.endswith('IntegerField')
                                 or internal_type == 'AutoField')):
            return int(value)
        return value

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


# Structure returned by the DB-API cursor.description interface (PEP 249)
FieldInfo = namedtuple('FieldInfo',
    'name type_code display_size internal_size precision scale null_ok'
)

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

    def table_names(self, cursor=None):
        """
        Returns a list of names of all tables that exist in the database.
        The returned table list is sorted by Python's default sorting. We
        do NOT use database's ORDER BY here to avoid subtle differences
        in sorting order between databases.
        """
        if cursor is None:
            cursor = self.connection.cursor()
        return sorted(self.get_table_list(cursor))

    def get_table_list(self, cursor):
        """
        Returns an unsorted list of names of all tables that exist in the
        database.
        """
        raise NotImplementedError

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
        tables = list(map(self.table_name_converter, tables))
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
                if model._meta.swapped:
                    continue
                if not router.allow_syncdb(self.connection.alias, model):
                    continue
                for f in model._meta.local_fields:
                    if isinstance(f, models.AutoField):
                        sequence_list.append({'table': model._meta.db_table, 'column': f.column})
                        break  # Only one AutoField is allowed per model, so don't bother continuing.

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
        Returns the name of the primary key column for the given table.
        """
        for column in six.iteritems(self.get_indexes(cursor, table_name)):
            if column[1]['primary_key']:
                return column[0]
        return None

    def get_indexes(self, cursor, table_name):
        """
        Returns a dictionary of indexed fieldname -> infodict for the given
        table, where each infodict is in the format:
            {'primary_key': boolean representing whether it's the primary key,
             'unique': boolean representing whether it's a unique index}

        Only single-column indexes are introspected.
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
