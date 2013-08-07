"""
Classes to represent the definitions of aggregate functions.
"""
from django.db.models.constants import LOOKUP_SEP


def refs_aggregate(lookup_parts, aggregates):
    """
    A little helper method to check if the lookup_parts contains references
    to the given aggregates set. Because the LOOKUP_SEP is contained in the
    default annotation names we must check each prefix of the lookup_parts
    for match.
    """
    for i in range(len(lookup_parts) + 1):
        if LOOKUP_SEP.join(lookup_parts[0:i]) in aggregates:
            return True
    return False


class Aggregate(object):
    """
    Default Aggregate definition.
    """
    def __init__(self, lookup, **extra):
        """Instantiate a new aggregate.

         * lookup is the field on which the aggregate operates.
         * extra is a dictionary of additional data to provide for the
           aggregate definition

        Also utilizes the class variables:
         * name, the identifier for this aggregate function.
        """
        self.lookup = lookup
        self.extra = extra

    def _default_alias(self):
        return '%s__%s' % (self.lookup, self.name.lower())
    default_alias = property(_default_alias)

    def add_to_query(self, query, alias, col, source, is_summary):
        """Add the aggregate to the nominated query.

        This method is used to convert the generic Aggregate definition into a
        backend-specific definition.

         * query is the backend-specific query instance to which the aggregate
           is to be added.
         * col is a column reference describing the subject field
           of the aggregate. It can be an alias, or a tuple describing
           a table and column name.
         * source is the underlying field or aggregate definition for
           the column reference. If the aggregate is not an ordinal or
           computed type, this reference is used to determine the coerced
           output type of the aggregate.
         * is_summary is a boolean that is set True if the aggregate is a
           summary value rather than an annotation.
        """
        klass = getattr(query.aggregates_module, self.name)
        aggregate = klass(col, source=source, is_summary=is_summary, **self.extra)
        query.aggregates[alias] = aggregate


class Avg(Aggregate):
    name = 'Avg'


class Count(Aggregate):
    name = 'Count'


class Max(Aggregate):
    name = 'Max'


class Min(Aggregate):
    name = 'Min'


class StdDev(Aggregate):
    name = 'StdDev'


class Sum(Aggregate):
    name = 'Sum'


class Variance(Aggregate):
    name = 'Variance'
