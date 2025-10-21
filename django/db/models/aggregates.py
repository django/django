"""
Classes to represent the definitions of aggregate functions.
"""

from django.core.exceptions import FieldError, FullResultSet
from django.db import NotSupportedError
from django.db.models.expressions import (
    Case,
    ColPairs,
    Func,
    OrderByList,
    Star,
    Value,
    When,
)
from django.db.models.fields import DateField, IntegerField, TextField
from django.db.models.fields.json import JSONField
from django.db.models.functions import Coalesce
from django.db.models.functions.mixins import (
    FixDurationInputMixin,
    NumericOutputFieldMixin,
)
from django.db.models.lookups import IsNull

__all__ = [
    "Aggregate",
    "AnyValue",
    "Avg",
    "Count",
    "Max",
    "Min",
    "StdDev",
    "StringAgg",
    "Sum",
    "Variance",
    "JSONArrayAgg",
]


class AggregateFilter(Func):
    arity = 1
    template = " FILTER (WHERE %(expressions)s)"

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_aggregate_filter_clause:
            raise NotSupportedError(
                "Aggregate filter clauses are not supported on this database backend."
            )
        try:
            return super().as_sql(compiler, connection, **extra_context)
        except FullResultSet:
            return "", ()

    @property
    def condition(self):
        return self.source_expressions[0]

    def __str__(self):
        return self.arg_joiner.join(str(arg) for arg in self.source_expressions)


class AggregateOrderBy(OrderByList):
    template = " ORDER BY %(expressions)s"

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_aggregate_order_by_clause:
            raise NotSupportedError(
                "This database backend does not support specifying an order on "
                "aggregates."
            )

        return super().as_sql(compiler, connection, **extra_context)


