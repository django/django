"""
Classes to represent the definitions of aggregate functions.
"""
from django.core.exceptions import FieldError, FullResultSet
from django.db.models.expressions import Case, Func, Star, Value, When
from django.db.models.fields import IntegerField
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
        if self.filter:
            return source_expressions + [self.filter]
        return source_expressions

    def set_source_expressions(self, exprs):
        self.filter = self.filter and exprs.pop()
        return super().set_source_expressions(exprs)

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        # Aggregates are not allowed in UPDATE queries, so ignore for_save
        c = super().resolve_expression(query, allow_joins, reuse, summarize)
        c.filter = c.filter and c.filter.resolve_expression(
            query, allow_joins, reuse, summarize
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
        expressions = self.get_source_expressions()
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
                    template = self.filter_template % extra_context.get(
                        "template", self.template
                    )
                    sql, params = super().as_sql(
                        compiler,
                        connection,
                        template=template,
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
