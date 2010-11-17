"""
Classes to represent the default SQL aggregate functions
"""

class AggregateField(object):
    """An internal field mockup used to identify aggregates in the
    data-conversion parts of the database backend.
    """
    def __init__(self, internal_type):
        self.internal_type = internal_type

    def get_internal_type(self):
        return self.internal_type

ordinal_aggregate_field = AggregateField('IntegerField')
computed_aggregate_field = AggregateField('FloatField')

class Aggregate(object):
    """
    Default SQL Aggregate.
    """
    is_ordinal = False
    is_computed = False
    sql_template = '%(function)s(%(field)s)'

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

    def relabel_aliases(self, change_map):
        if isinstance(self.col, (list, tuple)):
            self.col = (change_map.get(self.col[0], self.col[0]), self.col[1])

    def as_sql(self, qn, connection):
        "Return the aggregate, rendered as SQL."

        if hasattr(self.col, 'as_sql'):
            field_name = self.col.as_sql(qn, connection)
        elif isinstance(self.col, (list, tuple)):
            field_name = '.'.join([qn(c) for c in self.col])
        else:
            field_name = self.col

        params = {
            'function': self.sql_function,
            'field': field_name
        }
        params.update(self.extra)

        return self.sql_template % params


class Avg(Aggregate):
    is_computed = True
    sql_function = 'AVG'

class Count(Aggregate):
    is_ordinal = True
    sql_function = 'COUNT'
    sql_template = '%(function)s(%(distinct)s%(field)s)'

    def __init__(self, col, distinct=False, **extra):
        super(Count, self).__init__(col, distinct=distinct and 'DISTINCT ' or '', **extra)

class Max(Aggregate):
    sql_function = 'MAX'

class Min(Aggregate):
    sql_function = 'MIN'

class StdDev(Aggregate):
    is_computed = True

    def __init__(self, col, sample=False, **extra):
        super(StdDev, self).__init__(col, **extra)
        self.sql_function = sample and 'STDDEV_SAMP' or 'STDDEV_POP'

class Sum(Aggregate):
    sql_function = 'SUM'

class Variance(Aggregate):
    is_computed = True

    def __init__(self, col, sample=False, **extra):
        super(Variance, self).__init__(col, **extra)
        self.sql_function = sample and 'VAR_SAMP' or 'VAR_POP'