class Aggregate(Func):
    template = "%(function)s(%(distinct)s%(expressions)s%(order_by)s)%(filter)s"
    contains_aggregate = True
    name = None
    window_compatible = True
    allow_distinct = False
    allow_order_by = False
    empty_result_set_value = None

    def __init__(
        self,
        *expressions,
        distinct=False,
        filter=None,
        default=None,
        order_by=None,
        **extra,
    ):
        if distinct and not self.allow_distinct:
            raise TypeError("%s does not allow distinct." % self.__class__.__name__)
        if order_by and not self.allow_order_by:
            raise TypeError("%s does not allow order_by." % self.__class__.__name__)
        if default is not None and self.empty_result_set_value is not None:
            raise TypeError(f"{self.__class__.__name__} does not allow default.")

        self.distinct = distinct
        self.filter = None if filter is None else AggregateFilter(filter)
        self.default = default
        self.order_by = AggregateOrderBy.from_param(
            f"{self.__class__.__name__}.order_by", order_by
        )
        super().__init__(*expressions, **extra)

    def get_source_fields(self):
        # Don't consider filter and order by expression as they have nothing
        # to do with the output field resolution.
        return [e._output_field_or_none for e in super().get_source_expressions()]

    def get_source_expressions(self):
        source_expressions = super().get_source_expressions()
        return [*source_expressions, self.filter, self.order_by]

    def set_source_expressions(self, exprs):
        *exprs, self.filter, self.order_by = exprs
        return super().set_source_expressions(exprs)

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        # Aggregates are not allowed in UPDATE queries, so ignore for_save
        c = super().resolve_expression(query, allow_joins, reuse, summarize)
        if summarize:
            # Summarized aggregates cannot refer to summarized aggregates.
            for ref in c.get_refs():
                if query.annotations[ref].is_summary:
                    raise FieldError(
                        f"Cannot compute {c.name}('{ref}'): '{ref}' is an aggregate"
                    )
        elif not self.is_summary:
            # Call Aggregate.get_source_expressions() to avoid
            # returning self.filter and including that in this loop.
            expressions = super(Aggregate, c).get_source_expressions()
            for index, expr in enumerate(expressions):
                if expr.contains_aggregate:
                    before_resolved = self.get_source_expressions()[index]
                    name = (
                        before_resolved.name
                        if hasattr(before_resolved, "name")
                        else repr(before_resolved)
                    )
                    raise FieldError(
                        "Cannot compute %s('%s'): '%s' is an aggregate"
                        % (c.name, name, name)
                    )
        if (default := c.default) is None:
            return c
        if hasattr(default, "resolve_expression"):
            default = default.resolve_expression(query, allow_joins, reuse, summarize)
            if default._output_field_or_none is None:
                default.output_field = c._output_field_or_none
        else:
            default = Value(default, c._output_field_or_none)
        c.default = None  # Reset the default argument before wrapping.
        coalesce = Coalesce(c, default, output_field=c._output_field_or_none)
        coalesce.is_summary = c.is_summary
        return coalesce

    @property
    def default_alias(self):
        expressions = [
            expr for expr in self.get_source_expressions() if expr is not None
        ]
        if len(expressions) == 1 and hasattr(expressions[0], "name"):
            return "%s__%s" % (expressions[0].name, self.name.lower())
        raise TypeError("Complex expressions require an alias")

    def get_group_by_cols(self):
        return []

    def as_sql(self, compiler, connection, **extra_context):
        if (
            self.distinct
            and not connection.features.supports_aggregate_distinct_multiple_argument
            and len(super().get_source_expressions()) > 1
        ):
            raise NotSupportedError(
                f"{self.name} does not support distinct with multiple expressions on "
                f"this database backend."
            )

        distinct_sql = "DISTINCT " if self.distinct else ""
        order_by_sql = ""
        order_by_params = []
        filter_sql = ""
        filter_params = []

        if (order_by := self.order_by) is not None:
            order_by_sql, order_by_params = compiler.compile(order_by)

        if self.filter is not None:
            try:
                filter_sql, filter_params = compiler.compile(self.filter)
            except NotSupportedError:
                # Fallback to a CASE statement on backends that don't support
                # the FILTER clause.
                copy = self.copy()
                copy.filter = None
                source_expressions = copy.get_source_expressions()
                condition = When(self.filter.condition, then=source_expressions[0])
                copy.set_source_expressions([Case(condition)] + source_expressions[1:])
                return copy.as_sql(compiler, connection, **extra_context)

        extra_context.update(
            distinct=distinct_sql,
            filter=filter_sql,
            order_by=order_by_sql,
        )
        sql, params = super().as_sql(compiler, connection, **extra_context)
        return sql, (*params, *order_by_params, *filter_params)

    def _get_repr_options(self):
        options = super()._get_repr_options()
        if self.distinct:
            options["distinct"] = self.distinct
        if self.filter:
            options["filter"] = self.filter
        if self.order_by:
            options["order_by"] = self.order_by
        return options


class AnyValue(Aggregate):
    function = "ANY_VALUE"
    name = "AnyValue"
    arity = 1
    window_compatible = False

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_any_value:
            raise NotSupportedError(
                "ANY_VALUE is not supported on this database backend."
            )
        return super().as_sql(compiler, connection, **extra_context)


class Avg(FixDurationInputMixin, NumericOutputFieldMixin, Aggregate):
    function = "AVG"
    name = "Avg"
    allow_distinct = True
    arity = 1


class Count(Aggregate):
    function = "COUNT"
    name = "Count"
    output_field = IntegerField()
    allow_distinct = True
    empty_result_set_value = 0
    arity = 1
    allows_composite_expressions = True

    def __init__(self, expression, filter=None, **extra):
        if expression == "*":
            expression = Star()
        if isinstance(expression, Star) and filter is not None:
            raise ValueError("Star cannot be used with filter. Please specify a field.")
        super().__init__(expression, filter=filter, **extra)

    def resolve_expression(self, *args, **kwargs):
        result = super().resolve_expression(*args, **kwargs)
        source_expressions = result.get_source_expressions()

        # In case of composite primary keys, count the first column.
        if isinstance(expr := source_expressions[0], ColPairs):
            if self.distinct:
                raise ValueError(
                    "COUNT(DISTINCT) doesn't support composite primary keys"
                )

            source_expressions[0] = expr.get_cols()[0]
            result.set_source_expressions(source_expressions)

        return result


