"""
Code to manage the creation and SQL rendering of 'where' constraints.
"""
import datetime

from django.utils import tree
from django.db import connection
from django.db.models.fields import Field
from django.db.models.query_utils import QueryWrapper
from datastructures import EmptyResultSet, FullResultSet

# Connection types
AND = 'AND'
OR = 'OR'

class WhereNode(tree.Node):
    """
    Used to represent the SQL where-clause.

    The class is tied to the Query class that created it (in order to create
    the corret SQL).

    The children in this tree are usually either Q-like objects or lists of
    [table_alias, field_name, field_class, lookup_type, value]. However, a
    child could also be any class with as_sql() and relabel_aliases() methods.
    """
    default = AND

    def as_sql(self, node=None, qn=None):
        """
        Returns the SQL version of the where clause and the value to be
        substituted in. Returns None, None if this node is empty.

        If 'node' is provided, that is the root of the SQL generation
        (generally not needed except by the internal implementation for
        recursion).
        """
        if node is None:
            node = self
        if not qn:
            qn = connection.ops.quote_name
        if not node.children:
            return None, []
        result = []
        result_params = []
        empty = True
        for child in node.children:
            try:
                if hasattr(child, 'as_sql'):
                    sql, params = child.as_sql(qn=qn)
                    format = '(%s)'
                elif isinstance(child, tree.Node):
                    sql, params = self.as_sql(child, qn)
                    if child.negated:
                        format = 'NOT (%s)'
                    elif len(child.children) == 1:
                        format = '%s'
                    else:
                        format = '(%s)'
                else:
                    sql, params = self.make_atom(child, qn)
                    format = '%s'
            except EmptyResultSet:
                if node.connector == AND and not node.negated:
                    # We can bail out early in this particular case (only).
                    raise
                elif node.negated:
                    empty = False
                continue
            except FullResultSet:
                if self.connector == OR:
                    if node.negated:
                        empty = True
                        break
                    # We match everything. No need for any constraints.
                    return '', []
                if node.negated:
                    empty = True
                continue
            empty = False
            if sql:
                result.append(format % sql)
                result_params.extend(params)
        if empty:
            raise EmptyResultSet
        conn = ' %s ' % node.connector
        return conn.join(result), result_params

    def make_atom(self, child, qn):
        """
        Turn a tuple (table_alias, field_name, field_class, lookup_type, value)
        into valid SQL.

        Returns the string for the SQL fragment and the parameters to use for
        it.
        """
        table_alias, name, field, lookup_type, value = child
        if table_alias:
            lhs = '%s.%s' % (qn(table_alias), qn(name))
        else:
            lhs = qn(name)
        db_type = field and field.db_type() or None
        field_sql = connection.ops.field_cast_sql(db_type) % lhs

        if isinstance(value, datetime.datetime):
            cast_sql = connection.ops.datetime_cast_sql()
        else:
            cast_sql = '%s'

        if field:
            params = field.get_db_prep_lookup(lookup_type, value)
        else:
            params = Field().get_db_prep_lookup(lookup_type, value)
        if isinstance(params, QueryWrapper):
            extra, params = params.data
        else:
            extra = ''

        if lookup_type in connection.operators:
            format = "%s %%s %s" % (connection.ops.lookup_cast(lookup_type),
                    extra)
            return (format % (field_sql,
                    connection.operators[lookup_type] % cast_sql), params)

        if lookup_type == 'in':
            if not value:
                raise EmptyResultSet
            if extra:
                return ('%s IN %s' % (field_sql, extra), params)
            return ('%s IN (%s)' % (field_sql, ', '.join(['%s'] * len(value))),
                    params)
        elif lookup_type in ('range', 'year'):
            return ('%s BETWEEN %%s and %%s' % field_sql, params)
        elif lookup_type in ('month', 'day'):
            return ('%s = %%s' % connection.ops.date_extract_sql(lookup_type,
                    field_sql), params)
        elif lookup_type == 'isnull':
            return ('%s IS %sNULL' % (field_sql, (not value and 'NOT ' or '')),
                    params)
        elif lookup_type == 'search':
            return (connection.ops.fulltext_search_sql(field_sql), params)
        elif lookup_type in ('regex', 'iregex'):
            return connection.ops.regex_lookup(lookup_type) % (field_sql, cast_sql), params

        raise TypeError('Invalid lookup_type: %r' % lookup_type)

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
            else:
                if child[0] in change_map:
                    node.children[pos] = (change_map[child[0]],) + child[1:]

class EverythingNode(object):
    """
    A node that matches everything.
    """
    def as_sql(self, qn=None):
        raise FullResultSet

    def relabel_aliases(self, change_map, node=None):
        return
