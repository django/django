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

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        assert len(self.source_expressions) == 1
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
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        if expression == '*':
            expression = Value(expression)
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
