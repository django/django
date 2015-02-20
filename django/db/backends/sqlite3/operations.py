from __future__ import unicode_literals

import datetime
import uuid

from django.conf import settings
from django.core.exceptions import FieldError, ImproperlyConfigured
from django.db import utils
from django.db.backends import utils as backend_utils
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.models import aggregates, fields
from django.utils import six, timezone
from django.utils.dateparse import parse_date, parse_time
from django.utils.duration import duration_string

from .utils import parse_datetime_with_timezone_support

try:
    import pytz
except ImportError:
    pytz = None


class DatabaseOperations(BaseDatabaseOperations):
    def bulk_batch_size(self, fields, objs):
        """
        SQLite has a compile-time default (SQLITE_LIMIT_VARIABLE_NUMBER) of
        999 variables per query.

        If there is just single field to insert, then we can hit another
        limit, SQLITE_MAX_COMPOUND_SELECT which defaults to 500.
        """
        limit = 999 if len(fields) > 1 else 500
        return (limit // len(fields)) if len(fields) > 0 else len(objs)

    def check_expression_support(self, expression):
        bad_fields = (fields.DateField, fields.DateTimeField, fields.TimeField)
        bad_aggregates = (aggregates.Sum, aggregates.Avg, aggregates.Variance, aggregates.StdDev)
        if isinstance(expression, bad_aggregates):
            try:
                output_field = expression.input_field.output_field
                if isinstance(output_field, bad_fields):
                    raise NotImplementedError(
                        'You cannot use Sum, Avg, StdDev and Variance aggregations '
                        'on date/time fields in sqlite3 '
                        'since date/time is saved as text.')
            except FieldError:
                # not every sub-expression has an output_field which is fine to
                # ignore
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

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_extract_sql.
        if settings.USE_TZ:
            if pytz is None:
                raise ImproperlyConfigured("This query requires pytz, "
                                           "but it isn't installed.")
        return "django_datetime_extract('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        # Same comment as in date_trunc_sql.
        if settings.USE_TZ:
            if pytz is None:
                raise ImproperlyConfigured("This query requires pytz, "
                                           "but it isn't installed.")
        return "django_datetime_trunc('%s', %s, %%s)" % (
            lookup_type.lower(), field_name), [tzname]

    def drop_foreignkey_sql(self):
        return ""

    def pk_default_value(self):
        return "NULL"

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

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # SQLite doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("SQLite backend does not support timezone-aware datetimes when USE_TZ is False.")

        return six.text_type(value)

    def value_to_db_time(self, value):
        if value is None:
            return None

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
        return converters

    def convert_decimalfield_value(self, value, expression, connection, context):
        return backend_utils.typecast_decimal(expression.output_field.format_number(value))

    def convert_datefield_value(self, value, expression, connection, context):
        if value is not None and not isinstance(value, datetime.date):
            value = parse_date(value)
        return value

    def convert_datetimefield_value(self, value, expression, connection, context):
        if value is not None and not isinstance(value, datetime.datetime):
            value = parse_datetime_with_timezone_support(value)
        return value

    def convert_timefield_value(self, value, expression, connection, context):
        if value is not None and not isinstance(value, datetime.time):
            value = parse_time(value)
        return value

    def convert_uuidfield_value(self, value, expression, connection, context):
        if value is not None:
            value = uuid.UUID(value)
        return value

    def bulk_insert_sql(self, fields, num_values):
        res = []
        res.append("SELECT %s" % ", ".join(
            "%%s AS %s" % self.quote_name(f.column) for f in fields
        ))
        res.extend(["UNION ALL SELECT %s" % ", ".join(["%s"] * len(fields))] * (num_values - 1))
        return " ".join(res)

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
