"""
Code to manage the creation and SQL rendering of 'where' constraints.
"""

from __future__ import absolute_import

import datetime
from itertools import repeat

from django.utils import tree
from django.db.models.fields import Field
from django.db.models.sql.datastructures import EmptyResultSet
from django.db.models.sql.aggregates import Aggregate
from django.utils.itercompat import is_iterator
from django.utils.six.moves import xrange

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

    The children in this tree are usually either Q-like objects or lists of
    [table_alias, field_name, db_type, lookup_type, value_annotation, params].
    However, a child could also be any class with as_sql() and relabel_aliases() methods.
    """
    default = AND

    def add(self, data, connector):
        """
        Add a node to the where-tree. If the data is a list or tuple, it is
        expected to be of the form (obj, lookup_type, value), where obj is
        a Constraint object, and is then slightly munged before being stored
        (to avoid storing any reference to field objects). Otherwise, the 'data'
        is stored unchanged and can be any class with an 'as_sql()' method.
        """
        if not isinstance(data, (list, tuple)):
            super(WhereNode, self).add(data, connector)
            return

        obj, lookup_type, value = data
        if is_iterator(value):
            # Consume any generators immediately, so that we can determine
            # emptiness and transform any non-empty values correctly.
            value = list(value)

        # The "value_annotation" parameter is used to pass auxilliary information
        # about the value(s) to the query construction. Specifically, datetime
        # and empty values need special handling. Other types could be used
        # here in the future (using Python types is suggested for consistency).
        if isinstance(value, datetime.datetime):
            value_annotation = datetime.datetime
        elif hasattr(value, 'value_annotation'):
            value_annotation = value.value_annotation
        else:
            value_annotation = bool(value)

        if hasattr(obj, "prepare"):
            value = obj.prepare(lookup_type, value)

        super(WhereNode, self).add(
                (obj, lookup_type, value_annotation, value), connector)

    def as_sql(self, qn, connection):
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
                if hasattr(child, 'as_sql'):
                    sql, params = child.as_sql(qn=qn, connection=connection)
                else:
                    # A leaf node in the tree.
                    sql, params = self.make_atom(child, qn, connection)
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

    def make_atom(self, child, qn, connection):
        """
        Turn a tuple (Constraint(table_alias, column_name, db_type),
        lookup_type, value_annotation, params) into valid SQL.

        The first item of the tuple may also be an Aggregate.

        Returns the string for the SQL fragment and the parameters to use for
        it.
        """
        lvalue, lookup_type, value_annotation, params_or_value = child
        if isinstance(lvalue, Constraint):
            try:
                lvalue, params = lvalue.process(lookup_type, params_or_value, connection)
            except EmptyShortCircuit:
                raise EmptyResultSet
        elif isinstance(lvalue, Aggregate):
            params = lvalue.field.get_db_prep_lookup(lookup_type, params_or_value, connection)
        else:
            raise TypeError("'make_atom' expects a Constraint or an Aggregate "
                            "as the first item of its 'child' argument.")

        if isinstance(lvalue, tuple):
            # A direct database column lookup.
            field_sql = self.sql_for_columns(lvalue, qn, connection)
        else:
            # A smart object with an as_sql() method.
            field_sql = lvalue.as_sql(qn, connection)

        if value_annotation is datetime.datetime:
            cast_sql = connection.ops.datetime_cast_sql()
        else:
            cast_sql = '%s'

        if hasattr(params, 'as_sql'):
            extra, params = params.as_sql(qn, connection)
            cast_sql = ''
        else:
            extra = ''

        if (len(params) == 1 and params[0] == '' and lookup_type == 'exact'
            and connection.features.interprets_empty_strings_as_nulls):
            lookup_type = 'isnull'
            value_annotation = True

        if lookup_type in connection.operators:
            format = "%s %%s %%s" % (connection.ops.lookup_cast(lookup_type),)
            return (format % (field_sql,
                              connection.operators[lookup_type] % cast_sql,
                              extra), params)

        if lookup_type == 'in':
            if not value_annotation:
                raise EmptyResultSet
            if extra:
                return ('%s IN %s' % (field_sql, extra), params)
            max_in_list_size = connection.ops.max_in_list_size()
            if max_in_list_size and len(params) > max_in_list_size:
                # Break up the params list into an OR of manageable chunks.
                in_clause_elements = ['(']
                for offset in xrange(0, len(params), max_in_list_size):
                    if offset > 0:
                        in_clause_elements.append(' OR ')
                    in_clause_elements.append('%s IN (' % field_sql)
                    group_size = min(len(params) - offset, max_in_list_size)
                    param_group = ', '.join(repeat('%s', group_size))
                    in_clause_elements.append(param_group)
                    in_clause_elements.append(')')
                in_clause_elements.append(')')
                return ''.join(in_clause_elements), params
            else:
                return ('%s IN (%s)' % (field_sql,
                                        ', '.join(repeat('%s', len(params)))),
                        params)
        elif lookup_type in ('range', 'year'):
            return ('%s BETWEEN %%s and %%s' % field_sql, params)
        elif lookup_type in ('month', 'day', 'week_day'):
            return ('%s = %%s' % connection.ops.date_extract_sql(lookup_type, field_sql),
                    params)
        elif lookup_type == 'isnull':
            return ('%s IS %sNULL' % (field_sql,
                (not value_annotation and 'NOT ' or '')), ())
        elif lookup_type == 'search':
            return (connection.ops.fulltext_search_sql(field_sql), params)
        elif lookup_type in ('regex', 'iregex'):
            return connection.ops.regex_lookup(lookup_type) % (field_sql, cast_sql), params

        raise TypeError('Invalid lookup_type: %r' % lookup_type)

    def sql_for_columns(self, data, qn, connection):
        """
        Returns the SQL fragment used for the left-hand side of a column
        constraint (for example, the "T1.foo" portion in the clause
        "WHERE ... T1.foo = 6").
        """
        table_alias, name, db_type = data
        if table_alias:
            lhs = '%s.%s' % (qn(table_alias), qn(name))
        else:
            lhs = qn(name)
        return connection.ops.field_cast_sql(db_type) % lhs

    def relabel_aliases(self, change_map, node=None):
        """
        Relabels the alias values of any children. 'change_map' is a dictionary
        mapping old (current) alias values to the new values.
        """
        if not node:
            node = self
        for pos, child in enumerate(node.children):
            if hasattr(child, 'relabel_aliases'):
                child.relabel_aliases(change_map)
            elif isinstance(child, tree.Node):
                self.relabel_aliases(change_map, child)
            elif isinstance(child, (list, tuple)):
                if isinstance(child[0], (list, tuple)):
                    elt = list(child[0])
                    if elt[0] in change_map:
                        elt[0] = change_map[elt[0]]
                        node.children[pos] = (tuple(elt),) + child[1:]
                else:
                    child[0].relabel_aliases(change_map)

                # Check if the query value also requires relabelling
                if hasattr(child[3], 'relabel_aliases'):
                    child[3].relabel_aliases(change_map)

class EverythingNode(object):
    """
    A node that matches everything.
    """

    def as_sql(self, qn=None, connection=None):
        return '', []

    def relabel_aliases(self, change_map, node=None):
        return

class NothingNode(object):
    """
    A node that matches nothing.
    """
    def as_sql(self, qn=None, connection=None):
        raise EmptyResultSet

    def relabel_aliases(self, change_map, node=None):
        return

class ExtraWhere(object):
    def __init__(self, sqls, params):
        self.sqls = sqls
        self.params = params

    def as_sql(self, qn=None, connection=None):
        sqls = ["(%s)" % sql for sql in self.sqls]
        return " AND ".join(sqls), tuple(self.params or ())

class Constraint(object):
    """
    An object that can be passed to WhereNode.add() and knows how to
    pre-process itself prior to including in the WhereNode.
    """
    def __init__(self, alias, col, field):
        self.alias, self.col, self.field = alias, col, field

    def __getstate__(self):
        """Save the state of the Constraint for pickling.

        Fields aren't necessarily pickleable, because they can have
        callable default values. So, instead of pickling the field
        store a reference so we can restore it manually
        """
        obj_dict = self.__dict__.copy()
        if self.field:
            obj_dict['model'] = self.field.model
            obj_dict['field_name'] = self.field.name
        del obj_dict['field']
        return obj_dict

    def __setstate__(self, data):
        """Restore the constraint """
        model = data.pop('model', None)
        field_name = data.pop('field_name', None)
        self.__dict__.update(data)
        if model is not None:
            self.field = model._meta.get_field(field_name)
        else:
            self.field = None

    def prepare(self, lookup_type, value):
        if self.field:
            return self.field.get_prep_lookup(lookup_type, value)
        return value

    def process(self, lookup_type, value, connection):
        """
        Returns a tuple of data suitable for inclusion in a WhereNode
        instance.
        """
        # Because of circular imports, we need to import this here.
        from django.db.models.base import ObjectDoesNotExist
        try:
            if self.field:
                params = self.field.get_db_prep_lookup(lookup_type, value,
                    connection=connection, prepared=True)
                db_type = self.field.db_type(connection=connection)
            else:
                # This branch is used at times when we add a comparison to NULL
                # (we don't really want to waste time looking up the associated
                # field object at the calling location).
                params = Field().get_db_prep_lookup(lookup_type, value,
                    connection=connection, prepared=True)
                db_type = None
        except ObjectDoesNotExist:
            raise EmptyShortCircuit

        return (self.alias, self.col, db_type), params

    def relabel_aliases(self, change_map):
        if self.alias in change_map:
            self.alias = change_map[self.alias]
