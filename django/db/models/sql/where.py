"""
Code to manage the creation and SQL rendering of 'where' constraints.
"""

import collections
import datetime
import warnings
from itertools import repeat

from django.conf import settings
from django.db.models.fields import DateTimeField, Field
from django.db.models.sql.datastructures import Empty, EmptyResultSet
from django.utils import timezone, tree
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.functional import cached_property
from django.utils.six.moves import range

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

    A child is usually a tuple of:
        (Constraint(alias, targetcol, field), lookup_type, value)
    where value can be either raw Python value, or Query, ExpressionNode or
    something else knowing how to turn itself into SQL.

    However, a child could also be any class with as_sql() and either
    relabeled_clone() method or relabel_aliases() and clone() methods. The
    second alternative should be used if the alias is not the only mutable
    variable.
    """
    default = AND

    def _prepare_data(self, data):
        """
        Prepare data for addition to the tree. If the data is a list or tuple,
        it is expected to be of the form (obj, lookup_type, value), where obj
        is a Constraint object, and is then slightly munged before being
        stored (to avoid storing any reference to field objects). Otherwise,
        the 'data' is stored unchanged and can be any class with an 'as_sql()'
        method.
        """
        if not isinstance(data, (list, tuple)):
            return data
        obj, lookup_type, value = data
        if isinstance(value, collections.Iterator):
            # Consume any generators immediately, so that we can determine
            # emptiness and transform any non-empty values correctly.
            value = list(value)

        # The "value_annotation" parameter is used to pass auxiliary information
        # about the value(s) to the query construction. Specifically, datetime
        # and empty values need special handling. Other types could be used
        # here in the future (using Python types is suggested for consistency).
        if (isinstance(value, datetime.datetime)
                or (isinstance(obj.field, DateTimeField) and lookup_type != 'isnull')):
            value_annotation = datetime.datetime
        elif hasattr(value, 'value_annotation'):
            value_annotation = value.value_annotation
        else:
            value_annotation = bool(value)

        if hasattr(obj, 'prepare'):
            value = obj.prepare(lookup_type, value)
        return (obj, lookup_type, value_annotation, value)

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
                if hasattr(child, 'as_sql'):
                    sql, params = compiler.compile(child)
                else:
                    # A leaf node in the tree.
                    sql, params = self.make_atom(child, compiler, connection)
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
            if hasattr(child, 'get_group_by_cols'):
                cols.extend(child.get_group_by_cols())
            else:
                if isinstance(child[0], Constraint):
                    cols.append((child[0].alias, child[0].col))
                if hasattr(child[3], 'get_group_by_cols'):
                    cols.extend(child[3].get_group_by_cols())
        return cols

    def make_atom(self, child, compiler, connection):
        """
        Turn a tuple (Constraint(table_alias, column_name, db_type),
        lookup_type, value_annotation, params) into valid SQL.

        The first item of the tuple may also be an Aggregate.

        Returns the string for the SQL fragment and the parameters to use for
        it.
        """
        warnings.warn(
            "The make_atom() method will be removed in Django 1.9. Use Lookup class instead.",
            RemovedInDjango19Warning)
        lvalue, lookup_type, value_annotation, params_or_value = child
        field_internal_type = lvalue.field.get_internal_type() if lvalue.field else None

        if isinstance(lvalue, Constraint):
            try:
                lvalue, params = lvalue.process(lookup_type, params_or_value, connection)
            except EmptyShortCircuit:
                raise EmptyResultSet
        else:
            raise TypeError("'make_atom' expects a Constraint as the first "
                            "item of its 'child' argument.")

        if isinstance(lvalue, tuple):
            # A direct database column lookup.
            field_sql, field_params = self.sql_for_columns(lvalue, compiler, connection, field_internal_type), []
        else:
            # A smart object with an as_sql() method.
            field_sql, field_params = compiler.compile(lvalue)

        is_datetime_field = value_annotation is datetime.datetime
        cast_sql = connection.ops.datetime_cast_sql() if is_datetime_field else '%s'

        if hasattr(params, 'as_sql'):
            extra, params = compiler.compile(params)
            cast_sql = ''
        else:
            extra = ''

        params = field_params + params

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
                for offset in range(0, len(params), max_in_list_size):
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
        elif is_datetime_field and lookup_type in ('month', 'day', 'week_day',
                                                   'hour', 'minute', 'second'):
            tzname = timezone.get_current_timezone_name() if settings.USE_TZ else None
            sql, tz_params = connection.ops.datetime_extract_sql(lookup_type, field_sql, tzname)
            return ('%s = %%s' % sql, tz_params + params)
        elif lookup_type in ('month', 'day', 'week_day'):
            return ('%s = %%s'
                    % connection.ops.date_extract_sql(lookup_type, field_sql), params)
        elif lookup_type == 'isnull':
            assert value_annotation in (True, False), "Invalid value_annotation for isnull"
            return ('%s IS %sNULL' % (field_sql, ('' if value_annotation else 'NOT ')), ())
        elif lookup_type == 'search':
            return (connection.ops.fulltext_search_sql(field_sql), params)
        elif lookup_type in ('regex', 'iregex'):
            return connection.ops.regex_lookup(lookup_type) % (field_sql, cast_sql), params

        raise TypeError('Invalid lookup_type: %r' % lookup_type)

    def sql_for_columns(self, data, qn, connection, internal_type=None):
        """
        Returns the SQL fragment used for the left-hand side of a column
        constraint (for example, the "T1.foo" portion in the clause
        "WHERE ... T1.foo = 6") and a list of parameters.
        """
        table_alias, name, db_type = data
        if table_alias:
            lhs = '%s.%s' % (qn(table_alias), qn(name))
        else:
            lhs = qn(name)
        return connection.ops.field_cast_sql(db_type, internal_type) % lhs

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
            elif isinstance(child, (list, tuple)):
                # tuple starting with Constraint
                child = (child[0].relabeled_clone(change_map),) + child[1:]
                if hasattr(child[3], 'relabeled_clone'):
                    child = (child[0], child[1], child[2]) + (
                        child[3].relabeled_clone(change_map),)
                self.children[pos] = child

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


class EmptyWhere(WhereNode):
    def add(self, data, connector):
        return

    def as_sql(self, compiler=None, connection=None):
        raise EmptyResultSet


class EverythingNode(object):
    """
    A node that matches everything.
    """
    contains_aggregate = False

    def as_sql(self, compiler=None, connection=None):
        return '', []


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


class Constraint(object):
    """
    An object that can be passed to WhereNode.add() and knows how to
    pre-process itself prior to including in the WhereNode.
    """
    def __init__(self, alias, col, field):
        warnings.warn(
            "The Constraint class will be removed in Django 1.9. Use Lookup class instead.",
            RemovedInDjango19Warning)
        self.alias, self.col, self.field = alias, col, field

    def prepare(self, lookup_type, value):
        if self.field and not hasattr(value, 'as_sql'):
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

    def relabeled_clone(self, change_map):
        if self.alias not in change_map:
            return self
        else:
            new = Empty()
            new.__class__ = self.__class__
            new.alias, new.col, new.field = change_map[self.alias], self.col, self.field
            return new


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

        # QuerySet was sent
        if hasattr(query, 'values'):
            if query._db and connection.alias != query._db:
                raise ValueError("Can't do subqueries with queries on different DBs.")
            # Do not override already existing values.
            if not hasattr(query, 'field_names'):
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
