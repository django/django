"""
Classes to represent the definitions of aggregate functions.
"""
from django.core.exceptions import FieldError
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import WrappedExpression, Value
from django.db.models.fields import IntegerField, FloatField

__all__ = [
    'Aggregate', 'Avg', 'Count', 'Max', 'Min', 'StdDev', 'Sum', 'Variance',
]

integer_field = IntegerField()
float_field = FloatField()


class Aggregate(WrappedExpression):
    is_aggregate = True
    name = None

    def __init__(self, expression, output_type=None, **extra):
        super(Aggregate, self).__init__(expression, output_type, **extra)
        if self.expression.is_aggregate:
            raise FieldError("Cannot compute %s(%s(..)): aggregates cannot be nested" % (
                self.name, expression.name))

        if self.source is None:
            if self.is_ordinal:
                self.source = integer_field
            elif self.is_computed:
                self.source = float_field

    def prepare(self, query=None, allow_joins=True, reuse=None):
        if self.expression.validate_name:  # simple lookup
            name = self.expression.name
            field_list = name.split(LOOKUP_SEP)
            # this whole block was moved from sql/query.py to encapsulate, but will that
            # possibly break custom query classes? The derived prepare() saves us a lot
            # of extra boilerplate though
            if len(field_list) == 1 and name in query.aggregates:
                if not self.is_summary:
                    raise FieldError("Cannot compute %s('%s'): '%s' is an aggregate" % (
                        self.name, name, name))

                annotation = query.aggregates[name]
                if self.source is None:
                    self.source = annotation.output_type
                if annotation.is_aggregate:
                    # aggregation is over an aggregated annotation:
                    # manually set the column, and don't prepare the expression
                    # otherwise the full annotation, including the agg function,
                    # is built inside this aggregation.
                    self.expression.col = (None, name)
                    return
        self._patch_aggregate(query)  # backward-compatibility support
        super(Aggregate, self).prepare(query, allow_joins, reuse)

    def refs_field(self, aggregate_types, field_types):
        return (isinstance(self, aggregate_types) and
                isinstance(self.expression.source, field_types))

    def _default_alias(self):
        if hasattr(self.expression, 'name') and self.expression.validate_name:
            return '%s__%s' % (self.expression.name, self.name.lower())
        raise TypeError("Complex expressions require an alias")
    default_alias = property(_default_alias)

    def _patch_aggregate(self, query):
        """
        Helper method for patching 3rd party aggregates that do not yet support
        the new way of subclassing.

        add_to_query(query, alias, col, source, is_summary) will be defined on
        legacy aggregates which, in turn, instantiates the SQL implementation of
        the aggregate. In all the cases found, the general implementation of
        add_to_query looks like:

        def add_to_query(self, query, alias, col, source, is_summary):
            klass = SQLImplementationAggregate
            aggregate = klass(
                col, source=source, is_summary=is_summary, **self.extra)
            query.aggregates[alias] = aggregate

        By supplying a known alias, we can get the SQLAggregate out of the aggregates
        dict,  and use the sql_function and sql_template attributes to patch *this* aggregate.
        """
        if not hasattr(self, 'add_to_query') or self.sql_function is not None:
            return

        # raise a deprecation warning?

        placeholder_alias = "_XXXXXXXX_"
        self.add_to_query(query, placeholder_alias, None, None, None)
        sql_aggregate = query.aggregates.pop(placeholder_alias)
        if 'sql_function' not in self.extra and hasattr(sql_aggregate, 'sql_function'):
            self.extra['sql_function'] = sql_aggregate.sql_function

        if hasattr(sql_aggregate, 'sql_template'):
            self.extra['sql_template'] = sql_aggregate.sql_template


class Avg(Aggregate):
    is_computed = True
    sql_function = 'AVG'
    name = 'Avg'


class Count(Aggregate):
    is_ordinal = True
    sql_function = 'COUNT'
    name = 'Count'
    sql_template = '%(function)s(%(distinct)s%(field)s)'

    def __init__(self, expression, distinct=False, **extra):
        if expression == '*':
            expression = Value(expression)
            expression.source = integer_field
        super(Count, self).__init__(expression, distinct='DISTINCT ' if distinct else '', **extra)


class Max(Aggregate):
    sql_function = 'MAX'
    name = 'Max'


class Min(Aggregate):
    sql_function = 'MIN'
    name = 'Min'


class StdDev(Aggregate):
    is_computed = True
    name = 'StdDev'

    def __init__(self, expression, sample=False, **extra):
        super(StdDev, self).__init__(expression, **extra)
        self.sql_function = 'STDDEV_SAMP' if sample else 'STDDEV_POP'


class Sum(Aggregate):
    sql_function = 'SUM'
    name = 'Sum'


class Variance(Aggregate):
    is_computed = True
    name = 'Variance'

    def __init__(self, expression, sample=False, **extra):
        super(Variance, self).__init__(expression, **extra)
        self.sql_function = 'VAR_SAMP' if sample else 'VAR_POP'
