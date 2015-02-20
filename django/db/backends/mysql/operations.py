from __future__ import unicode_literals

import uuid

from django.conf import settings
from django.db.backends.base.operations import BaseDatabaseOperations
from django.utils import six, timezone
from django.utils.encoding import force_text


class DatabaseOperations(BaseDatabaseOperations):
    compiler_module = "django.db.backends.mysql.compiler"

    # MySQL stores positive fields as UNSIGNED ints.
    integer_field_ranges = dict(BaseDatabaseOperations.integer_field_ranges,
        PositiveSmallIntegerField=(0, 4294967295),
        PositiveIntegerField=(0, 18446744073709551615),
    )

    def date_extract_sql(self, lookup_type, field_name):
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        if lookup_type == 'week_day':
            # DAYOFWEEK() returns an integer, 1-7, Sunday=1.
            # Note: WEEKDAY() returns 0-6, Monday=0.
            return "DAYOFWEEK(%s)" % field_name
        else:
            return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_trunc_sql(self, lookup_type, field_name):
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s')  # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "CONVERT_TZ(%s, 'UTC', %%s)" % field_name
            params = [tzname]
        else:
            params = []
        # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
        if lookup_type == 'week_day':
            # DAYOFWEEK() returns an integer, 1-7, Sunday=1.
            # Note: WEEKDAY() returns 0-6, Monday=0.
            sql = "DAYOFWEEK(%s)" % field_name
        else:
            sql = "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)
        return sql, params

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = "CONVERT_TZ(%s, 'UTC', %%s)" % field_name
            params = [tzname]
        else:
            params = []
        fields = ['year', 'month', 'day', 'hour', 'minute', 'second']
        format = ('%%Y-', '%%m', '-%%d', ' %%H:', '%%i', ':%%s')  # Use double percents to escape.
        format_def = ('0000-', '01', '-01', ' 00:', '00', ':00')
        try:
            i = fields.index(lookup_type) + 1
        except ValueError:
            sql = field_name
        else:
            format_str = ''.join([f for f in format[:i]] + [f for f in format_def[i:]])
            sql = "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, format_str)
        return sql, params

    def date_interval_sql(self, timedelta):
        return "INTERVAL '%d 0:0:%d:%d' DAY_MICROSECOND" % (
            timedelta.days, timedelta.seconds, timedelta.microseconds), []

    def format_for_duration_arithmetic(self, sql):
        return 'INTERVAL %s MICROSECOND' % sql

    def drop_foreignkey_sql(self):
        return "DROP FOREIGN KEY"

    def force_no_ordering(self):
        """
        "ORDER BY NULL" prevents MySQL from implicitly ordering by grouped
        columns. If no ordering would otherwise be applied, we don't want any
        implicit sorting going on.
        """
        return [(None, ("NULL", [], False))]

    def fulltext_search_sql(self, field_name):
        return 'MATCH (%s) AGAINST (%%s IN BOOLEAN MODE)' % field_name

    def last_executed_query(self, cursor, sql, params):
        # With MySQLdb, cursor objects have an (undocumented) "_last_executed"
        # attribute where the exact query sent to the database is saved.
        # See MySQLdb/cursors.py in the source distribution.
        return force_text(getattr(cursor, '_last_executed', None), errors='replace')

    def no_limit_value(self):
        # 2**64 - 1, as recommended by the MySQL documentation
        return 18446744073709551615

    def quote_name(self, name):
        if name.startswith("`") and name.endswith("`"):
            return name  # Quoting once is enough.
        return "`%s`" % name

    def random_function_sql(self):
        return 'RAND()'

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # NB: The generated SQL below is specific to MySQL
        # 'TRUNCATE x;', 'TRUNCATE y;', 'TRUNCATE z;'... style SQL statements
        # to clear all tables of all data
        if tables:
            sql = ['SET FOREIGN_KEY_CHECKS = 0;']
            for table in tables:
                sql.append('%s %s;' % (
                    style.SQL_KEYWORD('TRUNCATE'),
                    style.SQL_FIELD(self.quote_name(table)),
                ))
            sql.append('SET FOREIGN_KEY_CHECKS = 1;')
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
            return sql
        else:
            return []

    def validate_autopk_value(self, value):
        # MySQLism: zero in AUTO_INCREMENT field does not work. Refs #17653.
        if value == 0:
            raise ValueError('The database backend does not accept 0 as a '
                             'value for AutoField.')
        return value

    def value_to_db_datetime(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("MySQL backend does not support timezone-aware datetimes when USE_TZ is False.")

        return six.text_type(value)

    def value_to_db_time(self, value):
        if value is None:
            return None

        # MySQL doesn't support tz-aware times
        if timezone.is_aware(value):
            raise ValueError("MySQL backend does not support timezone-aware times.")

        return six.text_type(value)

    def max_name_length(self):
        return 64

    def bulk_insert_sql(self, fields, num_values):
        items_sql = "(%s)" % ", ".join(["%s"] * len(fields))
        return "VALUES " + ", ".join([items_sql] * num_values)

    def combine_expression(self, connector, sub_expressions):
        """
        MySQL requires special cases for ^ operators in query expressions
        """
        if connector == '^':
            return 'POW(%s)' % ','.join(sub_expressions)
        return super(DatabaseOperations, self).combine_expression(connector, sub_expressions)

    def get_db_converters(self, expression):
        converters = super(DatabaseOperations, self).get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type in ['BooleanField', 'NullBooleanField']:
            converters.append(self.convert_booleanfield_value)
        if internal_type == 'UUIDField':
            converters.append(self.convert_uuidfield_value)
        if internal_type == 'TextField':
            converters.append(self.convert_textfield_value)
        return converters

    def convert_booleanfield_value(self, value, expression, connection, context):
        if value in (0, 1):
            value = bool(value)
        return value

    def convert_uuidfield_value(self, value, expression, connection, context):
        if value is not None:
            value = uuid.UUID(value)
        return value

    def convert_textfield_value(self, value, expression, connection, context):
        if value is not None:
            value = force_text(value)
        return value
