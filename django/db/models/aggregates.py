"""
Classes to represent the definitions of aggregate functions.
"""
from django.core.exceptions import FieldError
from django.db.models.expressions import Func, Value
from django.db.models.fields import FloatField, IntegerField

__all__ = [
    'Aggregate', 'Avg', 'Count', 'Max', 'Min', 'StdDev', 'Sum', 'Variance',
]


class Aggregate(Func):
    contains_aggregate = True
    name = None
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super(Aggregate, self).__init__(
            expression, distinct='DISTINCT ' if distinct else '', **extra)

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        assert len(self.source_expressions) == 1, \
            'source_expressions for %s is "%s"' % (self.__class__.__name__, self.source_expressions)
        # Aggregates are not allowed in UPDATE queries, so ignore for_save
        c = super(Aggregate, self).resolve_expression(query, allow_joins, reuse, summarize)
        if c.source_expressions[0].contains_aggregate and not summarize:
            name = self.source_expressions[0].name
            raise FieldError("Cannot compute %s('%s'): '%s' is an aggregate" % (
                c.name, name, name))
        c._patch_aggregate(query)  # backward-compatibility support
        return c

    @property
    def input_field(self):
        return self.source_expressions[0]

    @property
    def default_alias(self):
        if hasattr(self.source_expressions[0], 'name'):
            return '%s__%s' % (self.source_expressions[0].name, self.name.lower())
        raise TypeError("Complex expressions require an alias")

    def get_group_by_cols(self):
        return []

    def _patch_aggregate(self, query):
        """
        Helper method for patching 3rd party aggregates that do not yet support
        the new way of subclassing. This method should be removed in 2.0

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

    def __repr__(self, **extra_properties):
        extra_properties_repr = ', '.join("{!s}={!r}".format(key, val) for (key, val) in extra_properties.items())
        return '{}({}{}{})'.format(
            self.__class__.__name__,
            self.arg_joiner.join(str(arg) for arg in self.source_expressions),
            ', distinct=True' if self.extra['distinct'] else '',
            ', ' + extra_properties_repr if extra_properties else ''
        )


class Avg(Aggregate):
    function = 'AVG'
    name = 'Avg'

    def __init__(self, expression, **extra):
        super(Avg, self).__init__(expression, output_field=FloatField(), **extra)

    def convert_value(self, value, expression, connection, context):
        if value is None:
            return value
        return float(value)


class Count(Aggregate):
    function = 'COUNT'
    name = 'Count'

    def __init__(self, expression, **extra):
        if expression == '*':
            expression = Value(expression)
        super(Count, self).__init__(expression, output_field=IntegerField(), **extra)

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


class StatisticalAggregate(Aggregate):
    sample_function = None
    population_function = None

    def __init__(self, expression, sample=False, **extra):
        self.function = self.sample_function if sample else self.population_function
        super(StatisticalAggregate, self).__init__(expression, output_field=FloatField(), **extra)

    def __repr__(self):
        return super(StatisticalAggregate, self).__repr__(sample=self.uses_sample_function())

    def uses_sample_function(self):
        return self.function == self.sample_function

    def convert_value(self, value, expression, connection, context):
        if value is None:
            return value
        return float(value)


class StdDev(StatisticalAggregate):
    sample_function = 'STDDEV_SAMP'
    population_function = 'STDDEV_POP'
    name = 'StdDev'


class Sum(Aggregate):
    function = 'SUM'
    name = 'Sum'


class Variance(StatisticalAggregate):
    sample_function = 'VAR_SAMP'
    population_function = 'VAR_POP'
    name = 'Variance'
