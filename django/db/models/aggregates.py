"""
Classes to represent the definitions of aggregate functions.
"""
from django.core.exceptions import FieldError
from django.db.models.expressions import Func, Star
from django.db.models.fields import FloatField, IntegerField

__all__ = [
    'Aggregate', 'Avg', 'Count', 'Max', 'Min', 'StdDev', 'Sum', 'Variance',
]


class Aggregate(Func):
    contains_aggregate = True
    name = None

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        # Aggregates are not allowed in UPDATE queries, so ignore for_save
        c = super(Aggregate, self).resolve_expression(query, allow_joins, reuse, summarize)
        if not summarize:
            expressions = c.get_source_expressions()
            for index, expr in enumerate(expressions):
                if expr.contains_aggregate:
                    before_resolved = self.get_source_expressions()[index]
                    name = before_resolved.name if hasattr(before_resolved, 'name') else repr(before_resolved)
                    raise FieldError("Cannot compute %s('%s'): '%s' is an aggregate" % (c.name, name, name))
        c._patch_aggregate(query)  # backward-compatibility support
        return c

    @property
    def default_alias(self):
        expressions = self.get_source_expressions()
        if len(expressions) == 1 and hasattr(expressions[0], 'name'):
            return '%s__%s' % (expressions[0].name, self.name.lower())
        raise TypeError("Complex expressions require an alias")

    def get_group_by_cols(self):
        return []

    def _patch_aggregate(self, query):
        """
        Helper method for patching 3rd party aggregates that do not yet support
        the new way of subclassing. This method will be removed in Django 1.10.

        add_to_query(query, alias, col, source, is_summary) will be defined on
        legacy aggregates which, in turn, instantiates the SQL implementation of
        the aggregate. In all the cases found, the general implementation of
        add_to_query looks like:

        def add_to_query(self, query, alias, col, source, is_summary):
            klass = SQLImplementationAggregate
            aggregate = klass(col, source=source, is_summary=is_summary, **self.extra)
            query.aggregates[alias] = aggregate

        By supplying a known alias, we can get the SQLAggregate out of the
        aggregates dict, and use the sql_function and sql_template attributes
        to patch *this* aggregate.
        """
        if not hasattr(self, 'add_to_query') or self.function is not None:
            return

        placeholder_alias = "_XXXXXXXX_"
        self.add_to_query(query, placeholder_alias, None, None, None)
        sql_aggregate = query.aggregates.pop(placeholder_alias)
        if 'sql_function' not in self.extra and hasattr(sql_aggregate, 'sql_function'):
            self.extra['function'] = sql_aggregate.sql_function

        if hasattr(sql_aggregate, 'sql_template'):
            self.extra['template'] = sql_aggregate.sql_template


class Avg(Aggregate):
    function = 'AVG'
    name = 'Avg'

    def __init__(self, expression, **extra):
        output_field = extra.pop('output_field', FloatField())
        super(Avg, self).__init__(expression, output_field=output_field, **extra)

    def as_oracle(self, compiler, connection):
        if self.output_field.get_internal_type() == 'DurationField':
            expression = self.get_source_expressions()[0]
            from django.db.backends.oracle.functions import IntervalToSeconds, SecondsToInterval
            return compiler.compile(
                SecondsToInterval(Avg(IntervalToSeconds(expression)))
            )
        return super(Avg, self).as_sql(compiler, connection)


class Count(Aggregate):
    function = 'COUNT'
    name = 'Count'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        if expression == '*':
            expression = Star()
        super(Count, self).__init__(
            expression, distinct='DISTINCT ' if distinct else '', output_field=IntegerField(), **extra)

    def __repr__(self):
        return "{}({}, distinct={})".format(
            self.__class__.__name__,
            self.arg_joiner.join(str(arg) for arg in self.source_expressions),
            'False' if self.extra['distinct'] == '' else 'True',
        )

    def convert_value(self, value, expression, connection, context):
        if value is None:
            return 0
        return int(value)


class Max(Aggregate):
    function = 'MAX'
    name = 'Max'


class Min(Aggregate):
    function = 'MIN'
    name = 'Min'


class StdDev(Aggregate):
    name = 'StdDev'

    def __init__(self, expression, sample=False, **extra):
        self.function = 'STDDEV_SAMP' if sample else 'STDDEV_POP'
        super(StdDev, self).__init__(expression, output_field=FloatField(), **extra)

    def __repr__(self):
        return "{}({}, sample={})".format(
            self.__class__.__name__,
            self.arg_joiner.join(str(arg) for arg in self.source_expressions),
            'False' if self.function == 'STDDEV_POP' else 'True',
        )

    def convert_value(self, value, expression, connection, context):
        if value is None:
            return value
        return float(value)


class Sum(Aggregate):
    function = 'SUM'
    name = 'Sum'

    def as_oracle(self, compiler, connection):
        if self.output_field.get_internal_type() == 'DurationField':
            expression = self.get_source_expressions()[0]
            from django.db.backends.oracle.functions import IntervalToSeconds, SecondsToInterval
            return compiler.compile(
                SecondsToInterval(Sum(IntervalToSeconds(expression)))
            )
        return super(Sum, self).as_sql(compiler, connection)


class Variance(Aggregate):
    name = 'Variance'

    def __init__(self, expression, sample=False, **extra):
        self.function = 'VAR_SAMP' if sample else 'VAR_POP'
        super(Variance, self).__init__(expression, output_field=FloatField(), **extra)

    def __repr__(self):
        return "{}({}, sample={})".format(
            self.__class__.__name__,
            self.arg_joiner.join(str(arg) for arg in self.source_expressions),
            'False' if self.function == 'VAR_POP' else 'True',
        )

    def convert_value(self, value, expression, connection, context):
        if value is None:
            return value
        return float(value)
