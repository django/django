"""
Classes to represent the default SQL aggregate functions
"""
import copy

from django.db.models.fields import IntegerField, FloatField

# Fake fields used to identify aggregate types in data-conversion operations.
ordinal_aggregate_field = IntegerField()
computed_aggregate_field = FloatField()


class Aggregate(object):
    """
    Default SQL Aggregate.
    """
    is_ordinal = False
    is_computed = False
    sql_template = '%(function_{0})s(%(field_{0})s)'

    def __init__(self, col, source=None, is_summary=False, **extra):
        """Instantiate an SQL aggregate

         * col is a column reference describing the subject field
           of the aggregate. It can be an alias, or a tuple describing
           a table and column name.
         * source is the underlying field or aggregate definition for
           the column reference. If the aggregate is not an ordinal or
           computed type, this reference is used to determine the coerced
           output type of the aggregate.
         * extra is a dictionary of additional data to provide for the
           aggregate definition

        Also utilizes the class variables:
         * sql_function, the name of the SQL function that implements the
           aggregate.
         * sql_template, a template string that is used to render the
           aggregate into SQL.
         * is_ordinal, a boolean indicating if the output of this aggregate
           is an integer (e.g., a count)
         * is_computed, a boolean indicating if this output of this aggregate
           is a computed float (e.g., an average), regardless of the input
           type.

        """
        self.col = col
        self.source = source
        self.is_summary = is_summary
        self.extra = extra
        self.additional_aggregate_list = []
        self._set_sql_template()

        # Follow the chain of aggregate sources back until you find an
        # actual field, or an aggregate that forces a particular output
        # type. This type of this field will be used to coerce values
        # retrieved from the database.
        tmp = self

        while tmp and isinstance(tmp, Aggregate):
            if getattr(tmp, 'is_ordinal', False):
                tmp = ordinal_aggregate_field
            elif getattr(tmp, 'is_computed', False):
                tmp = computed_aggregate_field
            else:
                tmp = tmp.source

        self.field = tmp

    def __setstate__(self, state):
        for attr in state:
            setattr(self, attr, state[attr])
        self._set_sql_template()

    def _set_sql_template(self):
        self.sql_template = type(self).sql_template.format(id(self))

    def copy(self):
        clone = copy.copy(self)
        clone._set_sql_template()
        return clone

    def relabeled_clone(self, change_map):
        clone = self.copy()
        if isinstance(self.col, (list, tuple)):
            clone.col = (change_map.get(self.col[0], self.col[0]), self.col[1])
        return clone

    def _get_template_params(self, qn, connection):
        params = []
        if hasattr(self.col, 'as_sql'):
            field_name, params = self.col.as_sql(qn, connection)
        elif isinstance(self.col, (list, tuple)):
            field_name = '.'.join([qn(c) for c in self.col])
        else:
            field_name = self.col

        substitutions = {
            'function_{}'.format(id(self)): self.sql_function,
            'field_{}'.format(id(self)): field_name
        }
        substitutions.update({'{}_{}'.format(key, id(self)): value for key, value in self.extra.iteritems()})

        return substitutions, params

    def as_sql(self, qn, connection):
        "Return the aggregate, rendered as SQL with parameters."
        substitutions, params = self._get_template_params(qn, connection)
        for aggregate in self.additional_aggregate_list:
            subs, pars = aggregate._get_template_params(qn, connection)
            substitutions.update(subs)
            params.extend(pars)

        return self.sql_template % substitutions, params


class Avg(Aggregate):
    is_computed = True
    sql_function = 'AVG'


class Count(Aggregate):
    is_ordinal = True
    sql_function = 'COUNT'
    sql_template = '%(function_{0})s(%(distinct_{0})s%(field_{0})s)'

    def __init__(self, col, distinct=False, **extra):
        super(Count, self).__init__(col, distinct='DISTINCT ' if distinct else '', **extra)


class Max(Aggregate):
    sql_function = 'MAX'


class Min(Aggregate):
    sql_function = 'MIN'


class StdDev(Aggregate):
    is_computed = True

    def __init__(self, col, sample=False, **extra):
        super(StdDev, self).__init__(col, **extra)
        self.sql_function = 'STDDEV_SAMP' if sample else 'STDDEV_POP'


class Sum(Aggregate):
    sql_function = 'SUM'


class Variance(Aggregate):
    is_computed = True

    def __init__(self, col, sample=False, **extra):
        super(Variance, self).__init__(col, **extra)
        self.sql_function = 'VAR_SAMP' if sample else 'VAR_POP'
