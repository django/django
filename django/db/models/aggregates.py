"""
Classes to represent the definitions of aggregate functions.
"""

from django.core.exceptions import FieldError, FullResultSet
from django.db import NotSupportedError
from django.db.models.expressions import Case, ColPairs, Func, Star, Value, When
from django.db.models.fields import IntegerField
from django.db.models.fields.json import JSONField
from django.db.models.functions import Coalesce
from django.db.models.functions.mixins import (
    FixDurationInputMixin,
    NumericOutputFieldMixin,
)

__all__ = [
    "Aggregate",
    "Avg",
    "Count",
    "JSONArrayAgg",
    "Max",
    "Min",
    "StdDev",
    "Sum",
    "Variance",
]


class Aggregate(Func):
    template = "%(function)s(%(distinct)s%(expressions)s)"
    contains_aggregate = True
    name = None
    filter_template = "%s FILTER (WHERE %%(filter)s)"
    window_compatible = True
    allow_distinct = False
    empty_result_set_value = None

    def __init__(
        self, *expressions, distinct=False, filter=None, default=None, **extra
    ):
        if distinct and not self.allow_distinct:
            raise TypeError("%s does not allow distinct." % self.__class__.__name__)
        if default is not None and self.empty_result_set_value is not None:
            raise TypeError(f"{self.__class__.__name__} does not allow default.")
        self.distinct = distinct
        self.filter = filter
        self.default = default
        super().__init__(*expressions, **extra)

    def get_source_fields(self):
        # Don't return the filter expression since it's not a source field.
        return [e._output_field_or_none for e in super().get_source_expressions()]

    def get_source_expressions(self):
        source_expressions = super().get_source_expressions()
        return source_expressions + [self.filter]

    def set_source_expressions(self, exprs):
        *exprs, self.filter = exprs
        return super().set_source_expressions(exprs)

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        # Aggregates are not allowed in UPDATE queries, so ignore for_save
        c = super().resolve_expression(query, allow_joins, reuse, summarize)
        c.filter = (
            c.filter.resolve_expression(query, allow_joins, reuse, summarize)
            if c.filter
            else None
        )
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
        extra_context["distinct"] = "DISTINCT " if self.distinct else ""
        if self.filter:
            if connection.features.supports_aggregate_filter_clause:
                try:
                    filter_sql, filter_params = self.filter.as_sql(compiler, connection)
                except FullResultSet:
                    pass
                else:
                    extra_context = {
                        **extra_context,
                        "template": (
                            self.filter_template
                            % extra_context.get("template", self.template)
                        ),
                    }
                    sql, params = super().as_sql(
                        compiler,
                        connection,
                        filter=filter_sql,
                        **extra_context,
                    )
                    return sql, (*params, *filter_params)
            else:
                copy = self.copy()
                copy.filter = None
                source_expressions = copy.get_source_expressions()
                condition = When(self.filter, then=source_expressions[0])
                copy.set_source_expressions([Case(condition)] + source_expressions[1:])
                return super(Aggregate, copy).as_sql(
                    compiler, connection, **extra_context
                )
        return super().as_sql(compiler, connection, **extra_context)

    def _get_repr_options(self):
        options = super()._get_repr_options()
        if self.distinct:
            options["distinct"] = self.distinct
        if self.filter:
            options["filter"] = self.filter
        return options


class Avg(FixDurationInputMixin, NumericOutputFieldMixin, Aggregate):
    function = "AVG"
    name = "Avg"
    allow_distinct = True


class Count(Aggregate):
    function = "COUNT"
    name = "Count"
    output_field = IntegerField()
    allow_distinct = True
    empty_result_set_value = 0
    allows_composite_expressions = True

    def __init__(self, expression, filter=None, **extra):
        if expression == "*":
            expression = Star()
        if isinstance(expression, Star) and filter is not None:
            raise ValueError("Star cannot be used with filter. Please specify a field.")
        super().__init__(expression, filter=filter, **extra)

    def resolve_expression(self, *args, **kwargs):
        result = super().resolve_expression(*args, **kwargs)
        expr = result.source_expressions[0]

        # In case of composite primary keys, count the first column.
        if isinstance(expr, ColPairs):
            if self.distinct:
                raise ValueError(
                    "COUNT(DISTINCT) doesn't support composite primary keys"
                )

            cols = expr.get_cols()
            return Count(cols[0], filter=result.filter)

        return result


class Max(Aggregate):
    function = "MAX"
    name = "Max"


class Min(Aggregate):
    function = "MIN"
    name = "Min"


class StdDev(NumericOutputFieldMixin, Aggregate):
    name = "StdDev"

    def __init__(self, expression, sample=False, **extra):
        self.function = "STDDEV_SAMP" if sample else "STDDEV_POP"
        super().__init__(expression, **extra)

    def _get_repr_options(self):
        return {**super()._get_repr_options(), "sample": self.function == "STDDEV_SAMP"}


class Sum(FixDurationInputMixin, Aggregate):
    function = "SUM"
    name = "Sum"
    allow_distinct = True


class Variance(NumericOutputFieldMixin, Aggregate):
    name = "Variance"

    def __init__(self, expression, sample=False, **extra):
        self.function = "VAR_SAMP" if sample else "VAR_POP"
        super().__init__(expression, **extra)

    def _get_repr_options(self):
        return {**super()._get_repr_options(), "sample": self.function == "VAR_SAMP"}


class JSONArrayAgg(Aggregate):
    function = "JSON_ARRAYAGG"
    output_field = JSONField()
    arity = 1

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_json_field:
            raise NotSupportedError(
                "JSONFields are not supported on this database backend."
            )
        if self.filter and not connection.features.supports_aggregate_filter_clause:
            raise NotSupportedError(
                "JSONArrayAgg(filter) is not supported on this database backend."
            )
        return super().as_sql(compiler, connection, **extra_context)

    def as_sqlite(self, compiler, connection, **extra_context):
        sql, params = self.as_sql(
            compiler, connection, function="JSON_GROUP_ARRAY", **extra_context
        )
        # JSON_GROUP_ARRAY defaults to returning an empty array on an empty set.
        # Modifies the SQL to support a custom default value to be returned,
        # if a default argument is not passed, null is returned instead of [].
        if (default := self.default) == []:
            return sql, params
        # Ensure Count() is against the exact same parameters (filter, distinct)
        count = self.copy()
        count.__class__ = Count
        count_sql, count_params = compiler.compile(count)
        default_sql = ""
        default_params = () if self.filter is not None else []
        if default is not None:
            default_sql, default_params = compiler.compile(default)
            default_sql = f" ELSE {default_sql}"
        sql = f"(CASE WHEN {count_sql} > 0 THEN {sql}{default_sql} END)"
        return sql, count_params + params + default_params

    def as_postgresql(self, compiler, connection, **extra_context):
        if not connection.features.is_postgresql_16:
            sql, params = super().as_sql(
                compiler,
                connection,
                function="ARRAY_AGG",
                **extra_context,
            )
            return f"TO_JSONB({sql})", params
        extra_context.setdefault(
            "template", "%(function)s(%(distinct)s%(expressions)s RETURNING JSONB)"
        )
        return self.as_sql(compiler, connection, **extra_context)

    def as_oracle(self, compiler, connection, **extra_context):
        # Return same date field format as on other supported backends. 
        expression = self.get_source_expressions()[0]
        internal_type = expression.output_field.get_internal_type()
        if internal_type == "DateField":
            extra_context.setdefault(
                "template", "%(function)s(to_char(%(expressions)s, 'YYYY-MM-DD'))"
            )
        return self.as_sql(compiler, connection, **extra_context)