class Max(Aggregate):
    function = "MAX"
    name = "Max"
    arity = 1


class Min(Aggregate):
    function = "MIN"
    name = "Min"
    arity = 1


class StdDev(NumericOutputFieldMixin, Aggregate):
    name = "StdDev"
    arity = 1

    def __init__(self, expression, sample=False, **extra):
        self.function = "STDDEV_SAMP" if sample else "STDDEV_POP"
        super().__init__(expression, **extra)

    def _get_repr_options(self):
        return {**super()._get_repr_options(), "sample": self.function == "STDDEV_SAMP"}


class StringAggDelimiter(Func):
    arity = 1
    template = "%(expressions)s"

    def __init__(self, value):
        self.value = value
        super().__init__(value)

    def as_mysql(self, compiler, connection, **extra_context):
        template = " SEPARATOR %(expressions)s"

        return self.as_sql(
            compiler,
            connection,
            template=template,
            **extra_context,
        )


class StringAgg(Aggregate):
    template = "%(function)s(%(distinct)s%(expressions)s%(order_by)s)%(filter)s"
    function = "STRING_AGG"
    name = "StringAgg"
    allow_distinct = True
    allow_order_by = True
    output_field = TextField()

    def __init__(self, expression, delimiter, **extra):
        self.delimiter = StringAggDelimiter(delimiter)
        super().__init__(expression, self.delimiter, **extra)

    def as_oracle(self, compiler, connection, **extra_context):
        if self.order_by:
            template = (
                "%(function)s(%(distinct)s%(expressions)s) WITHIN GROUP (%(order_by)s)"
                "%(filter)s"
            )
        else:
            template = "%(function)s(%(distinct)s%(expressions)s)%(filter)s"

        return self.as_sql(
            compiler,
            connection,
            function="LISTAGG",
            template=template,
            **extra_context,
        )

    def as_mysql(self, compiler, connection, **extra_context):
        extra_context["function"] = "GROUP_CONCAT"

        template = "%(function)s(%(distinct)s%(expressions)s%(order_by)s%(delimiter)s)"
        extra_context["template"] = template

        c = self.copy()
        # The creation of the delimiter SQL and the ordering of the parameters
        # must be handled explicitly, as MySQL puts the delimiter at the end of
        # the aggregate using the `SEPARATOR` declaration (rather than treating
        # as an expression like other database backends).
        delimiter_params = []
        if c.delimiter:
            delimiter_sql, delimiter_params = compiler.compile(c.delimiter)
            # Drop the delimiter from the source expressions.
            c.source_expressions = c.source_expressions[:-1]
            extra_context["delimiter"] = delimiter_sql

        sql, params = c.as_sql(compiler, connection, **extra_context)

        return sql, (*params, *delimiter_params)

    def as_sqlite(self, compiler, connection, **extra_context):
        if connection.get_database_version() < (3, 44):
            return self.as_sql(
                compiler,
                connection,
                function="GROUP_CONCAT",
                **extra_context,
            )

        return self.as_sql(compiler, connection, **extra_context)


class Sum(FixDurationInputMixin, Aggregate):
    function = "SUM"
    name = "Sum"
    allow_distinct = True
    arity = 1


class Variance(NumericOutputFieldMixin, Aggregate):
    name = "Variance"
    arity = 1

    def __init__(self, expression, sample=False, **extra):
        self.function = "VAR_SAMP" if sample else "VAR_POP"
        super().__init__(expression, **extra)

    def _get_repr_options(self):
        return {**super()._get_repr_options(), "sample": self.function == "VAR_SAMP"}


