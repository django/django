import decimal
from threading import local

from django.db import DEFAULT_DB_ALIAS
from django.db.backends import util
from django.utils import datetime_safe
from django.utils.importlib import import_module

class BaseDatabaseWrapper(local):
    """
    Represents a database connection.
    """
    ops = None

    def __init__(self, settings_dict, alias=DEFAULT_DB_ALIAS):
        # `settings_dict` should be a dictionary containing keys such as
        # NAME, USER, etc. It's called `settings_dict` instead of `settings`
        # to disambiguate it from Django settings modules.
        self.connection = None
        self.queries = []
        self.settings_dict = settings_dict
        self.alias = alias

    def __eq__(self, other):
        return self.settings_dict == other.settings_dict

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

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def cursor(self):
        from django.conf import settings
        cursor = self._cursor()
        if settings.DEBUG:
            return self.make_debug_cursor(cursor)
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
    interprets_empty_strings_as_nulls = False
    can_use_chunked_reads = True
    can_return_id_from_insert = False
    uses_autocommit = False
    uses_savepoints = False
    # If True, don't use integer foreign keys referring to, e.g., positive
    # integer primary keys.
    related_fields_match_type = False
    allow_sliced_subqueries = True

class BaseDatabaseOperations(object):
    """
    This class encapsulates all backend-specific differences, such as the way
    a backend performs ordering or calculates the ID of a recently-inserted
    row.
    """
    compiler_module = "django.db.models.sql.compiler"

    def __init__(self):
        self._cache = {}

    def autoinc_sql(self, table, column):
        """
        Returns any SQL needed to support auto-incrementing primary keys, or
        None if no SQL is necessary.

        This SQL is executed when a table is created.
        """
        return None

    def date_extract_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month' or 'day', returns the SQL that
        extracts a value from the given date field field_name.
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
        if compiler_name not in self._cache:
            self._cache[compiler_name] = getattr(
                import_module(self.compiler_module), compiler_name
            )
        return self._cache[compiler_name]

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

    def tablespace_sql(self, tablespace, inline=False):
        """
        Returns the SQL that will be appended to tables or rows to define
        a tablespace. Returns '' if the backend doesn't use tablespaces.
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
        return datetime_safe.new_date(value).strftime('%Y-%m-%d')

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
        Transform a datetime value to an object compatible with what is expected
        by the backend driver for time columns.
        """
        if value is None:
            return None
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
        raise NotImplemented.
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
        if only_existing:
            tables = [t for t in tables if self.table_name_converter(t) in self.table_names()]
        return tables

    def installed_models(self, tables):
        "Returns a set of all models represented by the provided list of table names."
        from django.db import models, router
        all_models = []
        for app in models.get_apps():
            for model in models.get_models(app):
                if router.allow_syncdb(self.connection.alias, model):
                    all_models.append(model)
        return set([m for m in all_models
            if self.table_name_converter(m._meta.db_table) in map(self.table_name_converter, tables)
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
