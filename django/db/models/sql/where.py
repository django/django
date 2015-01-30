"""
Code to manage the creation and SQL rendering of 'where' constraints.
"""
from django.db.models.sql.datastructures import EmptyResultSet
from django.utils.functional import cached_property
from django.utils import tree


# Connection types
AND = 'AND'
OR = 'OR'


class EmptyShortCircuit(Exception):
    """
    Internal exception used to indicate that a "matches nothing" node should be
    added to the where-clause.
    """
    pass


class WhereNode(tree.Node):
    """
    Used to represent the SQL where-clause.

    The class is tied to the Query class that created it (in order to create
    the correct SQL).

    A child is usually an expression producing boolean values. Most likely the
    expression is a Lookup instance, but other types of objects fulfilling the
    required API could be used too (for example, sql.where.EverythingNode).

    However, a child could also be any class with as_sql() and either
    relabeled_clone() method or relabel_aliases() and clone() methods. The
    second alternative should be used if the alias is not the only mutable
    variable.
    """
    default = AND

    def as_sql(self, compiler, connection):
        """
        Returns the SQL version of the where clause and the value to be
        substituted in. Returns '', [] if this node matches everything,
        None, [] if this node is empty, and raises EmptyResultSet if this
        node can't match anything.
        """
        # Note that the logic here is made slightly more complex than
        # necessary because there are two kind of empty nodes: Nodes
        # containing 0 children, and nodes that are known to match everything.
        # A match-everything node is different than empty node (which also
        # technically matches everything) for backwards compatibility reasons.
        # Refs #5261.
        result = []
        result_params = []
        everything_childs, nothing_childs = 0, 0
        non_empty_childs = len(self.children)

        for child in self.children:
            try:
                sql, params = compiler.compile(child)
            except EmptyResultSet:
                nothing_childs += 1
            else:
                if sql:
                    result.append(sql)
                    result_params.extend(params)
                else:
                    if sql is None:
                        # Skip empty childs totally.
                        non_empty_childs -= 1
                        continue
                    everything_childs += 1
            # Check if this node matches nothing or everything.
            # First check the amount of full nodes and empty nodes
            # to make this node empty/full.
            if self.connector == AND:
                full_needed, empty_needed = non_empty_childs, 1
            else:
                full_needed, empty_needed = 1, non_empty_childs
            # Now, check if this node is full/empty using the
            # counts.
            if empty_needed - nothing_childs <= 0:
                if self.negated:
                    return '', []
                else:
                    raise EmptyResultSet
            if full_needed - everything_childs <= 0:
                if self.negated:
                    raise EmptyResultSet
                else:
                    return '', []

        if non_empty_childs == 0:
            # All the child nodes were empty, so this one is empty, too.
            return None, []
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
        if not isinstance(obj, tree.Node):
            return getattr(obj.lhs, 'contains_aggregate', False) or getattr(obj.rhs, 'contains_aggregate', False)
        return any(cls._contains_aggregate(c) for c in obj.children)

    @cached_property
    def contains_aggregate(self):
        return self._contains_aggregate(self)


class EmptyWhere(WhereNode):
    def add(self, data, connector):
        return

    def as_sql(self, compiler=None, connection=None):
        raise EmptyResultSet


class EverythingNode(object):
    """
    A node that matches everything.
    """

    def as_sql(self, compiler=None, connection=None):
        return '', []


class NothingNode(object):
    """
    A node that matches nothing.
    """
    def as_sql(self, compiler=None, connection=None):
        raise EmptyResultSet


class ExtraWhere(object):
    def __init__(self, sqls, params):
        self.sqls = sqls
        self.params = params

    def as_sql(self, compiler=None, connection=None):
        sqls = ["(%s)" % sql for sql in self.sqls]
        return " AND ".join(sqls), list(self.params or ())


class SubqueryConstraint(object):
    def __init__(self, alias, columns, targets, query_object):
        self.alias = alias
        self.columns = columns
        self.targets = targets
        self.query_object = query_object

    def as_sql(self, compiler, connection):
        query = self.query_object

        # QuerySet was sent
        if hasattr(query, 'values'):
            if query._db and connection.alias != query._db:
                raise ValueError("Can't do subqueries with queries on different DBs.")
            # Do not override already existing values.
            if query._fields is None:
                query = query.values(*self.targets)
            else:
                query = query._clone()
            query = query.query
            if query.can_filter():
                # If there is no slicing in use, then we can safely drop all ordering
                query.clear_ordering(True)

        query_compiler = query.get_compiler(connection=connection)
        return query_compiler.as_subquery_condition(self.alias, self.columns, compiler)

    def relabel_aliases(self, change_map):
        self.alias = change_map.get(self.alias, self.alias)

    def clone(self):
        return self.__class__(
            self.alias, self.columns, self.targets,
            self.query_object)
