"""
Various data structures used in query construction.

Factored out from django.db.models.query so that they can also be used by other
modules without getting into circular import difficulties.
"""
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
        self.add(other, conn)
        return self

    def __or__(self, other):
        return self._combine(other, self.OR)

    def __and__(self, other):
        return self._combine(other, self.AND)

class QNot(Q):
    """
    Encapsulates the negation of a Q object.
    """
    def __init__(self, q):
        """Creates the negation of the Q object passed in."""
        super(QNot, self).__init__()
        self.add(q, self.AND)
        self.negate()

