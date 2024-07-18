"""
Classes to represent the definitions of aggregate functions.
"""

from django.core.exceptions import FieldError, FullResultSet
from django.db.models.fields import IntegerField
from django.db import NotSupportedError
from django.db.models.expressions import Case, Func, Star, Value, When, OrderByList
from django.db.models.functions.comparison import Coalesce
from django.db.models.functions.mixins import (
    FixDurationInputMixin,
    NumericOutputFieldMixin,
)

__all__ = [
    "Aggregate",
    "Avg",
    "Count",
    "Max",
    "Min",
    "StdDev",
    "Sum",
    "Variance",
]


class AggregateFilter(Func):
    arity = 1
    template = " FILTER (WHERE %(expressions)s)"

    def as_sql(self, compiler, connection, **extra_context):
        if not connection.features.supports_aggregate_filter_clause:
            raise NotSupportedError
        try:
            return super().as_sql(compiler, connection, **extra_context)
        except FullResultSet:
            return "", ()

    def __str__(self):
        return self.arg_joiner.join(str(arg) for arg in self.source_expressions)


class AggregateOrderBy(OrderByList):
    template = " ORDER BY %(expressions)s"


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
        self.filter = filter and AggregateFilter(filter)
        self.order_by = order_by
        self.default = default
        self.order_by = order_by and AggregateOrderBy.from_param(
            f"{self.__class__.__name__}.order_by", order_by
        )
        super().__init__(*expressions, **extra)

    def get_source_fields(self):
        # Don't consider filter and order by expression as they have nothing
        # to do with the output field resolution.
        return [e._output_field_or_none for e in super().get_source_expressions()]

    def get_source_expressions(self):
        source_expressions = super().get_source_expressions()
        return source_expressions + [self.filter, self.order_by]

    def set_source_expressions(self, exprs):
        *exprs, self.filter, self.order_by = exprs
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
        c.order_by = (
            c.order_by.resolve_expression(query, allow_joins, reuse, summarize)
            if c.order_by
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
                # Fallback to a CASE statement on backends that don't
                # support the FILTER clause.
                copy = self.copy()
                copy.filter = None
                source_expressions = copy.get_source_expressions()
                condition = When(self.filter, then=source_expressions[0])
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

    def __init__(self, expression, filter=None, **extra):
        if expression == "*":
            expression = Star()
        if isinstance(expression, Star) and filter is not None:
            raise ValueError("Star cannot be used with filter. Please specify a field.")
        super().__init__(expression, filter=filter, **extra)


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
