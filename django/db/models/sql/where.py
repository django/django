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
    the correct SQL).

    The children in this tree are usually either Q-like objects or lists of
    [table_alias, field_name, db_type, lookup_type, value_annotation,
    params]. However, a child could also be any class with as_sql() and
    relabel_aliases() methods.
    """
    default = AND

    def add(self, data, connector):
        """
        Add a node to the where-tree. If the data is a list or tuple, it is
        expected to be of the form (alias, col_name, field_obj, lookup_type,
        value), which is then slightly munged before being stored (to avoid
        storing any reference to field objects). Otherwise, the 'data' is
        stored unchanged and can be anything with an 'as_sql()' method.
        """
        # Because of circular imports, we need to import this here.
        from django.db.models.base import ObjectDoesNotExist

        if not isinstance(data, (list, tuple)):
            super(WhereNode, self).add(data, connector)
            return

        alias, col, field, lookup_type, value = data
        try:
            if field:
                params = field.get_db_prep_lookup(lookup_type, value)
                db_type = field.db_type()
            else:
                # This is possible when we add a comparison to NULL sometimes
                # (we don't really need to waste time looking up the associated
                # field object).
                params = Field().get_db_prep_lookup(lookup_type, value)
                db_type = None
        except ObjectDoesNotExist:
            # This can happen when trying to insert a reference to a null pk.
            # We break out of the normal path and indicate there's nothing to
            # match.
            super(WhereNode, self).add(NothingNode(), connector)
            return
        if isinstance(value, datetime.datetime):
            annotation = datetime.datetime
        else:
            annotation = bool(value)
        super(WhereNode, self).add((alias, col, db_type, lookup_type,
                annotation, params), connector)

    def as_sql(self, qn=None):
        """
        Returns the SQL version of the where clause and the value to be
        substituted in. Returns None, None if this node is empty.

        If 'node' is provided, that is the root of the SQL generation
        (generally not needed except by the internal implementation for
        recursion).
        """
        if not qn:
            qn = connection.ops.quote_name
        if not self.children:
            return None, []
        result = []
        result_params = []
        empty = True
        for child in self.children:
            try:
                if hasattr(child, 'as_sql'):
                    sql, params = child.as_sql(qn=qn)
                else:
                    # A leaf node in the tree.
                    sql, params = self.make_atom(child, qn)
            except EmptyResultSet:
                if self.connector == AND and not self.negated:
                    # We can bail out early in this particular case (only).
                    raise
                elif self.negated:
                    empty = False
                continue
            except FullResultSet:
                if self.connector == OR:
                    if self.negated:
                        empty = True
                        break
                    # We match everything. No need for any constraints.
                    return '', []
                if self.negated:
                    empty = True
                continue
            empty = False
            if sql:
                result.append(sql)
                result_params.extend(params)
        if empty:
            raise EmptyResultSet

        conn = ' %s ' % self.connector
        sql_string = conn.join(result)
        if sql_string:
            if self.negated:
                sql_string = 'NOT (%s)' % sql_string
            elif len(self.children) != 1:
                sql_string = '(%s)' % sql_string
        return sql_string, result_params

    def make_atom(self, child, qn):
        """
        Turn a tuple (table_alias, column_name, db_type, lookup_type,
        value_annot, params) into valid SQL.

        Returns the string for the SQL fragment and the parameters to use for
        it.
        """
        table_alias, name, db_type, lookup_type, value_annot, params = child
        if table_alias:
            lhs = '%s.%s' % (qn(table_alias), qn(name))
        else:
            lhs = qn(name)
        field_sql = connection.ops.field_cast_sql(db_type) % lhs

        if value_annot is datetime.datetime:
            cast_sql = connection.ops.datetime_cast_sql()
        else:
            cast_sql = '%s'

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
            if not value_annot:
                raise EmptyResultSet
            if extra:
                return ('%s IN %s' % (field_sql, extra), params)
            return ('%s IN (%s)' % (field_sql, ', '.join(['%s'] * len(params))),
                    params)
        elif lookup_type in ('range', 'year'):
            return ('%s BETWEEN %%s and %%s' % field_sql, params)
        elif lookup_type in ('month', 'day'):
            return ('%s = %%s' % connection.ops.date_extract_sql(lookup_type,
                    field_sql), params)
        elif lookup_type == 'isnull':
            return ('%s IS %sNULL' % (field_sql,
                (not value_annot and 'NOT ' or '')), ())
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

class NothingNode(object):
    """
    A node that matches nothing.
    """
    def as_sql(self, qn=None):
        raise EmptyResultSet

    def relabel_aliases(self, change_map, node=None):
        return