class JSONArrayAgg(Aggregate):
    function = "JSON_ARRAYAGG"
    output_field = JSONField()
    allow_order_by = True
    arity = 1

    def __init__(self, *expressions, absent_on_null=False, **extra):
        self.absent_on_null = absent_on_null
        super().__init__(*expressions, **extra)

    def as_sql(self, compiler, connection, **extra_context):
        if self.filter and not connection.features.supports_aggregate_filter_clause:
            raise NotSupportedError(
                "JSONArrayAgg(filter) is not supported on this database backend."
            )
        if self.absent_on_null and not connection.features.supports_json_absent_on_null:
            raise NotSupportedError(
                "JSONArrayAgg(absent_on_null) is not supported on this database "
                "backend."
            )
        return super().as_sql(compiler, connection, **extra_context)

    def as_mysql(self, compiler, connection, **extra_context):
        if self.order_by is not None:
            raise NotSupportedError(
                "JSONArrayAgg(order_by) is not supported on this database backend."
            )
        return self.as_sql(compiler, connection, **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        sql, params = self.as_sql(
            compiler, connection, function="JSON_GROUP_ARRAY", **extra_context
        )
        # JSON_GROUP_ARRAY defaults to returning an empty array on an empty
        # set. Modifies the SQL to support a custom default value to be
        # returned, if a default argument is not passed, null is returned
        # instead of [].
        if (default := self.default) == []:
            return sql, params
        # Ensure Count() is against the exact same parameters (filter,
        # distinct)
        count = self.copy()
        count.__class__ = Count
        count_sql, count_params = compiler.compile(count)
        default_sql = ""
        default_params = ()
        if default is not None:
            default_sql, default_params = compiler.compile(default)
            default_sql = f" ELSE {default_sql}"
        sql = f"(CASE WHEN {count_sql} > 0 THEN {sql}{default_sql} END)"
        return sql, count_params + params + default_params

    def as_native(self, compiler, connection, *, returning=None, **extra_context):
        # Oracle and PostgreSQL 16+ default to removing SQL null values from
        # the returned array. This adds the NULL ON NULL clause to preserve
        # the null values in the array as default behaviour Similar to that
        # of SQLite, also removes the null values from the array when
        # specified via ABSENT ON NULL.
        if len(self.get_source_expressions()) == 0:
            on_null_clause = ""
        elif self.absent_on_null:
            on_null_clause = "ABSENT ON NULL"
        else:
            on_null_clause = "NULL ON NULL"
        if returning:
            extra_context.setdefault(
                "template",
                "%(function)s(%(distinct)s%(expressions)s%(order_by)s "
                f"{on_null_clause} RETURNING {returning}) %(filter)s",
            )
        else:
            extra_context.setdefault(
                "template",
                "%(function)s(%(distinct)s%(expressions)s%(order_by)s "
                f"{on_null_clause}) %(filter)s",
            )
        return self.as_sql(compiler, connection, **extra_context)

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_16:
            sql, params = self.as_sql(
                compiler,
                connection,
                function="ARRAY_AGG",
                **extra_context,
            )
            # Use a filter to cleanly remove null values from the array to
            # match the behaviour of ABSENT ON NULL on Oracle and
            # PostgreSQL 16+.
            if self.absent_on_null:
                expression = self.get_source_expressions()[0]
                if self.filter:
                    not_null_condition = IsNull(expression, False)
                    copy = self.copy()
                    copy.filter.source_expressions[0].children += [not_null_condition]
                    sql, params = copy.as_sql(
                        compiler, connection, function="ARRAY_AGG", **extra_context
                    )
                    return f"TO_JSONB({sql})", params
                else:
                    expr, _ = compiler.compile(expression)
                    filter_sql = f"FILTER (WHERE {expr} IS NOT NULL)"
                    return f"TO_JSONB({sql} {filter_sql})", params
            else:
                return f"TO_JSONB({sql})", params
        return self.as_native(compiler, connection, returning="JSONB", **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        # Oracle turns DATE columns into ISO 8601 timestamp including T00:00:00
        # suffixed when converting to JSON while other backends only include
        # the date part.
        source_expressions = self.get_source_expressions()
        expression = source_expressions[0]
        if isinstance(expression.output_field, DateField):
            clone = self.copy()
            clone.set_source_expressions(
                [
                    Func(expression, Value("YYYY-MM-DD"), function="TO_CHAR"),
                    *source_expressions[1:],
                ]
            )
            return clone.as_native(compiler, connection, **extra_context)
        return self.as_native(compiler, connection, **extra_context)
