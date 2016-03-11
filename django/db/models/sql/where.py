"""
Code to manage the creation and SQL rendering of 'where' constraints.
"""

from django.core.exceptions import EmptyResultSet
from django.utils import tree
from django.utils.functional import cached_property

# Connection types
AND = 'AND'
OR = 'OR'


class WhereNode(tree.Node):
    """
    Used to represent the SQL where-clause.

    The class is tied to the Query class that created it (in order to create
    the correct SQL).

    A child is usually an expression producing boolean values. Most likely the
    expression is a Lookup instance.

    However, a child could also be any class with as_sql() and either
    relabeled_clone() method or relabel_aliases() and clone() methods and
    contains_aggregate attribute.
    """
    default = AND

    def split_having(self, negated=False):
        """
        Returns two possibly None nodes: one for those parts of self that
        should be included in the WHERE clause and one for those parts of
        self that must be included in the HAVING clause.
        """
        if not self.contains_aggregate:
            return self, None
        in_negated = negated ^ self.negated
        # If the effective connector is OR and this node contains an aggregate,
        # then we need to push the whole branch to HAVING clause.
        may_need_split = (
            (in_negated and self.connector == AND) or
            (not in_negated and self.connector == OR))
        if may_need_split and self.contains_aggregate:
            return None, self
        where_parts = []
        having_parts = []
        for c in self.children:
            if hasattr(c, 'split_having'):
                where_part, having_part = c.split_having(in_negated)
                if where_part is not None:
                    where_parts.append(where_part)
                if having_part is not None:
                    having_parts.append(having_part)
            elif c.contains_aggregate:
                having_parts.append(c)
            else:
                where_parts.append(c)
        having_node = self.__class__(having_parts, self.connector, self.negated) if having_parts else None
        where_node = self.__class__(where_parts, self.connector, self.negated) if where_parts else None
        return where_node, having_node

    def as_sql(self, compiler, connection):
        """
        Returns the SQL version of the where clause and the value to be
        substituted in. Returns '', [] if this node matches everything,
        None, [] if this node is empty, and raises EmptyResultSet if this
        node can't match anything.
        """
        result = []
        result_params = []
        if self.connector == AND:
            full_needed, empty_needed = len(self.children), 1
        else:
            full_needed, empty_needed = 1, len(self.children)

        for child in self.children:
            try:
                sql, params = compiler.compile(child)
            except EmptyResultSet:
                empty_needed -= 1
            else:
                if sql:
                    result.append(sql)
                    result_params.extend(params)
                else:
                    full_needed -= 1
            # Check if this node matches nothing or everything.
            # First check the amount of full nodes and empty nodes
            # to make this node empty/full.
            # Now, check if this node is full/empty using the
            # counts.
            if empty_needed == 0:
                if self.negated:
                    return '', []
                else:
                    raise EmptyResultSet
            if full_needed == 0:
                if self.negated:
                    raise EmptyResultSet
                else:
                    return '', []
        conn = ' %s ' % self.connector
        sql_string = conn.join(result)
        if sql_string:
            if self.negated:
                # Some backends (Oracle at least) need parentheses
                # around the inner SQL in the negated case, even if the
                # inner SQL contains just a single expression.
                sql_string = 'NOT (%s)' % sql_string
            elif len(result) > 1:
                sql_string = '(%s)' % sql_string
        return sql_string, result_params

    def get_group_by_cols(self):
        cols = []
        for child in self.children:
            cols.extend(child.get_group_by_cols())
        return cols

    def get_source_expressions(self):
        return self.children[:]

    def set_source_expressions(self, children):
        assert len(children) == len(self.children)
        self.children = children

    def relabel_aliases(self, change_map):
        """
        Relabels the alias values of any children. 'change_map' is a dictionary
        mapping old (current) alias values to the new values.
        """
        for pos, child in enumerate(self.children):
            if hasattr(child, 'relabel_aliases'):
                # For example another WhereNode
                child.relabel_aliases(change_map)
            elif hasattr(child, 'relabeled_clone'):
                self.children[pos] = child.relabeled_clone(change_map)

    def clone(self):
        """
        Creates a clone of the tree. Must only be called on root nodes (nodes
        with empty subtree_parents). Childs must be either (Contraint, lookup,
        value) tuples, or objects supporting .clone().
        """
        clone = self.__class__._new_instance(
            children=[], connector=self.connector, negated=self.negated)
        for child in self.children:
            if hasattr(child, 'clone'):
                clone.children.append(child.clone())
            else:
                clone.children.append(child)
        return clone

    def relabeled_clone(self, change_map):
        clone = self.clone()
        clone.relabel_aliases(change_map)
        return clone

    @classmethod
    def _contains_aggregate(cls, obj):
        if isinstance(obj, tree.Node):
            return any(cls._contains_aggregate(c) for c in obj.children)
        return obj.contains_aggregate

    @cached_property
    def contains_aggregate(self):
        return self._contains_aggregate(self)

    @property
    def is_summary(self):
        return any(child.is_summary for child in self.children)


class NothingNode(object):
    """
    A node that matches nothing.
    """
    contains_aggregate = False

    def as_sql(self, compiler=None, connection=None):
        raise EmptyResultSet


class ExtraWhere(object):
    # The contents are a black box - assume no aggregates are used.
    contains_aggregate = False

    def __init__(self, sqls, params):
        self.sqls = sqls
        self.params = params

    def as_sql(self, compiler=None, connection=None):
        sqls = ["(%s)" % sql for sql in self.sqls]
        return " AND ".join(sqls), list(self.params or ())


class SubqueryConstraint(object):
    # Even if aggregates would be used in a subquery, the outer query isn't
    # interested about those.
    contains_aggregate = False

    def __init__(self, alias, columns, targets, query_object):
        self.alias = alias
        self.columns = columns
        self.targets = targets
        self.query_object = query_object

    def as_sql(self, compiler, connection):
        query = self.query_object
        query.set_values(self.targets)
        query_compiler = query.get_compiler(connection=connection)
        return query_compiler.as_subquery_condition(self.alias, self.columns, compiler)
