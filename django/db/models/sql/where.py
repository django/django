"""
Code to manage the creation and SQL rendering of 'where' constraints.
"""
import datetime

from django.utils import tree
from django.db import connection
from datastructures import EmptyResultSet

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
        for child in node.children:
            if hasattr(child, 'as_sql'):
                sql, params = child.as_sql(qn=qn)
                format = '(%s)'
            elif isinstance(child, tree.Node):
                sql, params = self.as_sql(child, qn)
                if child.negated:
                    format = 'NOT (%s)'
                else:
                    format = '(%s)'
            else:
                try:
                    sql, params = self.make_atom(child, qn)
                    format = '%s'
                except EmptyResultSet:
                    if self.connection == AND and not node.negated:
                        # We can bail out early in this particular case (only).
                        raise
                    sql = None
            if sql:
                result.append(format % sql)
                result_params.extend(params)
        conn = ' %s ' % node.connection
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
            # FIXME datetime_cast_sql() should return '%s' by default.
            cast_sql = connection.ops.datetime_cast_sql() or '%s'
        else:
            cast_sql = '%s'

        # FIXME: This is out of place. Move to a function like
        # datetime_cast_sql()
        if (lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith')
                and connection.features.needs_upper_for_iops):
            format = 'UPPER(%s) %s'
        else:
            format = '%s %s'

        params = field.get_db_prep_lookup(lookup_type, value)

        if lookup_type in connection.operators:
            return (format % (field_sql,
                    connection.operators[lookup_type] % cast_sql), params)

        if lookup_type == 'in':
            if not value:
                raise EmptyResultSet
            return ('%s IN (%s)' % (field_sql, ', '.join(['%s'] * len(value))),
                    params)
        elif lookup_type in ('range', 'year'):
            return ('%s BETWEEN %%s and %%s' % field_sql,
                    params)
        elif lookup_type in ('month', 'day'):
            return ('%s = %%s' % connection.ops.date_extract_sql(lookup_type,
                    field_sql), params)
        elif lookup_type == 'isnull':
            return ('%s IS %sNULL' % (field_sql, (not value and 'NOT ' or '')),
                    params)
        elif lookup_type in 'search':
            return (connection.ops.fulltest_search_sql(field_sql), params)
        elif lookup_type in ('regex', 'iregex'):
            # FIXME: Factor this out in to connection.ops
            if settings.DATABASE_ENGINE == 'oracle':
                if connection.oracle_version and connection.oracle_version <= 9:
                    raise NotImplementedError("Regexes are not supported in Oracle before version 10g.")
                if lookup_type == 'regex':
                    match_option = 'c'
                else:
                    match_option = 'i'
                return ("REGEXP_LIKE(%s, %s, '%s')" % (field_sql, cast_sql,
                        match_option), params)
            else:
                raise NotImplementedError

        raise TypeError('Invalid lookup_type: %r' % lookup_type)

    def relabel_aliases(self, change_map, node=None):
        """
        Relabels the alias values of any children. 'change_map' is a dictionary
        mapping old (current) alias values to the new values.
        """
        if not node:
            node = self
        for child in node.children:
            if hasattr(child, 'relabel_aliases'):
                child.relabel_aliases(change_map)
            elif isinstance(child, tree.Node):
                self.relabel_aliases(change_map, child)
            else:
                val = child[0]
                child[0] = change_map.get(val, val)

