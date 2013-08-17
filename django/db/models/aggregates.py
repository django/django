"""
Classes to represent the definitions of aggregate functions.
"""
import copy

from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields import DecimalField, FloatField


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
    ADDITION = '+'
    SUBSTRACTION = '-'
    MULTIPLICATION = '*'
    DIVISION = '/'

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
        self.operations = []

    def _default_alias(self):
        if self.operations:
            raise ValueError('Alias is required with computed aggregation.')
        return '%s__%s' % (self.lookup, self.name.lower())
    default_alias = property(_default_alias)

    def add_to_query(self, query, alias, col, source, is_summary, model):
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
         * model is the model for the aggregate is called
        """
        query.aggregates[alias] = self._get_aggregate(query, col, source, is_summary, model)

    def _get_aggregate(self, query, col, source, is_summary, model):
        klass = getattr(query.aggregates_module, self.name)
        aggregate = klass(col, source=source, is_summary=is_summary, **self.extra)

        is_computed = False
        for operation in self.operations:
            operator = operation[0]
            operand = operation[1]

            if operator == self.DIVISION and not is_computed:
                is_computed = True

            if isinstance(operand, Aggregate):
                operand_col, operand_source = query.get_column_and_source_for_aggrgate(operand, model, is_summary)
                operand_aggregate = operand._get_aggregate(query, operand_col, operand_source, is_summary, model)
                aggregate.sql_template = '({} {} {})'.format(aggregate.sql_template, operator, operand_aggregate.sql_template)
                aggregate.additional_aggregate_list.append(operand_aggregate)

                if isinstance(operand_aggregate.field, (FloatField, DecimalField)) and not is_computed:
                    is_computed = True
            else:
                aggregate.sql_template = '({} {} {})'.format(aggregate.sql_template, operator, operand)

                if isinstance(operand, float) and not is_computed:
                    is_computed = True

        if is_computed:
            aggregate.is_computed = True
            aggregate.is_ordinal = False
            aggregate.field = query.aggregates_module.computed_aggregate_field

        return aggregate

    def _update_operations(self, operator, obj):
        if not isinstance(obj, (int, long, float, Aggregate)):
            raise TypeError("unsupported operand type(s) for {}: '{}' and '{}'".format(operator, type(self).__name__, type(obj).__name__))

        clone = copy.copy(self)
        if isinstance(obj, Aggregate):
            obj = copy.copy(obj)
        clone.operations.append((operator, obj))
        return clone

    def __add__(self, obj):
        return self._update_operations(self.ADDITION, obj)

    def __mul__(self, obj):
        return self._update_operations(self.MULTIPLICATION, obj)

    def __sub__(self, obj):
        return self._update_operations(self.SUBSTRACTION, obj)

    def __div__(self, obj):
        return self._update_operations(self.DIVISION, obj)


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
