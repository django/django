"""
Useful auxilliary data structures for query construction. Not useful outside
the SQL domain.
"""

class EmptyResultSet(Exception):
    pass

class MultiJoin(Exception):
    """
    Used by join construction code to indicate the point at which a
    multi-valued join was attempted (if the caller wants to treat that
    exceptionally).
    """
    def __init__(self, names_pos, path_with_names):
        self.level = names_pos
        # The path travelled, this includes the path to the multijoin.
        self.names_with_path = path_with_names

class Empty(object):
    pass

class RawValue(object):
    def __init__(self, value):
        self.value = value

class Date(object):
    """
    Add a date selection column.
    """
    def __init__(self, col, lookup_type):
        self.col = col
        self.lookup_type = lookup_type

    def relabeled_clone(self, change_map):
        return self.__class__((change_map.get(self.col[0], self.col[0]), self.col[1]))

    def as_sql(self, qn, connection):
        if isinstance(self.col, (list, tuple)):
            col = '%s.%s' % tuple([qn(c) for c in self.col])
        else:
            col = self.col
        return connection.ops.date_trunc_sql(self.lookup_type, col), []

class DateTime(object):
    """
    Add a datetime selection column.
    """
    def __init__(self, col, lookup_type, tzname):
        self.col = col
        self.lookup_type = lookup_type
        self.tzname = tzname

    def relabeled_clone(self, change_map):
        return self.__class__((change_map.get(self.col[0], self.col[0]), self.col[1]))

    def as_sql(self, qn, connection):
        if isinstance(self.col, (list, tuple)):
            col = '%s.%s' % tuple([qn(c) for c in self.col])
        else:
            col = self.col
        return connection.ops.datetime_trunc_sql(self.lookup_type, col, self.tzname)
