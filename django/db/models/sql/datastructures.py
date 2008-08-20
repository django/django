"""
Useful auxilliary data structures for query construction. Not useful outside
the SQL domain.
"""

class EmptyResultSet(Exception):
    pass

class FullResultSet(Exception):
    pass

class MultiJoin(Exception):
    """
    Used by join construction code to indicate the point at which a
    multi-valued join was attempted (if the caller wants to treat that
    exceptionally).
    """
    def __init__(self, level):
        self.level = level

class Empty(object):
    pass

class RawValue(object):
    def __init__(self, value):
        self.value = value

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
    def __init__(self, col='*', distinct=False):
        """
        Set the column to count on (defaults to '*') and set whether the count
        should be distinct or not.
        """
        self.col = col
        self.distinct = distinct

    def relabel_aliases(self, change_map):
        c = self.col
        if isinstance(c, (list, tuple)):
            self.col = (change_map.get(c[0], c[0]), c[1])

    def as_sql(self, quote_func=None):
        if not quote_func:
            quote_func = lambda x: x
        if isinstance(self.col, (list, tuple)):
            col = ('%s.%s' % tuple([quote_func(c) for c in self.col]))
        elif hasattr(self.col, 'as_sql'):
            col = self.col.as_sql(quote_func)
        else:
            col = self.col
        if self.distinct:
            return 'COUNT(DISTINCT %s)' % col
        else:
            return 'COUNT(%s)' % col

class Date(object):
    """
    Add a date selection column.
    """
    def __init__(self, col, lookup_type, date_sql_func):
        self.col = col
        self.lookup_type = lookup_type
        self.date_sql_func = date_sql_func

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
        return self.date_sql_func(self.lookup_type, col)

