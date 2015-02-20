from __future__ import unicode_literals

import datetime
import re
import uuid

from django.conf import settings
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.backends.utils import truncate_name
from django.utils import six, timezone
from django.utils.encoding import force_bytes, force_text

from .base import Database
from .utils import InsertIdVar, Oracle_datetime, convert_unicode


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

    def autoinc_sql(self, table, column):
        # To simulate auto-incrementing primary keys in Oracle, we have to
        # create a sequence and a trigger.
        sq_name = self._get_sequence_name(table)
        tr_name = self._get_trigger_name(table)
        tbl_name = self.quote_name(table)
        col_name = self.quote_name(column)
        sequence_sql = """
DECLARE
    i INTEGER;
BEGIN
    SELECT COUNT(*) INTO i FROM USER_CATALOG
        WHERE TABLE_NAME = '%(sq_name)s' AND TABLE_TYPE = 'SEQUENCE';
    IF i = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE "%(sq_name)s"';
    END IF;
END;
/""" % locals()
        trigger_sql = """
CREATE OR REPLACE TRIGGER "%(tr_name)s"
BEFORE INSERT ON %(tbl_name)s
FOR EACH ROW
WHEN (new.%(col_name)s IS NULL)
    BEGIN
        SELECT "%(sq_name)s".nextval
        INTO :new.%(col_name)s FROM dual;
    END;
/""" % locals()
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
        else:
            # http://docs.oracle.com/cd/B19306_01/server.102/b14200/functions050.htm
            return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)

    def date_interval_sql(self, timedelta):
        """
        Implements the interval functionality for expressions
        format for Oracle:
        INTERVAL '3 00:03:20.000000' DAY(1) TO SECOND(6)
        """
        minutes, seconds = divmod(timedelta.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days = str(timedelta.days)
        day_precision = len(days)
        fmt = "INTERVAL '%s %02d:%02d:%02d.%06d' DAY(%d) TO SECOND(6)"
        return fmt % (days, hours, minutes, seconds, timedelta.microseconds,
                day_precision), []

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
        if not self._tzname_re.match(tzname):
            raise ValueError("Invalid time zone name: %s" % tzname)
        # Convert from UTC to local time, returning TIMESTAMP WITH TIME ZONE.
        result = "(FROM_TZ(%s, '0:00') AT TIME ZONE '%s')" % (field_name, tzname)
        # Extracting from a TIMESTAMP WITH TIME ZONE ignore the time zone.
        # Convert to a DATETIME, which is called DATE by Oracle. There's no
        # built-in function to do that; the easiest is to go through a string.
        result = "TO_CHAR(%s, 'YYYY-MM-DD HH24:MI:SS')" % result
        result = "TO_DATE(%s, 'YYYY-MM-DD HH24:MI:SS')" % result
        # Re-convert to a TIMESTAMP because EXTRACT only handles the date part
        # on DATE values, even though they actually store the time part.
        return "CAST(%s AS TIMESTAMP)" % result

    def datetime_extract_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
            field_name = self._convert_field_to_tz(field_name, tzname)
        if lookup_type == 'week_day':
            # TO_CHAR(field, 'D') returns an integer from 1-7, where 1=Sunday.
            sql = "TO_CHAR(%s, 'D')" % field_name
        else:
            # http://docs.oracle.com/cd/B19306_01/server.102/b14200/functions050.htm
            sql = "EXTRACT(%s FROM %s)" % (lookup_type.upper(), field_name)
        return sql, []

    def datetime_trunc_sql(self, lookup_type, field_name, tzname):
        if settings.USE_TZ:
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
            sql = field_name    # Cast to DATE removes sub-second precision.
        return sql, []

    def get_db_converters(self, expression):
        converters = super(DatabaseOperations, self).get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type == 'TextField':
            converters.append(self.convert_textfield_value)
        elif internal_type == 'BinaryField':
            converters.append(self.convert_binaryfield_value)
        elif internal_type in ['BooleanField', 'NullBooleanField']:
            converters.append(self.convert_booleanfield_value)
        elif internal_type == 'DateField':
            converters.append(self.convert_datefield_value)
        elif internal_type == 'TimeField':
            converters.append(self.convert_timefield_value)
        elif internal_type == 'UUIDField':
            converters.append(self.convert_uuidfield_value)
        converters.append(self.convert_empty_values)
        return converters

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

    def convert_textfield_value(self, value, expression, connection, context):
        if isinstance(value, Database.LOB):
            value = force_text(value.read())
        return value

    def convert_binaryfield_value(self, value, expression, connection, context):
        if isinstance(value, Database.LOB):
            value = force_bytes(value.read())
        return value

    def convert_booleanfield_value(self, value, expression, connection, context):
        if value in (1, 0):
            value = bool(value)
        return value

    # cx_Oracle always returns datetime.datetime objects for
    # DATE and TIMESTAMP columns, but Django wants to see a
    # python datetime.date, .time, or .datetime.
    def convert_datefield_value(self, value, expression, connection, context):
        if isinstance(value, Database.Timestamp):
            return value.date()

    def convert_timefield_value(self, value, expression, connection, context):
        if isinstance(value, Database.Timestamp):
            value = value.time()
        return value

    def convert_uuidfield_value(self, value, expression, connection, context):
        if value is not None:
            value = uuid.UUID(value)
        return value

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def drop_sequence_sql(self, table):
        return "DROP SEQUENCE %s;" % self.quote_name(self._get_sequence_name(table))

    def fetch_returned_insert_id(self, cursor):
        return int(cursor._insert_id_var.getvalue())

    def field_cast_sql(self, db_type, internal_type):
        if db_type and db_type.endswith('LOB'):
            return "DBMS_LOB.SUBSTR(%s)"
        else:
            return "%s"

    def last_executed_query(self, cursor, sql, params):
        # http://cx-oracle.sourceforge.net/html/cursor.html#Cursor.statement
        # The DB API definition does not define this attribute.
        statement = cursor.statement
        if statement and six.PY2 and not isinstance(statement, unicode):
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
        return convert_unicode("SAVEPOINT " + self.quote_name(sid))

    def savepoint_rollback_sql(self, sid):
        return convert_unicode("ROLLBACK TO SAVEPOINT " + self.quote_name(sid))

    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        # Return a list of 'TRUNCATE x;', 'TRUNCATE y;',
        # 'TRUNCATE z;'... style SQL statements
        if tables:
            # Oracle does support TRUNCATE, but it seems to get us into
            # FK referential trouble, whereas DELETE FROM table works.
            sql = ['%s %s %s;' % (
                style.SQL_KEYWORD('DELETE'),
                style.SQL_KEYWORD('FROM'),
                style.SQL_FIELD(self.quote_name(table))
            ) for table in tables]
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
                if not f.rel.through:
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

    def value_to_db_date(self, value):
        """
        Transform a date value to an object compatible with what is expected
        by the backend driver for date columns.
        The default implementation transforms the date to text, but that is not
        necessary for Oracle.
        """
        return value

    def value_to_db_datetime(self, value):
        """
        Transform a datetime value to an object compatible with what is expected
        by the backend driver for datetime columns.

        If naive datetime is passed assumes that is in UTC. Normally Django
        models.DateTimeField makes sure that if USE_TZ is True passed datetime
        is timezone aware.
        """

        if value is None:
            return None

        # cx_Oracle doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("Oracle backend does not support timezone-aware datetimes when USE_TZ is False.")

        return Oracle_datetime.from_datetime(value)

    def value_to_db_time(self, value):
        if value is None:
            return None

        if isinstance(value, six.string_types):
            return datetime.datetime.strptime(value, '%H:%M:%S')

        # Oracle doesn't support tz-aware times
        if timezone.is_aware(value):
            raise ValueError("Oracle backend does not support timezone-aware times.")

        return Oracle_datetime(1900, 1, 1, value.hour, value.minute,
                               value.second, value.microsecond)

    def year_lookup_bounds_for_date_field(self, value):
        # Create bounds as real date values
        first = datetime.date(value, 1, 1)
        last = datetime.date(value, 12, 31)
        return [first, last]

    def year_lookup_bounds_for_datetime_field(self, value):
        # cx_Oracle doesn't support tz-aware datetimes
        bounds = super(DatabaseOperations, self).year_lookup_bounds_for_datetime_field(value)
        if settings.USE_TZ:
            bounds = [b.astimezone(timezone.utc) for b in bounds]
        return [Oracle_datetime.from_datetime(b) for b in bounds]

    def combine_expression(self, connector, sub_expressions):
        "Oracle requires special cases for %% and & operators in query expressions"
        if connector == '%%':
            return 'MOD(%s)' % ','.join(sub_expressions)
        elif connector == '&':
            return 'BITAND(%s)' % ','.join(sub_expressions)
        elif connector == '|':
            raise NotImplementedError("Bit-wise or is not supported in Oracle.")
        elif connector == '^':
            return 'POWER(%s)' % ','.join(sub_expressions)
        return super(DatabaseOperations, self).combine_expression(connector, sub_expressions)

    def _get_sequence_name(self, table):
        name_length = self.max_name_length() - 3
        return '%s_SQ' % truncate_name(table, name_length).upper()

    def _get_trigger_name(self, table):
        name_length = self.max_name_length() - 3
        return '%s_TR' % truncate_name(table, name_length).upper()

    def bulk_insert_sql(self, fields, num_values):
        items_sql = "SELECT %s FROM DUAL" % ", ".join(["%s"] * len(fields))
        return " UNION ALL ".join([items_sql] * num_values)
