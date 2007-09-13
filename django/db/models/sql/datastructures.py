"""
Useful auxilliary data structures for query construction. Not useful outside
the SQL domain.
"""

class EmptyResultSet(Exception):
    pass

class Aggregate(object):
    """
    Base class for all aggregate-related classes (min, max, avg, count, sum).
    """
    def relabel_aliases(self, change_map):
        """
        Relabel the column alias, if necessary. Must be implemented by
        subclasses.
        """
        raise NotImplementedError

    def as_sql(self, quote_func=None):
        """
        Returns the SQL string fragment for this object.

        The quote_func function is used to quote the column components. If
        None, it defaults to doing nothing.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

class Count(Aggregate):
    """
    Perform a count on the given column.
    """
    def __init__(self, col=None, distinct=False):
        """
        Set the column to count on (defaults to '*') and set whether the count
        should be distinct or not.
        """
        self.col = col and col or '*'
        self.distinct = distinct

    def relabel_aliases(self, change_map):
        c = self.col
        if isinstance(c, (list, tuple)):
            self.col = (change_map.get(c[0], c[0]), c[1])

    def as_sql(self, quote_func=None):
        if not quote_func:
            quote_func = lambda x: x
        if isinstance(self.col, (list, tuple)):
            col = '%s.%s' % tuple([quote_func(c) for c in self.col])
        else:
            col = self.col
        if self.distinct:
            return 'COUNT(DISTINCT(%s))' % col
        else:
            return 'COUNT(%s)' % col

