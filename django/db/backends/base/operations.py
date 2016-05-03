import datetime
import decimal
import warnings
from importlib import import_module

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.backends import utils
from django.utils import six, timezone
from django.utils.dateparse import parse_duration
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.encoding import force_text


class BaseDatabaseOperations(object):
    """
    This class encapsulates all backend-specific differences, such as the way
    a backend performs ordering or calculates the ID of a recently-inserted
    row.
    """
    compiler_module = "django.db.models.sql.compiler"

    # Integer field safe ranges by `internal_type` as documented
    # in docs/ref/models/fields.txt.
    integer_field_ranges = {
        'SmallIntegerField': (-32768, 32767),
        'IntegerField': (-2147483648, 2147483647),
        'BigIntegerField': (-9223372036854775808, 9223372036854775807),
        'PositiveSmallIntegerField': (0, 32767),
        'PositiveIntegerField': (0, 2147483647),
    }

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

    def unification_cast_sql(self, output_field):
        """
        Given a field instance, returns the SQL necessary to cast the result of
        a union to that type. Note that the resulting string should contain a
        '%s' placeholder for the expression being cast.
        """
        return '%s'

    def date_extract_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month' or 'day', returns the SQL that
        extracts a value from the given date field field_name.
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a date_extract_sql() method')

    def date_interval_sql(self, timedelta):
        """
        Implements the date interval functionality for expressions
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a date_interval_sql() method')

    def date_trunc_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month' or 'day', returns the SQL that
        truncates the given date field field_name to a date object with only
        the given specificity.
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a datetrunc_sql() method')

    def datetime_cast_date_sql(self, field_name, tzname):
        """
        Returns the SQL necessary to cast a datetime value to date value.
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a datetime_cast_date() method')

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute' or
        'second', returns the SQL that extracts a value from the given
        datetime field field_name, and a tuple of parameters.
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a datetime_extract_sql() method')

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        """
        Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute' or
        'second', returns the SQL that truncates the given datetime field
        field_name to a datetime object with only the given specificity, and
        a tuple of parameters.
        """
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a datetime_trunk_sql() method')

    def time_extract_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'hour', 'minute' or 'second', returns the SQL
        that extracts a value from the given time field field_name.
        """
        return self.date_extract_sql(lookup_type, field_name)

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
        # Convert params to contain Unicode values.
        to_unicode = lambda s: force_text(s, strings_only=True, errors='replace')
        if isinstance(params, (list, tuple)):
            u_params = tuple(to_unicode(val) for val in params)
        elif params is None:
            u_params = ()
        else:
            u_params = {to_unicode(k): to_unicode(v) for k, v in params.items()}

        return six.text_type("QUERY = %r - PARAMS = %r") % (sql, u_params)

    def last_insert_id(self, cursor, table_name, pk_name):
        """
        Given a cursor object that has just performed an INSERT statement into
        a table that has an auto-incrementing ID, returns the newly created ID.

        This method also receives the table name and the name of the primary-key
        column.
        """
        return cursor.lastrowid

    def lookup_cast(self, lookup_type, internal_type=None):
        """
        Returns the string to use in a query when performing lookups
        ("contains", "like", etc.). The resulting string should contain a '%s'
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
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a no_limit_value() method')

    def pk_default_value(self):
        """
        Returns the value to use during an INSERT statement to specify that
        the field should use its default value.
        """
        return 'DEFAULT'

    def prepare_sql_script(self, sql):
        """
        Takes an SQL script that may contain multiple lines and returns a list
        of statements to feed to successive cursor.execute() calls.

        Since few databases are able to process raw SQL scripts in a single
        cursor.execute() call and PEP 249 doesn't talk about this use case,
        the default implementation is conservative.
        """
        try:
            import sqlparse
        except ImportError:
            raise ImproperlyConfigured(
                "sqlparse is required if you don't split your SQL "
                "statements manually."
            )
        else:
            return [sqlparse.format(statement, strip_comments=True)
                    for statement in sqlparse.split(sql) if statement]

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
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a quote_name() method')

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
        raise NotImplementedError('subclasses of BaseDatabaseOperations may require a regex_lookup() method')

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
        raise NotImplementedError('subclasses of BaseDatabaseOperations must provide an sql_flush() method')

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

    def adapt_unknown_value(self, value):
        """
        Transforms a value to something compatible with the backend driver.

        This method only depends on the type of the value. It's designed for
        cases where the target type isn't known, such as .raw() SQL queries.
        As a consequence it may not work perfectly in all circumstances.
        """
        if isinstance(value, datetime.datetime):   # must be before date
            return self.adapt_datetimefield_value(value)
        elif isinstance(value, datetime.date):
            return self.adapt_datefield_value(value)
        elif isinstance(value, datetime.time):
            return self.adapt_timefield_value(value)
        elif isinstance(value, decimal.Decimal):
            return self.adapt_decimalfield_value(value)
        else:
            return value

    def adapt_datefield_value(self, value):
        """
        Transforms a date value to an object compatible with what is expected
        by the backend driver for date columns.
        """
        if value is None:
            return None
        return six.text_type(value)

    def adapt_datetimefield_value(self, value):
        """
        Transforms a datetime value to an object compatible with what is expected
        by the backend driver for datetime columns.
        """
        if value is None:
            return None
        return six.text_type(value)

    def adapt_timefield_value(self, value):
        """
        Transforms a time value to an object compatible with what is expected
        by the backend driver for time columns.
        """
        if value is None:
            return None
        if timezone.is_aware(value):
            raise ValueError("Django does not support timezone-aware times.")
        return six.text_type(value)

    def adapt_decimalfield_value(self, value, max_digits=None, decimal_places=None):
        """
        Transforms a decimal.Decimal value to an object compatible with what is
        expected by the backend driver for decimal (numeric) columns.
        """
        return utils.format_number(value, max_digits, decimal_places)

    def adapt_ipaddressfield_value(self, value):
        """
        Transforms a string representation of an IP address into the expected
        type for the backend driver.
        """
        return value or None

    def year_lookup_bounds_for_date_field(self, value):
        """
        Returns a two-elements list with the lower and upper bound to be used
        with a BETWEEN operator to query a DateField value using a year
        lookup.

        `value` is an int, containing the looked-up year.
        """
        first = datetime.date(value, 1, 1)
        second = datetime.date(value, 12, 31)
        first = self.adapt_datefield_value(first)
        second = self.adapt_datefield_value(second)
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
        first = self.adapt_datetimefield_value(first)
        second = self.adapt_datetimefield_value(second)
        return [first, second]

    def get_db_converters(self, expression):
        """
        Get a list of functions needed to convert field data.

        Some field types on some backends do not provide data in the correct
        format, this is the hook for converter functions.
        """
        return []

    def convert_durationfield_value(self, value, expression, connection, context):
        if value is not None:
            value = str(decimal.Decimal(value) / decimal.Decimal(1000000))
            value = parse_duration(value)
        return value

    def check_aggregate_support(self, aggregate_func):
        warnings.warn(
            "check_aggregate_support has been deprecated. Use "
            "check_expression_support instead.",
            RemovedInDjango20Warning, stacklevel=2)
        return self.check_expression_support(aggregate_func)

    def check_expression_support(self, expression):
        """
        Check that the backend supports the provided expression.

        This is used on specific backends to rule out known expressions
        that have problematic or nonexistent implementations. If the
        expression has a known problem, the backend should raise
        NotImplementedError.
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

    def combine_duration_expression(self, connector, sub_expressions):
        return self.combine_expression(connector, sub_expressions)

    def modify_insert_params(self, placeholder, params):
        """Allow modification of insert parameters. Needed for Oracle Spatial
        backend due to #10888.
        """
        return params

    def integer_field_range(self, internal_type):
        """
        Given an integer field internal type (e.g. 'PositiveIntegerField'),
        returns a tuple of the (min_value, max_value) form representing the
        range of the column type bound to the field.
        """
        return self.integer_field_ranges[internal_type]
