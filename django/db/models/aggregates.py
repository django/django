"""
Classes to represent the definitions of aggregate functions.
"""

import copy

from django.db.models import expressions

class Aggregate(expressions.ExpressionNode):
    """
    Default Aggregate definition.
    """
    is_ordinal = False
    is_computed = False
    preserve_tree = True

    def __init__(self, lookup, **extra):
        """Instantiate a new aggregate.

         * lookup is the field on which the aggregate operates.
         * extra is a dictionary of additional data to provide for the
           aggregate definition

        Also utilizes the class variables:
         * name, the identifier for this aggregate function.
         * is_ordinal, a boolean indicating if the output of this aggregate
           is an integer (e.g., a count)
         * is_computed, a boolean indicating if this output of this aggregate
           is a computed float (e.g., an average), regardless of the input
           type.
        """
        self.lookup = lookup
        self.extra = extra
        if hasattr(self.lookup,'as_sql') or hasattr(self.lookup,'evaluate'):
            super(Aggregate, self).__init__([self.lookup], self.default_connector, False)
        else:
            super(Aggregate, self).__init__([expressions.F(self.lookup)], self.default_connector, False)

    def __deepcopy__(self, memodict):
        obj = super(Aggregate, self).__deepcopy__(memodict)
        obj.name = self.name
        obj.lookup = copy.deepcopy(self.lookup, memodict)
        obj.extra = copy.deepcopy(self.extra, memodict)
        return obj

    @property
    def default_connector(self):
        return self.name

    @property
    def default_alias(self):
        if hasattr(self.lookup, 'default_alias'):
            alias = self.lookup.default_alias
        elif hasattr(self.lookup, 'evaluate'): 
            raise ValueError('When aggregating over an expression, you need to give an alias.') 
        else:
            alias = self.lookup
        return '%s__%s' % (alias, self.name.lower())

    def add_to_query(self, query, alias, is_summary):
        """Add the aggregate to the nominated query.

        This method is used to convert the generic Aggregate definition into a
        backend-specific definition.

         * query is the backend-specific query instance to which the aggregate
           is to be added.
         * is_summary is a boolean that is set True if the aggregate is a
           summary value rather than an annotation.
        """
        klass = getattr(query.aggregates_module, self.name)
        aggregate = klass(self, query, promote_joins=True, is_summary=is_summary, **self.extra)
        query.aggregates[alias] = aggregate

class Asterisk(object):
    def evaluate(self, evaluator, qn, connection):
        return '*', ()

class Avg(Aggregate):
    name = 'Avg'
    is_computed = True

class Count(Aggregate):
    name = 'Count'
    is_ordinal = True

    def __init__(self, lookup, distinct=False, **extra):
        if lookup == '*':
            lookup = Asterisk()
        super(Count, self).__init__(lookup, distinct=distinct and 'DISTINCT ' or '', **extra)

class Max(Aggregate):
    name = 'Max'

class Min(Aggregate):
    name = 'Min'

class Sum(Aggregate):
    name = 'Sum'

class SampOrPopAgg(Aggregate):
    is_computed = True

    def __init__(self, lookup, sample=False, **extra):
        self.samporpop = 'SAMP' if sample else 'POP'
        super(SampOrPopAgg, self).__init__(lookup, **extra)

    @property
    def default_connector(self):
        return self.name + self.samporpop

class StdDev(SampOrPopAgg):
    name = 'StdDev'

class Variance(SampOrPopAgg):
    name = 'Variance'
