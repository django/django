"""
Various data structures used in query construction.

Factored out from django.db.models.query so that they can also be used by other
modules without getting into circular import difficulties.
"""

from copy import deepcopy

from django.utils import tree

class EmptyResultSet(Exception):
    """
    Raised when a QuerySet cannot contain any data.
    """
    pass

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
        if args and kwargs:
            raise TypeError('Use positional *or* kwargs; not both!')
        nodes = list(args) + kwargs.items()
        super(Q, self).__init__(children=nodes)

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

def not_q(q):
    return ~q

