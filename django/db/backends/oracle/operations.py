import datetime
import uuid
from functools import lru_cache

from django.conf import settings
from django.db import DatabaseError, NotSupportedError
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.backends.utils import split_tzname_delta, strip_quotes, truncate_name
from django.db.models import AutoField, Exists, ExpressionWrapper, Lookup
from django.db.models.expressions import RawSQL
from django.db.models.sql.where import WhereNode
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.functional import cached_property
from django.utils.regex_helper import _lazy_re_compile

from .base import Database
from .utils import BulkInsertMapper, InsertVar, Oracle_datetime


class DatabaseOperations(BaseDatabaseOperations):
    # Oracle uses NUMBER(5), NUMBER(11), and NUMBER(19) for integer fields.
    # SmallIntegerField uses NUMBER(11) instead of NUMBER(5), which is used by
    # SmallAutoField, to preserve backward compatibility.
    integer_field_ranges = {
        "SmallIntegerField": (-99999999999, 99999999999),
        "IntegerField": (-99999999999, 99999999999),
        "BigIntegerField": (-9999999999999999999, 9999999999999999999),
        "PositiveBigIntegerField": (0, 9999999999999999999),
        "PositiveSmallIntegerField": (0, 99999999999),
        "PositiveIntegerField": (0, 99999999999),
        "SmallAutoField": (-99999, 99999),
        "AutoField": (-99999999999, 99999999999),
        "BigAutoField": (-9999999999999999999, 9999999999999999999),
    }
    set_operators = {**BaseDatabaseOperations.set_operators, "difference": "MINUS"}

    # TODO: colorize this SQL code with style.SQL_KEYWORD(), etc.
    _sequence_reset_sql = """
DECLARE
    table_value integer;
    seq_value integer;
    seq_name user_tab_identity_cols.sequence_name%%TYPE;
BEGIN
    BEGIN
        SELECT sequence_name INTO seq_name FROM user_tab_identity_cols
        WHERE  table_name = '%(table_name)s' AND
               column_name = '%(column_name)s';
        EXCEPTION WHEN NO_DATA_FOUND THEN
            seq_name := '%(no_autofield_sequence_name)s';
    END;

    SELECT NVL(MAX(%(column)s), 0) INTO table_value FROM %(table)s;
    SELECT NVL(last_number - cache_size, 0) INTO seq_value FROM user_sequences
           WHERE sequence_name = seq_name;
    WHILE table_value > seq_value LOOP
        EXECUTE IMMEDIATE 'SELECT "'||seq_name||'".nextval%(suffix)s'
        INTO seq_value;
    END LOOP;
END;
/"""

    # Oracle doesn't support string without precision; use the max string size.
    cast_char_field_without_max_length = "NVARCHAR2(2000)"
    cast_data_types = {
        "AutoField": "NUMBER(11)",
        "BigAutoField": "NUMBER(19)",
        "SmallAutoField": "NUMBER(5)",
        "TextField": cast_char_field_without_max_length,
    }

    def cache_key_culling_sql(self):
        cache_key = self.quote_name("cache_key")
        return (
            f"SELECT {cache_key} "
            f"FROM %s "
            f"ORDER BY {cache_key} OFFSET %%s ROWS FETCH FIRST 1 ROWS ONLY"
        )

    # EXTRACT format cannot be passed in parameters.
    _extract_format_re = _lazy_re_compile(r"[A-Z_]+")

    def date_extract_sql(self, lookup_type, sql, params):
        extract_sql = f"TO_CHAR({sql}, %s)"
        extract_param = None
        if lookup_type == "week_day":
            # TO_CHAR(field, 'D') returns an integer from 1-7, where 1=Sunday.
            extract_param = "D"
        elif lookup_type == "iso_week_day":
            extract_sql = f"TO_CHAR({sql} - 1, %s)"
            extract_param = "D"
        elif lookup_type == "week":
            # IW = ISO week number
            extract_param = "IW"
        elif lookup_type == "quarter":
            extract_param = "Q"
        elif lookup_type == "iso_year":
            extract_param = "IYYY"
        else:
            lookup_type = lookup_type.upper()
            if not self._extract_format_re.fullmatch(lookup_type):
                raise ValueError(f"Invalid loookup type: {lookup_type!r}")
            # https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/EXTRACT-datetime.html
            return f"EXTRACT({lookup_type} FROM {sql})", params
        return extract_sql, (*params, extract_param)

    def date_trunc_sql(self, lookup_type, sql, params, tzname=None):
        sql, params = self._convert_sql_to_tz(sql, params, tzname)
        # https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/ROUND-and-TRUNC-Date-Functions.html
        trunc_param = None
        if lookup_type in ("year", "month"):
            trunc_param = lookup_type.upper()
        elif lookup_type == "quarter":
            trunc_param = "Q"
        elif lookup_type == "week":
            trunc_param = "IW"
        else:
            return f"TRUNC({sql})", params
        return f"TRUNC({sql}, %s)", (*params, trunc_param)

    # Oracle crashes with "ORA-03113: end-of-file on communication channel"
    # if the time zone name is passed in parameter. Use interpolation instead.
    # https://groups.google.com/forum/#!msg/django-developers/zwQju7hbG78/9l934yelwfsJ
    # This regexp matches all time zone names from the zoneinfo database.
    _tzname_re = _lazy_re_compile(r"^[\w/:+-]+$")

    def _prepare_tzname_delta(self, tzname):
        tzname, sign, offset = split_tzname_delta(tzname)
        return f"{sign}{offset}" if offset else tzname

    def _convert_sql_to_tz(self, sql, params, tzname):
        if not (settings.USE_TZ and tzname):
            return sql, params
        if not self._tzname_re.match(tzname):
            raise ValueError("Invalid time zone name: %s" % tzname)
        # Convert from connection timezone to the local time, returning
        # TIMESTAMP WITH TIME ZONE and cast it back to TIMESTAMP to strip the
        # TIME ZONE details.
        if self.connection.timezone_name != tzname:
            from_timezone_name = self.connection.timezone_name
            to_timezone_name = self._prepare_tzname_delta(tzname)
            return (
                f"CAST((FROM_TZ({sql}, '{from_timezone_name}') AT TIME ZONE "
                f"'{to_timezone_name}') AS TIMESTAMP)",
                params,
            )
        return sql, params

    def datetime_cast_date_sql(self, sql, params, tzname):
        sql, params = self._convert_sql_to_tz(sql, params, tzname)
        return f"TRUNC({sql})", params

    def datetime_cast_time_sql(self, sql, params, tzname):
        # Since `TimeField` values are stored as TIMESTAMP change to the
        # default date and convert the field to the specified timezone.
        sql, params = self._convert_sql_to_tz(sql, params, tzname)
        convert_datetime_sql = (
            f"TO_TIMESTAMP(CONCAT('1900-01-01 ', TO_CHAR({sql}, 'HH24:MI:SS.FF')), "
            f"'YYYY-MM-DD HH24:MI:SS.FF')"
        )
        return (
            f"CASE WHEN {sql} IS NOT NULL THEN {convert_datetime_sql} ELSE NULL END",
            (*params, *params),
        )

    def datetime_extract_sql(self, lookup_type, sql, params, tzname):
        sql, params = self._convert_sql_to_tz(sql, params, tzname)
        if lookup_type == "second":
            # Truncate fractional seconds.
            return f"FLOOR(EXTRACT(SECOND FROM {sql}))", params
        return self.date_extract_sql(lookup_type, sql, params)

    def datetime_trunc_sql(self, lookup_type, sql, params, tzname):
        sql, params = self._convert_sql_to_tz(sql, params, tzname)
        # https://docs.oracle.com/en/database/oracle/oracle-database/21/sqlrf/ROUND-and-TRUNC-Date-Functions.html
        trunc_param = None
        if lookup_type in ("year", "month"):
            trunc_param = lookup_type.upper()
        elif lookup_type == "quarter":
            trunc_param = "Q"
        elif lookup_type == "week":
            trunc_param = "IW"
        elif lookup_type == "hour":
            trunc_param = "HH24"
        elif lookup_type == "minute":
            trunc_param = "MI"
        elif lookup_type == "day":
            return f"TRUNC({sql})", params
        else:
            # Cast to DATE removes sub-second precision.
            return f"CAST({sql} AS DATE)", params
        return f"TRUNC({sql}, %s)", (*params, trunc_param)

    def time_extract_sql(self, lookup_type, sql, params):
        if lookup_type == "second":
            # Truncate fractional seconds.
            return f"FLOOR(EXTRACT(SECOND FROM {sql}))", params
        return self.date_extract_sql(lookup_type, sql, params)

    def time_trunc_sql(self, lookup_type, sql, params, tzname=None):
        # The implementation is similar to `datetime_trunc_sql` as both
        # `DateTimeField` and `TimeField` are stored as TIMESTAMP where
        # the date part of the later is ignored.
        sql, params = self._convert_sql_to_tz(sql, params, tzname)
        trunc_param = None
        if lookup_type == "hour":
            trunc_param = "HH24"
        elif lookup_type == "minute":
            trunc_param = "MI"
        elif lookup_type == "second":
            # Cast to DATE removes sub-second precision.
            return f"CAST({sql} AS DATE)", params
        return f"TRUNC({sql}, %s)", (*params, trunc_param)

    def get_db_converters(self, expression):
        converters = super().get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type in ["JSONField", "TextField"]:
            converters.append(self.convert_textfield_value)
        elif internal_type == "BinaryField":
            converters.append(self.convert_binaryfield_value)
        elif internal_type == "BooleanField":
            converters.append(self.convert_booleanfield_value)
        elif internal_type == "DateTimeField":
            if settings.USE_TZ:
                converters.append(self.convert_datetimefield_value)
        elif internal_type == "DateField":
            converters.append(self.convert_datefield_value)
        elif internal_type == "TimeField":
            converters.append(self.convert_timefield_value)
        elif internal_type == "UUIDField":
            converters.append(self.convert_uuidfield_value)
        # Oracle stores empty strings as null. If the field accepts the empty
        # string, undo this to adhere to the Django convention of using
        # the empty string instead of null.
        if expression.output_field.empty_strings_allowed:
            converters.append(
                self.convert_empty_bytes
                if internal_type == "BinaryField"
                else self.convert_empty_string
            )
        return converters

    def convert_textfield_value(self, value, expression, connection):
        if isinstance(value, Database.LOB):
            value = value.read()
        return value

    def convert_binaryfield_value(self, value, expression, connection):
        if isinstance(value, Database.LOB):
            value = force_bytes(value.read())
        return value

    def convert_booleanfield_value(self, value, expression, connection):
        if value in (0, 1):
            value = bool(value)
        return value

    # oracledb always returns datetime.datetime objects for
    # DATE and TIMESTAMP columns, but Django wants to see a
    # python datetime.date, .time, or .datetime.

    def convert_datetimefield_value(self, value, expression, connection):
        if value is not None:
            value = timezone.make_aware(value, self.connection.timezone)
        return value

    def convert_datefield_value(self, value, expression, connection):
        if isinstance(value, Database.Timestamp):
            value = value.date()
        return value

    def convert_timefield_value(self, value, expression, connection):
        if isinstance(value, Database.Timestamp):
            value = value.time()
        return value

    def convert_uuidfield_value(self, value, expression, connection):
        if value is not None:
            value = uuid.UUID(value)
        return value

    @staticmethod
    def convert_empty_string(value, expression, connection):
        return "" if value is None else value

    @staticmethod
    def convert_empty_bytes(value, expression, connection):
        return b"" if value is None else value

    def deferrable_sql(self):
        return " DEFERRABLE INITIALLY DEFERRED"

    def fetch_returned_insert_columns(self, cursor, returning_params):
        columns = []
        for param in returning_params:
            value = param.get_value()
            # Can be removed when cx_Oracle is no longer supported and
            # python-oracle 2.1.2 becomes the minimum supported version.
            if value == []:
                raise DatabaseError(
                    "The database did not return a new row id. Probably "
                    '"ORA-1403: no data found" was raised internally but was '
                    "hidden by the Oracle OCI library (see "
                    "https://code.djangoproject.com/ticket/28859)."
                )
            columns.append(value[0])
        return tuple(columns)

    def no_limit_value(self):
        return None

    def limit_offset_sql(self, low_mark, high_mark):
        fetch, offset = self._get_limit_offset_params(low_mark, high_mark)
        return " ".join(
            sql
            for sql in (
                ("OFFSET %d ROWS" % offset) if offset else None,
                ("FETCH FIRST %d ROWS ONLY" % fetch) if fetch else None,
            )
            if sql
        )

    def last_executed_query(self, cursor, sql, params):
        # https://python-oracledb.readthedocs.io/en/latest/api_manual/cursor.html#Cursor.statement
        # The DB API definition does not define this attribute.
        statement = cursor.statement
        # Unlike Psycopg's `query` and MySQLdb`'s `_executed`, oracledb's
        # `statement` doesn't contain the query parameters. Substitute
        # parameters manually.
        if params:
            if isinstance(params, (tuple, list)):
                params = {
                    f":arg{i}": param for i, param in enumerate(dict.fromkeys(params))
                }
            elif isinstance(params, dict):
                params = {f":{key}": val for (key, val) in params.items()}
            for key in sorted(params, key=len, reverse=True):
                statement = statement.replace(
                    key, force_str(params[key], errors="replace")
                )
        return statement

    def last_insert_id(self, cursor, table_name, pk_name):
        sq_name = self._get_sequence_name(cursor, strip_quotes(table_name), pk_name)
        cursor.execute('"%s".currval' % sq_name)
        return cursor.fetchone()[0]

    def lookup_cast(self, lookup_type, internal_type=None):
        if lookup_type in ("iexact", "icontains", "istartswith", "iendswith"):
            return "UPPER(%s)"
        if lookup_type != "isnull" and internal_type in (
            "BinaryField",
            "TextField",
        ):
            return "DBMS_LOB.SUBSTR(%s)"
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
            return ""
        return value.read()

    def quote_name(self, name):
        # SQL92 requires delimited (quoted) names to be case-sensitive.  When
        # not quoted, Oracle has case-insensitive behavior for identifiers, but
        # always defaults to uppercase.
        # We simplify things by making Oracle identifiers always uppercase.
        if not name.startswith('"') and not name.endswith('"'):
            name = '"%s"' % truncate_name(name, self.max_name_length())
        # Oracle puts the query text into a (query % args) construct, so % signs
        # in names need to be escaped. The '%%' will be collapsed back to '%' at
        # that stage so we aren't really making the name longer here.
        name = name.replace("%", "%%")
        return name.upper()

    def regex_lookup(self, lookup_type):
        if lookup_type == "regex":
            match_option = "'c'"
        else:
            match_option = "'i'"
        return "REGEXP_LIKE(%%s, %%s, %s)" % match_option

    def return_insert_columns(self, fields):
        if not fields:
            return "", ()
        field_names = []
        params = []
        for field in fields:
            field_names.append(
                "%s.%s"
                % (
                    self.quote_name(field.model._meta.db_table),
                    self.quote_name(field.column),
                )
            )
            params.append(InsertVar(field))
        return "RETURNING %s INTO %s" % (
            ", ".join(field_names),
            ", ".join(["%s"] * len(params)),
        ), tuple(params)

    def __foreign_key_constraints(self, table_name, recursive):
        with self.connection.cursor() as cursor:
            if recursive:
                cursor.execute(
                    """
                    SELECT
                        user_tables.table_name, rcons.constraint_name
                    FROM
                        user_tables
                    JOIN
                        user_constraints cons
                        ON (user_tables.table_name = cons.table_name
                        AND cons.constraint_type = ANY('P', 'U'))
                    LEFT JOIN
                        user_constraints rcons
                        ON (user_tables.table_name = rcons.table_name
                        AND rcons.constraint_type = 'R')
                    START WITH user_tables.table_name = UPPER(%s)
                    CONNECT BY
                        NOCYCLE PRIOR cons.constraint_name = rcons.r_constraint_name
                    GROUP BY
                        user_tables.table_name, rcons.constraint_name
                    HAVING user_tables.table_name != UPPER(%s)
                    ORDER BY MAX(level) DESC
                    """,
                    (table_name, table_name),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        cons.table_name, cons.constraint_name
                    FROM
                        user_constraints cons
                    WHERE
                        cons.constraint_type = 'R'
                        AND cons.table_name = UPPER(%s)
                    """,
                    (table_name,),
                )
            return cursor.fetchall()

    @cached_property
    def _foreign_key_constraints(self):
        # 512 is large enough to fit the ~330 tables (as of this writing) in
        # Django's test suite.
        return lru_cache(maxsize=512)(self.__foreign_key_constraints)

    def sql_flush(self, style, tables, *, reset_sequences=False, allow_cascade=False):
        if not tables:
            return []

        truncated_tables = {table.upper() for table in tables}
        constraints = set()
        # Oracle's TRUNCATE CASCADE only works with ON DELETE CASCADE foreign
        # keys which Django doesn't define. Emulate the PostgreSQL behavior
        # which truncates all dependent tables by manually retrieving all
        # foreign key constraints and resolving dependencies.
        for table in tables:
            for foreign_table, constraint in self._foreign_key_constraints(
                table, recursive=allow_cascade
            ):
                if allow_cascade:
                    truncated_tables.add(foreign_table)
                constraints.add((foreign_table, constraint))
        sql = (
            [
                "%s %s %s %s %s %s %s %s;"
                % (
                    style.SQL_KEYWORD("ALTER"),
                    style.SQL_KEYWORD("TABLE"),
                    style.SQL_FIELD(self.quote_name(table)),
                    style.SQL_KEYWORD("DISABLE"),
                    style.SQL_KEYWORD("CONSTRAINT"),
                    style.SQL_FIELD(self.quote_name(constraint)),
                    style.SQL_KEYWORD("KEEP"),
                    style.SQL_KEYWORD("INDEX"),
                )
                for table, constraint in constraints
            ]
            + [
                "%s %s %s;"
                % (
                    style.SQL_KEYWORD("TRUNCATE"),
                    style.SQL_KEYWORD("TABLE"),
                    style.SQL_FIELD(self.quote_name(table)),
                )
                for table in truncated_tables
            ]
            + [
                "%s %s %s %s %s %s;"
                % (
                    style.SQL_KEYWORD("ALTER"),
                    style.SQL_KEYWORD("TABLE"),
                    style.SQL_FIELD(self.quote_name(table)),
                    style.SQL_KEYWORD("ENABLE"),
                    style.SQL_KEYWORD("CONSTRAINT"),
                    style.SQL_FIELD(self.quote_name(constraint)),
                )
                for table, constraint in constraints
            ]
        )
        if reset_sequences:
            sequences = [
                sequence
                for sequence in self.connection.introspection.sequence_list()
                if sequence["table"].upper() in truncated_tables
            ]
            # Since we've just deleted all the rows, running our sequence ALTER
            # code will reset the sequence to 0.
            sql.extend(self.sequence_reset_by_name_sql(style, sequences))
        return sql

    def sequence_reset_by_name_sql(self, style, sequences):
        sql = []
        for sequence_info in sequences:
            no_autofield_sequence_name = self._get_no_autofield_sequence_name(
                sequence_info["table"]
            )
            table = self.quote_name(sequence_info["table"])
            column = self.quote_name(sequence_info["column"] or "id")
            query = self._sequence_reset_sql % {
                "no_autofield_sequence_name": no_autofield_sequence_name,
                "table": table,
                "column": column,
                "table_name": strip_quotes(table),
                "column_name": strip_quotes(column),
                "suffix": self.connection.features.bare_select_suffix,
            }
            sql.append(query)
        return sql

    def sequence_reset_sql(self, style, model_list):
        output = []
        query = self._sequence_reset_sql
        for model in model_list:
            for f in model._meta.local_fields:
                if isinstance(f, AutoField):
                    no_autofield_sequence_name = self._get_no_autofield_sequence_name(
                        model._meta.db_table
                    )
                    table = self.quote_name(model._meta.db_table)
                    column = self.quote_name(f.column)
                    output.append(
                        query
                        % {
                            "no_autofield_sequence_name": no_autofield_sequence_name,
                            "table": table,
                            "column": column,
                            "table_name": strip_quotes(table),
                            "column_name": strip_quotes(column),
                            "suffix": self.connection.features.bare_select_suffix,
                        }
                    )
                    # Only one AutoField is allowed per model, so don't
                    # continue to loop
                    break
        return output

    def start_transaction_sql(self):
        return ""

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

        # oracledb doesn't support tz-aware datetimes
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = timezone.make_naive(value, self.connection.timezone)
            else:
                raise ValueError(
                    "Oracle backend does not support timezone-aware datetimes when "
                    "USE_TZ is False."
                )

        return Oracle_datetime.from_datetime(value)

    def adapt_timefield_value(self, value):
        if value is None:
            return None

        if isinstance(value, str):
            return datetime.datetime.strptime(value, "%H:%M:%S")

        # Oracle doesn't support tz-aware times
        if timezone.is_aware(value):
            raise ValueError("Oracle backend does not support timezone-aware times.")

        return Oracle_datetime(
            1900, 1, 1, value.hour, value.minute, value.second, value.microsecond
        )

    def adapt_decimalfield_value(self, value, max_digits=None, decimal_places=None):
        return value

    def combine_expression(self, connector, sub_expressions):
        lhs, rhs = sub_expressions
        if connector == "%%":
            return "MOD(%s)" % ",".join(sub_expressions)
        elif connector == "&":
            return "BITAND(%s)" % ",".join(sub_expressions)
        elif connector == "|":
            return "BITAND(-%(lhs)s-1,%(rhs)s)+%(lhs)s" % {"lhs": lhs, "rhs": rhs}
        elif connector == "<<":
            return "(%(lhs)s * POWER(2, %(rhs)s))" % {"lhs": lhs, "rhs": rhs}
        elif connector == ">>":
            return "FLOOR(%(lhs)s / POWER(2, %(rhs)s))" % {"lhs": lhs, "rhs": rhs}
        elif connector == "^":
            return "POWER(%s)" % ",".join(sub_expressions)
        elif connector == "#":
            raise NotSupportedError("Bitwise XOR is not supported in Oracle.")
        return super().combine_expression(connector, sub_expressions)

    def _get_no_autofield_sequence_name(self, table):
        """
        Manually created sequence name to keep backward compatibility for
        AutoFields that aren't Oracle identity columns.
        """
        name_length = self.max_name_length() - 3
        return "%s_SQ" % truncate_name(strip_quotes(table), name_length).upper()

    def _get_sequence_name(self, cursor, table, pk_name):
        cursor.execute(
            """
            SELECT sequence_name
            FROM user_tab_identity_cols
            WHERE table_name = UPPER(%s)
            AND column_name = UPPER(%s)""",
            [table, pk_name],
        )
        row = cursor.fetchone()
        return self._get_no_autofield_sequence_name(table) if row is None else row[0]

    def bulk_insert_sql(self, fields, placeholder_rows):
        field_placeholders = [
            BulkInsertMapper.types.get(
                getattr(field, "target_field", field).get_internal_type(), "%s"
            )
            for field in fields
            if field
        ]
        if (
            self.connection.features.supports_bulk_insert_with_multiple_rows
            # A workaround with UNION of SELECTs is required for models without
            # any fields.
            and field_placeholders
        ):
            placeholder_rows_sql = []
            for row in placeholder_rows:
                placeholders_row = (
                    field_placeholder % placeholder
                    for field_placeholder, placeholder in zip(
                        field_placeholders, row, strict=True
                    )
                )
                placeholder_rows_sql.append(placeholders_row)
            return super().bulk_insert_sql(fields, placeholder_rows_sql)
        # Oracle < 23c doesn't support inserting multiple rows in a single
        # statement, use UNION of SELECTs as a workaround.
        query = []
        for row in placeholder_rows:
            select = []
            for i, placeholder in enumerate(row):
                # A model without any fields has fields=[None].
                if fields[i]:
                    placeholder = field_placeholders[i] % placeholder
                # Add columns aliases to the first select to avoid "ORA-00918:
                # column ambiguously defined" when two or more columns in the
                # first select have the same value.
                if not query:
                    placeholder = "%s col_%s" % (placeholder, i)
                select.append(placeholder)
            suffix = self.connection.features.bare_select_suffix
            query.append(f"SELECT %s{suffix}" % ", ".join(select))
        # Bulk insert to tables with Oracle identity columns causes Oracle to
        # add sequence.nextval to it. Sequence.nextval cannot be used with the
        # UNION operator. To prevent incorrect SQL, move UNION to a subquery.
        return "SELECT * FROM (%s)" % " UNION ALL ".join(query)

    def subtract_temporals(self, internal_type, lhs, rhs):
        if internal_type == "DateField":
            lhs_sql, lhs_params = lhs
            rhs_sql, rhs_params = rhs
            params = (*lhs_params, *rhs_params)
            return (
                "NUMTODSINTERVAL(TO_NUMBER(%s - %s), 'DAY')" % (lhs_sql, rhs_sql),
                params,
            )
        return super().subtract_temporals(internal_type, lhs, rhs)

    def bulk_batch_size(self, fields, objs):
        """Oracle restricts the number of parameters in a query."""
        if fields:
            return self.connection.features.max_query_params // len(fields)
        return len(objs)

    def conditional_expression_supported_in_where_clause(self, expression):
        """
        Oracle supports only EXISTS(...) or filters in the WHERE clause, others
        must be compared with True.
        """
        if isinstance(expression, (Exists, Lookup, WhereNode)):
            return True
        if isinstance(expression, ExpressionWrapper) and expression.conditional:
            return self.conditional_expression_supported_in_where_clause(
                expression.expression
            )
        if isinstance(expression, RawSQL) and expression.conditional:
            return True
        return False
