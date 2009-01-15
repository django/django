"""
Various data structures used in query construction.

Factored out from django.db.models.query so that they can also be used by other
modules without getting into circular import difficulties.
"""

from copy import deepcopy

from django.utils import tree

class QueryWrapper(object):
    """
    A type that indicates the contents are an SQL fragment and the associate
    parameters. Can be used to pass opaque data to a where-clause, for example.
    """
    def __init__(self, sql, params):
        self.data = sql, params

class Q(tree.Node):
    """
    Encapsulates filters as objects that can then be combined logically (using
    & and |).
    """
    # Connection types
    AND = 'AND'
    OR = 'OR'
    default = AND

    def __init__(self, *args, **kwargs):
        super(Q, self).__init__(children=list(args) + kwargs.items())

    def _combine(self, other, conn):
        if not isinstance(other, Q):
            raise TypeError(other)
        obj = deepcopy(self)
        obj.add(other, conn)
        return obj

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

    def __invert__(self):
        obj = deepcopy(self)
        obj.negate()
        return obj

def select_related_descend(field, restricted, requested):
    """
    Returns True if this field should be used to descend deeper for
    select_related() purposes. Used by both the query construction code
    (sql.query.fill_related_selections()) and the model instance creation code
    (query.get_cached_row()).
    """
    if not field.rel:
        return False
    if field.rel.parent_link:
        return False
    if restricted and field.name not in requested:
        return False
    if not restricted and field.null:
        return False
    return True
