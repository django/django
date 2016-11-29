from __future__ import unicode_literals

import datetime
import uuid

from django.conf import settings
from django.core.exceptions import FieldError
from django.db import utils
from django.db.backends import utils as backend_utils
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.models import aggregates, fields
from django.utils import six, timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time
from django.utils.duration import duration_string


class DatabaseOperations(BaseDatabaseOperations):
    def bulk_batch_size(self, fields, objs):
        """
        SQLite has a compile-time default (SQLITE_LIMIT_VARIABLE_NUMBER) of
        999 variables per query.

        If there's only a single field to insert, the limit is 500
        (SQLITE_MAX_COMPOUND_SELECT).
        """
        limit = 999 if len(fields) > 1 else 500
        return (limit // len(fields)) if len(fields) > 0 else len(objs)

    def check_expression_support(self, expression):
        bad_fields = (fields.DateField, fields.DateTimeField, fields.TimeField)
        bad_aggregates = (aggregates.Sum, aggregates.Avg, aggregates.Variance, aggregates.StdDev)
        if isinstance(expression, bad_aggregates):
            for expr in expression.get_source_expressions():
                try:
                    output_field = expr.output_field
                    if isinstance(output_field, bad_fields):
                        raise NotImplementedError(
                            'You cannot use Sum, Avg, StdDev, and Variance '
                            'aggregations on date/time fields in sqlite3 '
                            'since date/time is saved as text.'
                        )
                except FieldError:
                    # Not every subexpression has an output_field which is fine
                    # to ignore.
                    pass

    def date_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_date_extract that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_extract('%s', %s)" % (lookup_type.lower(), field_name)

    def date_interval_sql(self, timedelta):
        return "'%s'" % duration_string(timedelta), []

    def format_for_duration_arithmetic(self, sql):
        """Do nothing here, we will handle it in the custom function."""
        return sql

    def date_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_date_trunc('%s', %s)" % (lookup_type.lower(), field_name)

    def time_trunc_sql(self, lookup_type, field_name):
        # sqlite doesn't support DATE_TRUNC, so we fake it with a user-defined
        # function django_date_trunc that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_time_trunc('%s', %s)" % (lookup_type.lower(), field_name)

    def datetime_cast_date_sql(self, field_name, tzname):
        return "django_datetime_cast_date(%s, %%s)" % field_name, [tzname]

    def datetime_cast_time_sql(self, field_name, tzname):
        return "django_datetime_cast_time(%s, %%s)" % field_name, [tzname]

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_extract_sql.
        return "django_datetime_extract('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_trunc_sql.
        return "django_datetime_trunc('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def time_extract_sql(self, lookup_type, field_name):
        # sqlite doesn't support extract, so we fake it with the user-defined
        # function django_time_extract that's registered in connect(). Note that
        # single quotes are used because this is a string (and could otherwise
        # cause a collision with a field name).
        return "django_time_extract('%s', %s)" % (lookup_type.lower(), field_name)

    def pk_default_value(self):
        return "NULL"

    def _quote_params_for_last_executed_query(self, params):
        """
        Only for last_executed_query! Don't use this to execute SQL queries!
        """
        # This function is limited both by SQLITE_LIMIT_VARIABLE_NUMBER (the
        # number of parameters, default = 999) and SQLITE_MAX_COLUMN (the
        # number of return values, default = 2000). Since Python's sqlite3
        # module doesn't expose the get_limit() C API, assume the default
        # limits are in effect and split the work in batches if needed.
        BATCH_SIZE = 999
        if len(params) > BATCH_SIZE:
            results = ()
            for index in range(0, len(params), BATCH_SIZE):
                chunk = params[index:index + BATCH_SIZE]
                results += self._quote_params_for_last_executed_query(chunk)
            return results

        sql = 'SELECT ' + ', '.join(['QUOTE(?)'] * len(params))
        # Bypass Django's wrappers and use the underlying sqlite3 connection
        # to avoid logging this query - it would trigger infinite recursion.
        cursor = self.connection.connection.cursor()
        # Native sqlite3 cursors cannot be used as context managers.
        try:
            return cursor.execute(sql, params).fetchone()
        finally:
            cursor.close()

    def last_executed_query(self, cursor, sql, params):
        # Python substitutes parameters in Modules/_sqlite/cursor.c with:
        # pysqlite_statement_bind_parameters(self->statement, parameters, allow_8bit_chars);
        # Unfortunately there is no way to reach self->statement from Python,
        # so we quote and substitute parameters manually.
        if params:
            if isinstance(params, (list, tuple)):
                params = self._quote_params_for_last_executed_query(params)
            else:
                keys = params.keys()
                values = tuple(params.values())
                values = self._quote_params_for_last_executed_query(values)
                params = dict(zip(keys, values))
            return sql % params
        # For consistency with SQLiteCursorWrapper.execute(), just return sql
        # when there are no parameters. See #13648 and #17158.
        else:
            return sql

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name  # Quoting once is enough.
        return '"%s"' % name

    def no_limit_value(self):
        return -1

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # NB: The generated SQL below is specific to SQLite
        # Note: The DELETE FROM... SQL generated below works for SQLite databases
        # because constraints don't exist
        sql = ['%s %s %s;' % (
            style.SQL_KEYWORD('DELETE'),
            style.SQL_KEYWORD('FROM'),
            style.SQL_FIELD(self.quote_name(table))
        ) for table in tables]
        # Note: No requirement for reset of auto-incremented indices (cf. other
        # sql_flush() implementations). Just return SQL at this point
        return sql

    def adapt_datetimefield_value(self, value):
        if value is None:
            return None

        # Expression values are adapted by the database.
        if hasattr(value, 'resolve_expression'):
            return value

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = timezone.make_naive(value, self.connection.timezone)
            else:
                raise ValueError("SQLite backend does not support timezone-aware datetimes when USE_TZ is False.")

        return six.text_type(value)

    def adapt_timefield_value(self, value):
        if value is None:
            return None

        # Expression values are adapted by the database.
        if hasattr(value, 'resolve_expression'):
            return value

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            raise ValueError("SQLite backend does not support timezone-aware times.")

        return six.text_type(value)

    def get_db_converters(self, expression):
        converters = super(DatabaseOperations, self).get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type == 'DateTimeField':
            converters.append(self.convert_datetimefield_value)
        elif internal_type == 'DateField':
            converters.append(self.convert_datefield_value)
        elif internal_type == 'TimeField':
            converters.append(self.convert_timefield_value)
        elif internal_type == 'DecimalField':
            converters.append(self.convert_decimalfield_value)
        elif internal_type == 'UUIDField':
            converters.append(self.convert_uuidfield_value)
        elif internal_type in ('NullBooleanField', 'BooleanField'):
            converters.append(self.convert_booleanfield_value)
        return converters

    def convert_datetimefield_value(self, value, expression, connection, context):
        if value is not None:
            if not isinstance(value, datetime.datetime):
                value = parse_datetime(value)
            if settings.USE_TZ and not timezone.is_aware(value):
                value = timezone.make_aware(value, self.connection.timezone)
        return value

    def convert_datefield_value(self, value, expression, connection, context):
        if value is not None:
            if not isinstance(value, datetime.date):
                value = parse_date(value)
        return value

    def convert_timefield_value(self, value, expression, connection, context):
        if value is not None:
            if not isinstance(value, datetime.time):
                value = parse_time(value)
        return value

    def convert_decimalfield_value(self, value, expression, connection, context):
        if value is not None:
            value = expression.output_field.format_number(value)
            value = backend_utils.typecast_decimal(value)
        return value

    def convert_uuidfield_value(self, value, expression, connection, context):
        if value is not None:
            value = uuid.UUID(value)
        return value

    def convert_booleanfield_value(self, value, expression, connection, context):
        return bool(value) if value in (1, 0) else value

    def bulk_insert_sql(self, fields, placeholder_rows):
        return " UNION ALL ".join(
            "SELECT %s" % ", ".join(row)
            for row in placeholder_rows
        )

    def combine_expression(self, connector, sub_expressions):
        # SQLite doesn't have a power function, so we fake it with a
        # user-defined function django_power that's registered in connect().
        if connector == '^':
            return 'django_power(%s)' % ','.join(sub_expressions)
        return super(DatabaseOperations, self).combine_expression(connector, sub_expressions)

    def combine_duration_expression(self, connector, sub_expressions):
        if connector not in ['+', '-']:
            raise utils.DatabaseError('Invalid connector for timedelta: %s.' % connector)
        fn_params = ["'%s'" % connector] + sub_expressions
        if len(fn_params) > 3:
            raise ValueError('Too many params for timedelta operations.')
        return "django_format_dtdelta(%s)" % ', '.join(fn_params)

    def integer_field_range(self, internal_type):
        # SQLite doesn't enforce any integer constraints
        return (None, None)

    def subtract_temporals(self, internal_type, lhs, rhs):
        lhs_sql, lhs_params = lhs
        rhs_sql, rhs_params = rhs
        if internal_type == 'TimeField':
            return "django_time_diff(%s, %s)" % (lhs_sql, rhs_sql), lhs_params + rhs_params
        return "django_timestamp_diff(%s, %s)" % (lhs_sql, rhs_sql), lhs_params + rhs_params
