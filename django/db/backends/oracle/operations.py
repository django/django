from __future__ import unicode_literals

import datetime
import re
import uuid

from django.conf import settings
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.backends.utils import strip_quotes, truncate_name
from django.utils import six, timezone
from django.utils.encoding import force_bytes, force_text

from .base import Database
from .utils import InsertIdVar, Oracle_datetime


class DatabaseOperations(BaseDatabaseOperations):
    compiler_module = "django.db.backends.oracle.compiler"

    # Oracle uses NUMBER(11) and NUMBER(19) for integer fields.
    integer_field_ranges = {
        'SmallIntegerField': (-99999999999, 99999999999),
        'IntegerField': (-99999999999, 99999999999),
        'BigIntegerField': (-9999999999999999999, 9999999999999999999),
        'PositiveSmallIntegerField': (0, 99999999999),
        'PositiveIntegerField': (0, 99999999999),
    }

    # TODO: colorize this SQL code with style.SQL_KEYWORD(), etc.
    _sequence_reset_sql = """
DECLARE
    table_value integer;
    seq_value integer;
BEGIN
    SELECT NVL(MAX(%(column)s), 0) INTO table_value FROM %(table)s;
    SELECT NVL(last_number - cache_size, 0) INTO seq_value FROM user_sequences
           WHERE sequence_name = '%(sequence)s';
    WHILE table_value > seq_value LOOP
        SELECT "%(sequence)s".nextval INTO seq_value FROM dual;
    END LOOP;
END;
/"""

    def __init__(self, *args, **kwargs):
        super(DatabaseOperations, self).__init__(*args, **kwargs)
        self.set_operators['difference'] = 'MINUS'

    def autoinc_sql(self, table, column):
        # To simulate auto-incrementing primary keys in Oracle, we have to
        # create a sequence and a trigger.
        args = {
            'sq_name': self._get_sequence_name(table),
            'tr_name': self._get_trigger_name(table),
            'tbl_name': self.quote_name(table),
            'col_name': self.quote_name(column),
        }
        sequence_sql = """
DECLARE
    i INTEGER;
BEGIN
    SELECT COUNT(1) INTO i FROM USER_SEQUENCES
        WHERE SEQUENCE_NAME = '%(sq_name)s';
    IF i = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE "%(sq_name)s"';
    END IF;
END;
/""" % args
        trigger_sql = """
CREATE OR REPLACE TRIGGER "%(tr_name)s"
BEFORE INSERT ON %(tbl_name)s
FOR EACH ROW
WHEN (new.%(col_name)s IS NULL)
    BEGIN
        SELECT "%(sq_name)s".nextval
        INTO :new.%(col_name)s FROM dual;
    END;
/""" % args
        return sequence_sql, trigger_sql

    def cache_key_culling_sql(self):
        return """
            SELECT cache_key
              FROM (SELECT cache_key, rank() OVER (ORDER BY cache_key) AS rank FROM %s)
             WHERE rank = %%s + 1
        """

    def date_extract_sql(self, lookup_type, field_name):
        if lookup_type == 'week_day':
            # TO_CHAR(field, 'D') returns an integer from 1-7, where 1=Sunday.
            return "TO_CHAR(%s, 'D')" % field_name
        elif lookup_type == 'week':
            # IW = ISO week number
            return "TO_CHAR(%s, 'IW')" % field_name
        else:
            # http://docs.oracle.com/cd/B19306_01/server.102/b14200/functions050.htm
            return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_interval_sql(self, timedelta):
        """
        NUMTODSINTERVAL converts number to INTERVAL DAY TO SECOND literal.
        """
        return "NUMTODSINTERVAL(%06f, 'SECOND')" % (timedelta.total_seconds()), []

    def date_trunc_sql(self, lookup_type, field_name):
        # http://docs.oracle.com/cd/B19306_01/server.102/b14200/functions230.htm#i1002084
        if lookup_type in ('year', 'month'):
            return "TRUNC(%s, '%s')" % (field_name, lookup_type.upper())
        else:
            return "TRUNC(%s)" % field_name

    # Oracle crashes with "ORA-03113: end-of-file on communication channel"
    # if the time zone name is passed in parameter. Use interpolation instead.
    # https://groups.google.com/forum/#!msg/django-developers/zwQju7hbG78/9l934yelwfsJ
    # This regexp matches all time zone names from the zoneinfo database.
    _tzname_re = re.compile(r'^[\w/:+-]+$')

    def _convert_field_to_tz(self, field_name, tzname):
        if not settings.USE_TZ:
            return field_name
        if not self._tzname_re.match(tzname):
            raise ValueError("Invalid time zone name: %s" % tzname)
        # Convert from UTC to local time, returning TIMESTAMP WITH TIME ZONE
        # and cast it back to TIMESTAMP to strip the TIME ZONE details.
        return "CAST((FROM_TZ(%s, '0:00') AT TIME ZONE '%s') AS TIMESTAMP)" % (field_name, tzname)

    def datetime_cast_date_sql(self, field_name, tzname):
        field_name = self._convert_field_to_tz(field_name, tzname)
        sql = 'TRUNC(%s)' % field_name
        return sql, []

    def datetime_cast_time_sql(self, field_name, tzname):
        # Since `TimeField` values are stored as TIMESTAMP where only the date
        # part is ignored, convert the field to the specified timezone.
        field_name = self._convert_field_to_tz(field_name, tzname)
        return field_name, []

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        field_name = self._convert_field_to_tz(field_name, tzname)
        sql = self.date_extract_sql(lookup_type, field_name)
        return sql, []

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        field_name = self._convert_field_to_tz(field_name, tzname)
        # http://docs.oracle.com/cd/B19306_01/server.102/b14200/functions230.htm#i1002084
        if lookup_type in ('year', 'month'):
            sql = "TRUNC(%s, '%s')" % (field_name, lookup_type.upper())
        elif lookup_type == 'day':
            sql = "TRUNC(%s)" % field_name
        elif lookup_type == 'hour':
            sql = "TRUNC(%s, 'HH24')" % field_name
        elif lookup_type == 'minute':
            sql = "TRUNC(%s, 'MI')" % field_name
        else:
            sql = "CAST(%s AS DATE)" % field_name  # Cast to DATE removes sub-second precision.
        return sql, []

    def time_trunc_sql(self, lookup_type, field_name):
        # The implementation is similar to `datetime_trunc_sql` as both
        # `DateTimeField` and `TimeField` are stored as TIMESTAMP where
        # the date part of the later is ignored.
        if lookup_type == 'hour':
            sql = "TRUNC(%s, 'HH24')" % field_name
        elif lookup_type == 'minute':
            sql = "TRUNC(%s, 'MI')" % field_name
        elif lookup_type == 'second':
            sql = "CAST(%s AS DATE)" % field_name  # Cast to DATE removes sub-second precision.
        return sql

    def get_db_converters(self, expression):
        converters = super(DatabaseOperations, self).get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type == 'TextField':
            converters.append(self.convert_textfield_value)
        elif internal_type == 'BinaryField':
            converters.append(self.convert_binaryfield_value)
        elif internal_type in ['BooleanField', 'NullBooleanField']:
            converters.append(self.convert_booleanfield_value)
        elif internal_type == 'DateTimeField':
            converters.append(self.convert_datetimefield_value)
        elif internal_type == 'DateField':
            converters.append(self.convert_datefield_value)
        elif internal_type == 'TimeField':
            converters.append(self.convert_timefield_value)
        elif internal_type == 'UUIDField':
            converters.append(self.convert_uuidfield_value)
        converters.append(self.convert_empty_values)
        return converters

    def convert_textfield_value(self, value, expression, connection, context):
        if isinstance(value, Database.LOB):
            value = force_text(value.read())
        return value

    def convert_binaryfield_value(self, value, expression, connection, context):
        if isinstance(value, Database.LOB):
            value = force_bytes(value.read())
        return value

    def convert_booleanfield_value(self, value, expression, connection, context):
        if value in (0, 1):
            value = bool(value)
        return value

    # cx_Oracle always returns datetime.datetime objects for
    # DATE and TIMESTAMP columns, but Django wants to see a
    # python datetime.date, .time, or .datetime.

    def convert_datetimefield_value(self, value, expression, connection, context):
        if value is not None:
            if settings.USE_TZ:
                value = timezone.make_aware(value, self.connection.timezone)
        return value

    def convert_datefield_value(self, value, expression, connection, context):
        if isinstance(value, Database.Timestamp):
            value = value.date()
        return value

    def convert_timefield_value(self, value, expression, connection, context):
        if isinstance(value, Database.Timestamp):
            value = value.time()
        return value

    def convert_uuidfield_value(self, value, expression, connection, context):
        if value is not None:
            value = uuid.UUID(value)
        return value

    def convert_empty_values(self, value, expression, connection, context):
        # Oracle stores empty strings as null. We need to undo this in
        # order to adhere to the Django convention of using the empty
        # string instead of null, but only if the field accepts the
        # empty string.
        field = expression.output_field
        if value is None and field.empty_strings_allowed:
            value = ''
            if field.get_internal_type() == 'BinaryField':
                value = b''
        return value

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def fetch_returned_insert_id(self, cursor):
        return int(cursor._insert_id_var.getvalue())

    def field_cast_sql(self, db_type, internal_type):
        if db_type and db_type.endswith('LOB'):
            return "DBMS_LOB.SUBSTR(%s)"
        else:
            return "%s"

    def last_executed_query(self, cursor, sql, params):
        # https://cx-oracle.readthedocs.io/en/latest/cursor.html#Cursor.statement
        # The DB API definition does not define this attribute.
        statement = cursor.statement
        if statement and six.PY2 and not isinstance(statement, unicode):  # NOQA: unicode undefined on PY3
            statement = statement.decode('utf-8')
        # Unlike Psycopg's `query` and MySQLdb`'s `_last_executed`, CxOracle's
        # `statement` doesn't contain the query parameters. refs #20010.
        return super(DatabaseOperations, self).last_executed_query(cursor, statement, params)

    def last_insert_id(self, cursor, table_name, pk_name):
        sq_name = self._get_sequence_name(table_name)
        cursor.execute('SELECT "%s".currval FROM dual' % sq_name)
        return cursor.fetchone()[0]

    def lookup_cast(self, lookup_type, internal_type=None):
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            return "UPPER(%s)"
        return "%s"

    def max_in_list_size(self):
        return 1000

    def max_name_length(self):
        return 30

    def pk_default_value(self):
        return "NULL"

    def prep_for_iexact_query(self, x):
        return x

    def process_clob(self, value):
        if value is None:
            return ''
        return force_text(value.read())

    def quote_name(self, name):
        # SQL92 requires delimited (quoted) names to be case-sensitive.  When
        # not quoted, Oracle has case-insensitive behavior for identifiers, but
        # always defaults to uppercase.
        # We simplify things by making Oracle identifiers always uppercase.
        if not name.startswith('"') and not name.endswith('"'):
            name = '"%s"' % truncate_name(name.upper(), self.max_name_length())
        # Oracle puts the query text into a (query % args) construct, so % signs
        # in names need to be escaped. The '%%' will be collapsed back to '%' at
        # that stage so we aren't really making the name longer here.
        name = name.replace('%', '%%')
        return name.upper()

    def random_function_sql(self):
        return "DBMS_RANDOM.RANDOM"

    def regex_lookup(self, lookup_type):
        if lookup_type == 'regex':
            match_option = "'c'"
        else:
            match_option = "'i'"
        return 'REGEXP_LIKE(%%s, %%s, %s)' % match_option

    def return_insert_id(self):
        return "RETURNING %s INTO %%s", (InsertIdVar(),)

    def savepoint_create_sql(self, sid):
        return "SAVEPOINT " + self.quote_name(sid)

    def savepoint_rollback_sql(self, sid):
        return "ROLLBACK TO SAVEPOINT " + self.quote_name(sid)

    def _foreign_key_constraints(self, table_name, recursive=False):
        with self.connection.cursor() as cursor:
            if recursive:
                cursor.execute("""
                    SELECT
                        user_tables.table_name, rcons.constraint_name, MAX(level)
                    FROM
                        user_tables
                    JOIN
                        user_constraints cons
                        ON (user_tables.table_name = cons.table_name AND cons.constraint_type = ANY('P', 'U'))
                    LEFT JOIN
                        user_constraints rcons
                        ON (user_tables.table_name = rcons.table_name AND rcons.constraint_type = 'R')
                    START WITH user_tables.table_name = UPPER(%s)
                    CONNECT BY NOCYCLE PRIOR cons.constraint_name = rcons.r_constraint_name
                    GROUP BY
                        user_tables.table_name, rcons.constraint_name
                    HAVING user_tables.table_name != UPPER(%s)
                    ORDER BY MAX(level) DESC
                """, (table_name, table_name))
            else:
                cursor.execute("""
                    SELECT
                        cons.table_name, cons.constraint_name, 1
                    FROM
                        user_constraints cons
                    WHERE
                        cons.constraint_type = 'R'
                        AND cons.table_name = UPPER(%s)
                """, (table_name,))
            return [
                (foreign_table, constraint) for foreign_table, constraint, _ in cursor.fetchall()
            ]

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        if tables:
            truncated_tables = {table.upper() for table in tables}
            constraints = set()
            # Oracle's TRUNCATE CASCADE only works with ON DELETE CASCADE
            # foreign keys which Django doesn't define. Emulate the
            # PostgreSQL behavior which truncates all dependent tables by
            # manually retrieving all foreign key constraints and resolving
            # dependencies.
            for table in tables:
                for foreign_table, constraint in self._foreign_key_constraints(table, recursive=allow_cascade):
                    if allow_cascade:
                        truncated_tables.add(foreign_table)
                    constraints.add((foreign_table, constraint))
            sql = [
                "%s %s %s %s %s %s %s %s;" % (
                    style.SQL_KEYWORD('ALTER'),
                    style.SQL_KEYWORD('TABLE'),
                    style.SQL_FIELD(self.quote_name(table)),
                    style.SQL_KEYWORD('DISABLE'),
                    style.SQL_KEYWORD('CONSTRAINT'),
                    style.SQL_FIELD(self.quote_name(constraint)),
                    style.SQL_KEYWORD('KEEP'),
                    style.SQL_KEYWORD('INDEX'),
                ) for table, constraint in constraints
            ] + [
                "%s %s %s;" % (
                    style.SQL_KEYWORD('TRUNCATE'),
                    style.SQL_KEYWORD('TABLE'),
                    style.SQL_FIELD(self.quote_name(table)),
                ) for table in truncated_tables
            ] + [
                "%s %s %s %s %s %s;" % (
                    style.SQL_KEYWORD('ALTER'),
                    style.SQL_KEYWORD('TABLE'),
                    style.SQL_FIELD(self.quote_name(table)),
                    style.SQL_KEYWORD('ENABLE'),
                    style.SQL_KEYWORD('CONSTRAINT'),
                    style.SQL_FIELD(self.quote_name(constraint)),
                ) for table, constraint in constraints
            ]
            # Since we've just deleted all the rows, running our sequence
            # ALTER code will reset the sequence to 0.
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
            return sql
        else:
            return []

    def sequence_reset_by_name_sql(self, style, sequences):
        sql = []
        for sequence_info in sequences:
            sequence_name = self._get_sequence_name(sequence_info['table'])
            table_name = self.quote_name(sequence_info['table'])
            column_name = self.quote_name(sequence_info['column'] or 'id')
            query = self._sequence_reset_sql % {
                'sequence': sequence_name,
                'table': table_name,
                'column': column_name,
            }
            sql.append(query)
        return sql

    def sequence_reset_sql(self, style, model_list):
        from django.db import models
        output = []
        query = self._sequence_reset_sql
        for model in model_list:
            for f in model._meta.local_fields:
                if isinstance(f, models.AutoField):
                    table_name = self.quote_name(model._meta.db_table)
                    sequence_name = self._get_sequence_name(model._meta.db_table)
                    column_name = self.quote_name(f.column)
                    output.append(query % {'sequence': sequence_name,
                                           'table': table_name,
                                           'column': column_name})
                    # Only one AutoField is allowed per model, so don't
                    # continue to loop
                    break
            for f in model._meta.many_to_many:
                if not f.remote_field.through:
                    table_name = self.quote_name(f.m2m_db_table())
                    sequence_name = self._get_sequence_name(f.m2m_db_table())
                    column_name = self.quote_name('id')
                    output.append(query % {'sequence': sequence_name,
                                           'table': table_name,
                                           'column': column_name})
        return output

    def start_transaction_sql(self):
        return ''

    def tablespace_sql(self, tablespace, inline=False):
        if inline:
            return "USING INDEX TABLESPACE %s" % self.quote_name(tablespace)
        else:
            return "TABLESPACE %s" % self.quote_name(tablespace)

    def adapt_datefield_value(self, value):
        """
        Transform a date value to an object compatible with what is expected
        by the backend driver for date columns.
        The default implementation transforms the date to text, but that is not
        necessary for Oracle.
        """
        return value

    def adapt_datetimefield_value(self, value):
        """
        Transform a datetime value to an object compatible with what is expected
        by the backend driver for datetime columns.

        If naive datetime is passed assumes that is in UTC. Normally Django
        models.DateTimeField makes sure that if USE_TZ is True passed datetime
        is timezone aware.
        """

        if value is None:
            return None

        # Expression values are adapted by the database.
        if hasattr(value, 'resolve_expression'):
            return value

        # cx_Oracle doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = timezone.make_naive(value, self.connection.timezone)
            else:
                raise ValueError("Oracle backend does not support timezone-aware datetimes when USE_TZ is False.")

        return Oracle_datetime.from_datetime(value)

    def adapt_timefield_value(self, value):
        if value is None:
            return None

        # Expression values are adapted by the database.
        if hasattr(value, 'resolve_expression'):
            return value

        if isinstance(value, six.string_types):
            return datetime.datetime.strptime(value, '%H:%M:%S')

        # Oracle doesn't support tz-aware times
        if timezone.is_aware(value):
            raise ValueError("Oracle backend does not support timezone-aware times.")

        return Oracle_datetime(1900, 1, 1, value.hour, value.minute,
                               value.second, value.microsecond)

    def combine_expression(self, connector, sub_expressions):
        lhs, rhs = sub_expressions
        if connector == '%%':
            return 'MOD(%s)' % ','.join(sub_expressions)
        elif connector == '&':
            return 'BITAND(%s)' % ','.join(sub_expressions)
        elif connector == '|':
            return 'BITAND(-%(lhs)s-1,%(rhs)s)+%(lhs)s' % {'lhs': lhs, 'rhs': rhs}
        elif connector == '<<':
            return '(%(lhs)s * POWER(2, %(rhs)s))' % {'lhs': lhs, 'rhs': rhs}
        elif connector == '>>':
            return 'FLOOR(%(lhs)s / POWER(2, %(rhs)s))' % {'lhs': lhs, 'rhs': rhs}
        elif connector == '^':
            return 'POWER(%s)' % ','.join(sub_expressions)
        return super(DatabaseOperations, self).combine_expression(connector, sub_expressions)

    def _get_sequence_name(self, table):
        name_length = self.max_name_length() - 3
        sequence_name = '%s_SQ' % strip_quotes(table)
        return truncate_name(sequence_name, name_length).upper()

    def _get_trigger_name(self, table):
        name_length = self.max_name_length() - 3
        trigger_name = '%s_TR' % strip_quotes(table)
        return truncate_name(trigger_name, name_length).upper()

    def bulk_insert_sql(self, fields, placeholder_rows):
        return " UNION ALL ".join(
            "SELECT %s FROM DUAL" % ", ".join(row)
            for row in placeholder_rows
        )

    def subtract_temporals(self, internal_type, lhs, rhs):
        if internal_type == 'DateField':
            lhs_sql, lhs_params = lhs
            rhs_sql, rhs_params = rhs
            return "NUMTODSINTERVAL(%s - %s, 'DAY')" % (lhs_sql, rhs_sql), lhs_params + rhs_params
        return super(DatabaseOperations, self).subtract_temporals(internal_type, lhs, rhs)
