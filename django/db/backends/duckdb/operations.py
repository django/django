"""
Database operations for DuckDB backend.
"""

import datetime
import decimal
import uuid
from functools import cached_property

from django.conf import settings
from django.db import DatabaseError, NotSupportedError, models
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.models.constants import OnConflict
from django.db.models.expressions import Col
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime, parse_time


class DatabaseOperations(BaseDatabaseOperations):
    cast_char_field_without_max_length = "VARCHAR"
    cast_data_types = {
        "DateField": "VARCHAR",
        "DateTimeField": "VARCHAR",
    }
    explain_prefix = "EXPLAIN"

    def date_extract_sql(self, lookup_type, sql, params):
        return f"EXTRACT({lookup_type.lower()} FROM {sql})", params

    def date_trunc_sql(self, lookup_type, sql, params, tzname=None):
        return f"DATE_TRUNC({lookup_type.lower()}, {sql})", (lookup_type.lower(), *params)

    def time_trunc_sql(self, lookup_type, sql, params, tzname=None):
        return f"TIME_TRUNC({lookup_type.lower()}, {sql})", (lookup_type.lower(), *params)

    def datetime_trunc_sql(self, lookup_type, sql, params, tzname=None):
        return f"TIMESTAMP_TRUNC({lookup_type.lower()}, {sql})", (lookup_type.lower(), *params)

    def pk_default_value(self):
        return "NULL"

    def last_executed_query(self, cursor, sql, params):
        if params:
            if isinstance(params, (list, tuple)):
                params = tuple(repr(p) for p in params)
                return sql % params
            else:
                values = tuple(repr(v) for v in params.values())
                params = dict(zip(params, values))
                return sql % params
        return sql

    def quote_name(self, name):
        if name.startswith('"') and name.endswith('"'):
            return name
        return '"%s"' % name

    def no_limit_value(self):
        return ""

    def sql_flush(self, style, tables, *, reset_sequences=False, allow_cascade=False):
        sql = [
            "%s %s %s;"
            % (
                style.SQL_KEYWORD("DELETE"),
                style.SQL_KEYWORD("FROM"),
                style.SQL_FIELD(self.quote_name(table)),
            )
            for table in tables
        ]
        if reset_sequences and tables:
            sql.extend(self.sequence_reset_by_name_sql(style, [{"table": t} for t in tables]))
        return sql

    def sequence_reset_by_name_sql(self, style, sequences):
        # DuckDB doesn't have sequences
        return []

    def adapt_datetimefield_value(self, value):
        if value is None:
            return None
        if timezone.is_aware(value):
            if settings.USE_TZ:
                value = timezone.make_naive(value, self.connection.timezone)
            else:
                raise ValueError(
                    "DuckDB backend does not support timezone-aware datetimes when "
                    "USE_TZ is False."
                )
        return str(value)

    def adapt_timefield_value(self, value):
        if value is None:
            return None
        if timezone.is_aware(value):
            raise ValueError("DuckDB backend does not support timezone-aware times.")
        return str(value)

    def get_db_converters(self, expression):
        converters = super().get_db_converters(expression)
        internal_type = expression.output_field.get_internal_type()
        if internal_type == "DateTimeField":
            converters.append(self.convert_datetimefield_value)
        elif internal_type == "DateField":
            converters.append(self.convert_datefield_value)
        elif internal_type == "TimeField":
            converters.append(self.convert_timefield_value)
        elif internal_type == "DecimalField":
            converters.append(self.get_decimalfield_converter(expression))
        elif internal_type == "UUIDField":
            converters.append(self.convert_uuidfield_value)
        elif internal_type == "BooleanField":
            converters.append(self.convert_booleanfield_value)
        return converters

    def convert_datetimefield_value(self, value, expression, connection):
        if value is not None:
            if not isinstance(value, datetime.datetime):
                value = parse_datetime(value)
            if settings.USE_TZ and not timezone.is_aware(value):
                value = timezone.make_aware(value, self.connection.timezone)
        return value

    def convert_datefield_value(self, value, expression, connection):
        if value is not None:
            if not isinstance(value, datetime.date):
                value = parse_date(value)
        return value

    def convert_timefield_value(self, value, expression, connection):
        if value is not None:
            if not isinstance(value, datetime.time):
                value = parse_time(value)
        return value

    @staticmethod
    def _create_decimal(value):
        if isinstance(value, (int, str)):
            return decimal.Decimal(value)
        return decimal.Context(prec=15).create_decimal_from_float(value)

    def get_decimalfield_converter(self, expression):
        if (
            isinstance(expression, Col)
            and expression.output_field.decimal_places is not None
        ):
            quantize_value = decimal.Decimal(1).scaleb(
                -expression.output_field.decimal_places
            )

            def converter(value, expression, connection):
                if value is not None:
                    return self._create_decimal(value).quantize(
                        quantize_value, context=expression.output_field.context
                    )

        else:

            def converter(value, expression, connection):
                if value is not None:
                    return self._create_decimal(value)

        return converter

    def convert_uuidfield_value(self, value, expression, connection):
        if value is not None:
            value = uuid.UUID(value)
        return value

    def convert_booleanfield_value(self, value, expression, connection):
        return bool(value) if value in (1, 0) else value

    def combine_expression(self, connector, sub_expressions):
        if connector == "^":
            return "POWER(%s)" % ",".join(sub_expressions)
        elif connector == "#":
            return "BITXOR(%s)" % ",".join(sub_expressions)
        return super().combine_expression(connector, sub_expressions)

    def combine_duration_expression(self, connector, sub_expressions):
        if connector not in ["+", "-", "*", "/"]:
            raise DatabaseError("Invalid connector for timedelta: %s." % connector)
        return super().combine_duration_expression(connector, sub_expressions)

    def integer_field_range(self, internal_type):
        if internal_type in [
            "PositiveBigIntegerField",
            "PositiveIntegerField",
            "PositiveSmallIntegerField",
        ]:
            return (0, 9223372036854775807)
        return (-9223372036854775808, 9223372036854775807)

    def insert_statement(self, on_conflict=None):
        if on_conflict == OnConflict.IGNORE:
            return "INSERT OR IGNORE INTO"
        return super().insert_statement(on_conflict=on_conflict)

    def on_conflict_suffix_sql(self, fields, on_conflict, update_fields, unique_fields):
        if (
            on_conflict == OnConflict.UPDATE
            and self.connection.features.supports_update_conflicts_with_target
        ):
            return "ON CONFLICT(%s) DO UPDATE SET %s" % (
                ", ".join(map(self.quote_name, unique_fields)),
                ", ".join(
                    [
                        f"{field} = EXCLUDED.{field}"
                        for field in map(self.quote_name, update_fields)
                    ]
                ),
            )
        return super().on_conflict_suffix_sql(
            fields,
            on_conflict,
            update_fields,
            unique_fields,
        )
