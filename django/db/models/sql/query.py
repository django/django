"""
Create SQL statements for QuerySets.

The code in here encapsulates all of the SQL construction so that QuerySets
themselves do not have to (and could be backed by things other than SQL
databases). The abstraction barrier only works one way: this module has to know
all about the internals of models in order to get the information it needs.
"""

import copy
import re

from django.utils.tree import Node
from django.utils.datastructures import SortedDict
from django.dispatch import dispatcher
from django.db.models import signals
from django.db.models.sql.where import WhereNode, AND, OR
from django.db.models.sql.datastructures import Count, Date
from django.db.models.fields import FieldDoesNotExist, Field, related
from django.contrib.contenttypes import generic
from datastructures import EmptyResultSet

try:
    reversed
except NameError:
    from django.utils.itercompat import reversed    # For python 2.3.

# Valid query types (a dictionary is used for speedy lookups).
QUERY_TERMS = dict([(x, None) for x in (
    'exact', 'iexact', 'contains', 'icontains', 'gt', 'gte', 'lt', 'lte', 'in',
    'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'year',
    'month', 'day', 'isnull', 'search', 'regex', 'iregex',
    )])

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Separator used to split filter strings apart.
LOOKUP_SEP = '__'

# Constants to make looking up tuple values clearer.
# Join lists
TABLE_NAME = 0
RHS_ALIAS = 1
JOIN_TYPE = 2
LHS_ALIAS = 3
LHS_JOIN_COL = 4
RHS_JOIN_COL = 5
# Alias map lists
ALIAS_TABLE = 0
ALIAS_REFCOUNT = 1
ALIAS_JOIN = 2

# How many results to expect from a cursor.execute call
MULTI = 'multi'
SINGLE = 'single'
NONE = None

ORDER_PATTERN = re.compile(r'\?|[-+]?\w+$')
ORDER_DIR = {
    'ASC': ('ASC', 'DESC'),
    'DESC': ('DESC', 'ASC')}

class Empty(object):
    pass

class Query(object):
    """
    A single SQL query.
    """
    # SQL join types. These are part of the class because their string forms
    # vary from database to database and can be customised by a subclass.
    INNER = 'INNER JOIN'
    LOUTER = 'LEFT OUTER JOIN'

    alias_prefix = 'T'

    def __init__(self, model, connection):
        self.model = model
        self.connection = connection
        self.alias_map = {}     # Maps alias to table name
        self.table_map = {}     # Maps table names to list of aliases.
        self.join_map = {}      # Maps join_tuple to list of aliases.
        self.rev_join_map = {}  # Reverse of join_map.
        self.quote_cache = {}
        self.default_cols = True

        # SQL-related attributes
        self.select = []
        self.tables = []    # Aliases in the order they are created.
        self.where = WhereNode()
        self.group_by = []
        self.having = []
        self.order_by = []
        self.low_mark, self.high_mark = 0, None  # Used for offset/limit
        self.distinct = False
        self.select_related = False

        # Arbitrary maximum limit for select_related to prevent infinite
        # recursion. Can be changed by the depth parameter to select_related().
        self.max_depth = 5

        # These are for extensions. The contents are more or less appended
        # verbatim to the appropriate clause.
        self.extra_select = SortedDict()  # Maps col_alias -> col_sql.
        self.extra_tables = []
        self.extra_where = []
        self.extra_params = []
        self.extra_order_by = []

    def __str__(self):
        """
        Returns the query as a string of SQL with the parameter values
        substituted in.

        Parameter values won't necessarily be quoted correctly, since that is
        done by the database interface at execution time.
        """
        sql, params = self.as_sql()
        return sql % params

    def quote_name_unless_alias(self, name):
        """
        A wrapper around connection.ops.quote_name that doesn't quote aliases
        for table names. This avoids problems with some SQL dialects that treat
        quoted strings specially (e.g. PostgreSQL).
        """
        if name in self.quote_cache:
            return self.quote_cache[name]
        if name in self.alias_map and name not in self.table_map:
            self.quote_cache[name] = name
            return name
        r = self.connection.ops.quote_name(name)
        self.quote_cache[name] = r
        return r

    def clone(self, klass=None, **kwargs):
        """
        Creates a copy of the current instance. The 'kwargs' parameter can be
        used by clients to update attributes after copying has taken place.
        """
        obj = Empty()
        obj.__class__ = klass or self.__class__
        obj.model = self.model
        obj.connection = self.connection
        obj.alias_map = copy.deepcopy(self.alias_map)
        obj.table_map = self.table_map.copy()
        obj.join_map = copy.deepcopy(self.join_map)
        obj.rev_join_map = copy.deepcopy(self.rev_join_map)
        obj.quote_cache = {}
        obj.default_cols = self.default_cols
        obj.select = self.select[:]
        obj.tables = self.tables[:]
        obj.where = copy.deepcopy(self.where)
        obj.group_by = self.group_by[:]
        obj.having = self.having[:]
        obj.order_by = self.order_by[:]
        obj.low_mark, obj.high_mark = self.low_mark, self.high_mark
        obj.distinct = self.distinct
        obj.select_related = self.select_related
        obj.max_depth = self.max_depth
        obj.extra_select = self.extra_select.copy()
        obj.extra_tables = self.extra_tables[:]
        obj.extra_where = self.extra_where[:]
        obj.extra_params = self.extra_params[:]
        obj.extra_order_by = self.extra_order_by[:]
        obj.__dict__.update(kwargs)
        return obj

    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        fields = self.model._meta.fields
        resolve_columns = hasattr(self, 'resolve_columns')
        for rows in self.execute_sql(MULTI):
            for row in rows:
                if resolve_columns:
                    row = self.resolve_columns(row, fields)
                yield row

    def get_count(self):
        """
        Performs a COUNT() query using the current filter constraints.
        """
        obj = self.clone()
        obj.clear_ordering(True)
        obj.clear_limits()
        obj.select_related = False
        if obj.distinct and len(obj.select) > 1:
            obj = self.clone(CountQuery, _query=obj, where=WhereNode(),
                    distinct=False)
        obj.add_count_column()
        data = obj.execute_sql(SINGLE)
        if not data:
            return 0
        number = data[0]

        # Apply offset and limit constraints manually, since using LIMIT/OFFSET
        # in SQL doesn't change the COUNT output.
        number = max(0, number - self.low_mark)
        if self.high_mark:
            number = min(number, self.high_mark - self.low_mark)

        return number

    def as_sql(self, with_limits=True):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.

        If 'with_limits' is False, any limit/offset information is not included
        in the query.
        """
        self.pre_sql_setup()
        out_cols = self.get_columns()
        ordering = self.get_ordering()
        # This must come after 'select' and 'ordering' -- see docstring of
        # get_from_clause() for details.
        from_, f_params = self.get_from_clause()
        where, w_params = self.where.as_sql(qn=self.quote_name_unless_alias)

        result = ['SELECT']
        if self.distinct:
            result.append('DISTINCT')
        result.append(', '.join(out_cols))

        result.append('FROM')
        result.extend(from_)
        params = list(f_params)

        if where:
            result.append('WHERE %s' % where)
        if self.extra_where:
            if not where:
                result.append('WHERE')
            else:
                result.append('AND')
            result.append(' AND'.join(self.extra_where))
        params.extend(w_params)

        if self.group_by:
            grouping = self.get_grouping()
            result.append('GROUP BY %s' % ', '.join(grouping))

        if ordering:
            result.append('ORDER BY %s' % ', '.join(ordering))

        if with_limits:
            if self.high_mark:
                result.append('LIMIT %d' % (self.high_mark - self.low_mark))
            if self.low_mark:
                assert self.high_mark, "'offset' is not allowed without 'limit'"
                result.append('OFFSET %d' % self.low_mark)

        params.extend(self.extra_params)
        return ' '.join(result), tuple(params)

    def combine(self, rhs, connection):
        """
        Merge the 'rhs' query into the current one (with any 'rhs' effects
        being applied *after* (that is, "to the right of") anything in the
        current query. 'rhs' is not modified during a call to this function.

        The 'connection' parameter describes how to connect filters from the
        'rhs' query.
        """
        assert self.model == rhs.model, \
                "Cannot combine queries on two different base models."
        assert self.can_filter(), \
                "Cannot combine queries once a slice has been taken."
        assert self.distinct == rhs.distinct, \
            "Cannot combine a unique query with a non-unique query."

        # Work out how to relabel the rhs aliases, if necessary.
        change_map = {}
        used = {}
        conjunction = (connection == AND)
        first = True
        for alias in rhs.tables:
            if not rhs.alias_map[alias][ALIAS_REFCOUNT]:
                # An unused alias.
                continue
            promote = (rhs.alias_map[alias][ALIAS_JOIN][JOIN_TYPE] ==
                    self.LOUTER)
            new_alias = self.join(rhs.rev_join_map[alias],
                    (conjunction and not first), used, promote, not conjunction)
            used[new_alias] = None
            change_map[alias] = new_alias
            first = False

        # So that we don't exclude valid results in an "or" query combination,
        # the first join that is exclusive to the lhs (self) must be converted
        # to an outer join.
        if not conjunction:
            for alias in self.tables[1:]:
                if self.alias_map[alias][ALIAS_REFCOUNT] == 1:
                    self.alias_map[alias][ALIAS_JOIN][JOIN_TYPE] = self.LOUTER
                    break

        # Now relabel a copy of the rhs where-clause and add it to the current
        # one.
        if rhs.where:
            w = copy.deepcopy(rhs.where)
            w.relabel_aliases(change_map)
            if not self.where:
                # Since 'self' matches everything, add an explicit "include
                # everything" (pk is not NULL) where-constraint so that
                # connections between the where clauses won't exclude valid
                # results.
                alias = self.join((None, self.model._meta.db_table, None, None))
                pk = self.model._meta.pk
                self.where.add([alias, pk.column, pk, 'isnull', False], AND)
        elif self.where:
            # rhs has an empty where clause. Make it match everything (see
            # above for reasoning).
            w = WhereNode()
            alias = self.join((None, self.model._meta.db_table, None, None))
            pk = self.model._meta.pk
            w.add([alias, pk.column, pk, 'isnull', False], AND)
        else:
            w = WhereNode()
        self.where.add(w, connection)

        # Selection columns and extra extensions are those provided by 'rhs'.
        self.select = []
        for col in rhs.select:
            if isinstance(col, (list, tuple)):
                self.select.append((change_map.get(col[0], col[0]), col[1]))
            else:
                item = copy.deepcopy(col)
                item.relabel_aliases(change_map)
                self.select.append(item)
        self.extra_select = rhs.extra_select.copy()
        self.extra_tables = rhs.extra_tables[:]
        self.extra_where = rhs.extra_where[:]
        self.extra_params = rhs.extra_params[:]

        # Ordering uses the 'rhs' ordering, unless it has none, in which case
        # the current ordering is used.
        self.order_by = rhs.order_by and rhs.order_by[:] or self.order_by
        self.extra_order_by = (rhs.extra_order_by and rhs.extra_order_by[:] or
                self.extra_order_by)

    def pre_sql_setup(self):
        """
        Does any necessary class setup immediately prior to producing SQL. This
        is for things that can't necessarily be done in __init__ because we
        might not have all the pieces in place at that time.
        """
        if not self.tables:
            self.join((None, self.model._meta.db_table, None, None))
        if self.select_related:
            self.fill_related_selections()

    def get_columns(self):
        """
        Return the list of columns to use in the select statement. If no
        columns have been specified, returns all columns relating to fields in
        the model.
        """
        qn = self.quote_name_unless_alias
        result = []
        aliases = []
        if self.select:
            for col in self.select:
                if isinstance(col, (list, tuple)):
                    r = '%s.%s' % (qn(col[0]), qn(col[1]))
                    result.append(r)
                    aliases.append(r)
                else:
                    result.append(col.as_sql(quote_func=qn))
                    if hasattr(col, 'alias'):
                        aliases.append(col.alias)
        elif self.default_cols:
            table_alias = self.tables[0]
            result = ['%s.%s' % (qn(table_alias), qn(f.column))
                    for f in self.model._meta.fields]
            aliases = result[:]

        result.extend(['(%s) AS %s' % (col, alias)
                for alias, col in self.extra_select.items()])
        aliases.extend(self.extra_select.keys())

        self._select_aliases = dict.fromkeys(aliases)
        return result

    def get_from_clause(self):
        """
        Returns a list of strings that are joined together to go after the
        "FROM" part of the query, as well as any extra parameters that need to
        be included. Sub-classes, can override this to create a from-clause via
        a "select", for example (e.g. CountQuery).

        This should only be called after any SQL construction methods that
        might change the tables we need. This means the select columns and
        ordering must be done first.
        """
        result = []
        qn = self.quote_name_unless_alias
        first = True
        for alias in self.tables:
            if not self.alias_map[alias][ALIAS_REFCOUNT]:
                continue
            join = self.alias_map[alias][ALIAS_JOIN]
            if join:
                name, alias, join_type, lhs, lhs_col, col = join
                alias_str = (alias != name and ' AS %s' % alias or '')
            else:
                join_type = None
                alias_str = ''
                name = alias
            if join_type:
                result.append('%s %s%s ON (%s.%s = %s.%s)'
                        % (join_type, qn(name), alias_str, qn(lhs),
                           qn(lhs_col), qn(alias), qn(col)))
            else:
                connector = not first and ', ' or ''
                result.append('%s%s%s' % (connector, qn(name), alias_str))
            first = False
        extra_tables = []
        for t in self.extra_tables:
            alias, created = self.table_alias(t)
            if created:
                connector = not first and ', ' or ''
                result.append('%s%s' % (connector, alias))
                first = False
        return result, []

    def get_grouping(self):
        """
        Returns a tuple representing the SQL elements in the "group by" clause.
        """
        qn = self.quote_name_unless_alias
        result = []
        for col in self.group_by:
            if isinstance(col, (list, tuple)):
                result.append('%s.%s' % (qn(col[0]), qn(col[1])))
            elif hasattr(col, 'as_sql'):
                result.append(col.as_sql(qn))
            else:
                result.append(str(col))
        return result

    def get_ordering(self):
        """
        Returns a tuple representing the SQL elements in the "order by" clause.

        Determining the ordering SQL can change the tables we need to include,
        so this should be run *before* get_from_clause().
        """
        if self.extra_order_by:
            ordering = self.extra_order_by
        elif self.order_by is None:
            ordering = []
        else:
            # Note that self.order_by can be empty in two ways: [] ("use the
            # default"), which is handled here, and None ("no ordering"), which
            # is handled in the previous test.
            ordering = self.order_by or self.model._meta.ordering
        qn = self.quote_name_unless_alias
        distinct = self.distinct
        select_aliases = self._select_aliases
        result = []
        for field in ordering:
            if field == '?':
                result.append(self.connection.ops.random_function_sql())
                continue
            if isinstance(field, int):
                if field < 0:
                    order = 'DESC'
                    field = -field
                else:
                    order = 'ASC'
                result.append('%s %s' % (field, order))
                continue
            if '.' in field:
                # This came in through an extra(ordering=...) addition. Pass it
                # on verbatim, after mapping the table name to an alias, if
                # necessary.
                col, order = get_order_dir(field)
                table, col = col.split('.', 1)
                elt = '%s.%s' % (qn(self.table_alias(table)[0]), col)
                if not distinct or elt in select_aliases:
                    result.append('%s %s' % (elt, order))
            elif get_order_dir(field)[0] not in self.extra_select:
                # 'col' is of the form 'field' or 'field1__field2' or
                # '-field1__field2__field', etc.
                for table, col, order in self.find_ordering_name(field,
                        self.model._meta):
                    elt = '%s.%s' % (qn(table), qn(col))
                    if not distinct or elt in select_aliases:
                        result.append('%s %s' % (elt, order))
            else:
                col, order = get_order_dir(field)
                elt = qn(col)
                if not distinct or elt in select_aliases:
                    result.append('%s %s' % (elt, order))
        return result

    def find_ordering_name(self, name, opts, alias=None, default_order='ASC'):
        """
        Returns the table alias (the name might be ambiguous, the alias will
        not be) and column name for ordering by the given 'name' parameter.
        The 'name' is of the form 'field1__field2__...__fieldN'.
        """
        name, order = get_order_dir(name, default_order)
        pieces = name.split(LOOKUP_SEP)
        if not alias:
            alias = self.join((None, opts.db_table, None, None))
        field, target, opts, joins, unused2 = self.setup_joins(pieces, opts,
                alias, False)
        alias = joins[-1][-1]
        col = target.column

        # If we get to this point and the field is a relation to another model,
        # append the default ordering for that model.
        if len(joins) > 1 and opts.ordering:
            results = []
            for item in opts.ordering:
                results.extend(self.find_ordering_name(item, opts, alias,
                        order))
            return results

        if alias:
            # We have to do the same "final join" optimisation as in
            # add_filter, since the final column might not otherwise be part of
            # the select set (so we can't order on it).
            join = self.alias_map[alias][ALIAS_JOIN]
            if col == join[RHS_JOIN_COL]:
                self.unref_alias(alias)
                alias = join[LHS_ALIAS]
                col = join[LHS_JOIN_COL]
        return [(alias, col, order)]

    def table_alias(self, table_name, create=False):
        """
        Returns a table alias for the given table_name and whether this is a
        new alias or not.

        If 'create' is true, a new alias is always created. Otherwise, the
        most recently created alias for the table (if one exists) is reused.
        """
        if not create and table_name in self.table_map:
            alias = self.table_map[table_name][-1]
            self.alias_map[alias][ALIAS_REFCOUNT] += 1
            return alias, False

        # Create a new alias for this table.
        if table_name not in self.table_map:
            # The first occurence of a table uses the table name directly.
            alias = table_name
        else:
            alias = '%s%d' % (self.alias_prefix, len(self.alias_map) + 1)
        self.alias_map[alias] = [table_name, 1, None, False]
        self.table_map.setdefault(table_name, []).append(alias)
        self.tables.append(alias)
        return alias, True

    def ref_alias(self, alias):
        """ Increases the reference count for this alias. """
        self.alias_map[alias][ALIAS_REFCOUNT] += 1

    def unref_alias(self, alias):
        """ Decreases the reference count for this alias. """
        self.alias_map[alias][ALIAS_REFCOUNT] -= 1

    def promote_alias(self, alias):
        """ Promotes the join type of an alias to an outer join. """
        self.alias_map[alias][ALIAS_JOIN][JOIN_TYPE] = self.LOUTER

    def join(self, (lhs, table, lhs_col, col), always_create=False,
            exclusions=(), promote=False, outer_if_first=False):
        """
        Returns an alias for a join between 'table' and 'lhs' on the given
        columns, either reusing an existing alias for that join or creating a
        new one.

        'lhs' is either an existing table alias or a table name. If
        'always_create' is True, a new alias is always created, regardless of
        whether one already exists or not.

        If 'exclusions' is specified, it is something satisfying the container
        protocol ("foo in exclusions" must work) and specifies a list of
        aliases that should not be returned, even if they satisfy the join.

        If 'promote' is True, the join type for the alias will be LOUTER (if
        the alias previously existed, the join type will be promoted from INNER
        to LOUTER, if necessary).

        If 'outer_if_first' is True and a new join is created, it will have the
        LOUTER join type. This is used when joining certain types of querysets
        and Q-objects together.
        """
        if lhs is None:
            lhs_table = None
            is_table = False
        elif lhs not in self.alias_map:
            lhs_table = lhs
            is_table = True
        else:
            lhs_table = self.alias_map[lhs][ALIAS_TABLE]
            is_table = False
        t_ident = (lhs_table, table, lhs_col, col)
        if not always_create:
            aliases = self.join_map.get(t_ident)
            if aliases:
                for alias in aliases:
                    if alias not in exclusions:
                        self.ref_alias(alias)
                        if promote:
                            self.alias_map[alias][ALIAS_JOIN][JOIN_TYPE] = \
                                    self.LOUTER
                        return alias
                # If we get to here (no non-excluded alias exists), we'll fall
                # through to creating a new alias.

        # No reuse is possible, so we need a new alias.
        assert not is_table, \
                "Must pass in lhs alias when creating a new join."
        alias, _ = self.table_alias(table, True)
        if promote or outer_if_first:
            join_type = self.LOUTER
        else:
            join_type = self.INNER
        join = [table, alias, join_type, lhs, lhs_col, col]
        if not lhs:
            # Not all tables need to be joined to anything. No join type
            # means the later columns are ignored.
            join[JOIN_TYPE] = None
        self.alias_map[alias][ALIAS_JOIN] = join
        self.join_map.setdefault(t_ident, []).append(alias)
        self.rev_join_map[alias] = t_ident
        return alias

    def fill_related_selections(self, opts=None, root_alias=None, cur_depth=0,
            used=None):
        """
        Fill in the information needed for a select_related query.
        """
        if self.max_depth and cur_depth > self.max_depth:
            # We've recursed too deeply; bail out.
            return
        if not opts:
            opts = self.model._meta
            root_alias = self.tables[0]
            self.select.extend([(root_alias, f.column) for f in opts.fields])
        if not used:
            used = []

        for f in opts.fields:
            if not f.rel or f.null:
                continue
            table = f.rel.to._meta.db_table
            alias = self.join((root_alias, table, f.column,
                    f.rel.get_related_field().column), exclusions=used)
            used.append(alias)
            self.select.extend([(alias, f2.column)
                    for f2 in f.rel.to._meta.fields])
            self.fill_related_selections(f.rel.to._meta, alias, cur_depth + 1,
                    used)

    def add_filter(self, filter_expr, connection=AND, negate=False):
        """
        Add a single filter to the query.
        """
        arg, value = filter_expr
        parts = arg.split(LOOKUP_SEP)
        if not parts:
            raise TypeError("Cannot parse keyword query %r" % arg)

        # Work out the lookup type and remove it from 'parts', if necessary.
        if len(parts) == 1 or parts[-1] not in QUERY_TERMS:
            lookup_type = 'exact'
        else:
            lookup_type = parts.pop()

        # Interpret '__exact=None' as the sql '= NULL'; otherwise, reject all
        # uses of None as a query value.
        # FIXME: Weren't we going to change this so that '__exact=None' was the
        # same as '__isnull=True'? Need to check the conclusion of the mailing
        # list thread.
        if value is None and lookup_type != 'exact':
            raise ValueError("Cannot use None as a query value")
        elif callable(value):
            value = value()

        opts = self.model._meta
        alias = self.join((None, opts.db_table, None, None))

        field, target, unused, join_list, nullable = self.setup_joins(parts,
                opts, alias, (connection == AND))
        col = target.column
        alias = join_list[-1][-1]

        if join_list:
            # An optimization: if the final join is against the same column as
            # we are comparing against, we can go back one step in the join
            # chain and compare against the lhs of the join instead. The result
            # (potentially) involves one less table join.
            join = self.alias_map[alias][ALIAS_JOIN]
            if col == join[RHS_JOIN_COL]:
                self.unref_alias(alias)
                alias = join[LHS_ALIAS]
                col = join[LHS_JOIN_COL]

        if (lookup_type == 'isnull' and value is True):
            # If the comparison is against NULL, we need to use a left outer
            # join when connecting to the previous model. We make that
            # adjustment here. We don't do this unless needed because it's less
            # efficient at the database level.
            self.promote_alias(join_list[-1][0])

        self.where.add([alias, col, field, lookup_type, value], connection)
        if negate:
            flag = False
            for pos, null in enumerate(nullable):
                if not null:
                    continue
                flag = True
                for join in join_list[pos]:
                    self.promote_alias(join)
            self.where.negate()
            if flag:
                self.where.add([alias, col, field, 'isnull', True], OR)

    def add_q(self, q_object):
        """
        Adds a Q-object to the current filter.

        Can also be used to add anything that has an 'add_to_query()' method.
        """
        if hasattr(q_object, 'add_to_query'):
            # Complex custom objects are responsible for adding themselves.
            q_object.add_to_query(self)
            return

        for child in q_object.children:
            if isinstance(child, Node):
                self.where.start_subtree(q_object.connection)
                self.add_q(child)
                self.where.end_subtree()
            else:
                self.add_filter(child, q_object.connection, q_object.negated)

    def setup_joins(self, names, opts, alias, dupe_multis):
        """
        Compute the necessary table joins for the passage through the fields
        given in 'names'. 'opts' is the Options class for the current model
        (which gives the table we are joining to), 'alias' is the alias for the
        table we are joining to. If dupe_multis is True, any many-to-many or
        many-to-one joins will always create a new alias (necessary for
        disjunctive filters).

        Returns the final field involved in the join, the target database
        column (used for any 'where' constraint), the final 'opts' value, the
        list of tables joined and a list indicating whether or not each join
        can be null.
        """
        joins = [[alias]]
        nullable = [False]
        for pos, name in enumerate(names):
            if name == 'pk':
                name = opts.pk.name

            try:
                field, direct, m2m = opts.get_field_by_name(name)
            except FieldDoesNotExist:
                names = opts.get_all_field_names()
                raise TypeError("Cannot resolve keyword %r into field. "
                        "Choices are: %s" % (name, ", ".join(names)))
            cached_data = opts._join_cache.get(name)
            orig_opts = opts

            if direct:
                if m2m:
                    # Many-to-many field defined on the current model.
                    if cached_data:
                        (table1, from_col1, to_col1, table2, from_col2,
                                to_col2, opts, target) = cached_data
                    else:
                        table1 = field.m2m_db_table()
                        from_col1 = opts.pk.column
                        to_col1 = field.m2m_column_name()
                        opts = field.rel.to._meta
                        table2 = opts.db_table
                        from_col2 = field.m2m_reverse_name()
                        to_col2 = opts.pk.column
                        target = opts.pk
                        orig_opts._join_cache[name] = (table1, from_col1,
                                to_col1, table2, from_col2, to_col2, opts,
                                target)

                    int_alias = self.join((alias, table1, from_col1, to_col1),
                            dupe_multis)
                    alias = self.join((int_alias, table2, from_col2, to_col2),
                            dupe_multis)
                    joins.append([int_alias, alias])
                    nullable.append(field.null)
                elif field.rel:
                    # One-to-one or many-to-one field
                    if cached_data:
                        (table, from_col, to_col, opts, target) = cached_data
                    else:
                        opts = field.rel.to._meta
                        target = field.rel.get_related_field()
                        table = opts.db_table
                        from_col = field.column
                        to_col = target.column
                        orig_opts._join_cache[name] = (table, from_col, to_col,
                                opts, target)

                    alias = self.join((alias, table, from_col, to_col))
                    joins.append([alias])
                    nullable.append(field.null)
                else:
                    target = field
                    break
            else:
                orig_field = field
                field = field.field
                nullable.append(True)
                if m2m:
                    # Many-to-many field defined on the target model.
                    if cached_data:
                        (table1, from_col1, to_col1, table2, from_col2,
                                to_col2, opts, target) = cached_data
                    else:
                        table1 = field.m2m_db_table()
                        from_col1 = opts.pk.column
                        to_col1 = field.m2m_reverse_name()
                        opts = orig_field.opts
                        table2 = opts.db_table
                        from_col2 = field.m2m_column_name()
                        to_col2 = opts.pk.column
                        target = opts.pk
                        orig_opts._join_cache[name] = (table1, from_col1,
                                to_col1, table2, from_col2, to_col2, opts,
                                target)

                    int_alias = self.join((alias, table1, from_col1, to_col1),
                            dupe_multis)
                    alias = self.join((int_alias, table2, from_col2, to_col2),
                            dupe_multis)
                    joins.append([int_alias, alias])
                else:
                    # One-to-many field (ForeignKey defined on the target model)
                    if cached_data:
                        (table, from_col, to_col, opts, target) = cached_data
                    else:
                        local_field = opts.get_field_by_name(
                                field.rel.field_name)[0]
                        opts = orig_field.opts
                        table = opts.db_table
                        from_col = local_field.column
                        to_col = field.column
                        target = opts.pk
                        orig_opts._join_cache[name] = (table, from_col, to_col,
                                opts, target)

                    alias = self.join((alias, table, from_col, to_col),
                            dupe_multis)
                    joins.append([alias])

        if pos != len(names) - 1:
            raise TypeError("Join on field %r not permitted." % name)

        return field, target, opts, joins, nullable

    def set_limits(self, low=None, high=None):
        """
        Adjusts the limits on the rows retrieved. We use low/high to set these,
        as it makes it more Pythonic to read and write. When the SQL query is
        created, they are converted to the appropriate offset and limit values.

        Any limits passed in here are applied relative to the existing
        constraints. So low is added to the current low value and both will be
        clamped to any existing high value.
        """
        if high:
            if self.high_mark:
                self.high_mark = min(self.high_mark, self.low_mark + high)
            else:
                self.high_mark = self.low_mark + high
        if low:
            if self.high_mark:
                self.low_mark = min(self.high_mark, self.low_mark + low)
            else:
                self.low_mark = self.low_mark + low

    def clear_limits(self):
        """
        Clears any existing limits.
        """
        self.low_mark, self.high_mark = 0, None

    def can_filter(self):
        """
        Returns True if adding filters to this instance is still possible.

        Typically, this means no limits or offsets have been put on the results.
        """
        return not (self.low_mark or self.high_mark)

    def add_local_columns(self, columns):
        """
        Adds the given column names to the select set, assuming they come from
        the root model (the one given in self.model).
        """
        table = self.model._meta.db_table
        self.select.extend([(table, col) for col in columns])

    def add_ordering(self, *ordering):
        """
        Adds items from the 'ordering' sequence to the query's "order by"
        clause. These items are either field names (not column names) --
        possibly with a direction prefix ('-' or '?') -- or ordinals,
        corresponding to column positions in the 'select' list.
        """
        errors = []
        for item in ordering:
            if not ORDER_PATTERN.match(item):
                errors.append(item)
        if errors:
            raise TypeError('Invalid order_by arguments: %s' % errors)
        self.order_by.extend(ordering)

    def clear_ordering(self, force_empty=False):
        """
        Removes any ordering settings. If 'force_empty' is True, there will be
        no ordering in the resulting query (not even the model's default).
        """
        if force_empty:
            self.order_by = None
        else:
            self.order_by = []
        self.extra_order_by = []

    def add_count_column(self):
        """
        Converts the query to do count(*) or count(distinct(pk)) in order to
        get its size.
        """
        # TODO: When group_by support is added, this needs to be adjusted so
        # that it doesn't totally overwrite the select list.
        if not self.distinct:
            select = Count()
        else:
            opts = self.model._meta
            if not self.select:
                select = Count((self.join((None, opts.db_table, None, None)),
                        opts.pk.column), True)
            else:
                # Because of SQL portability issues, multi-column, distinct
                # counts need a sub-query -- see get_count() for details.
                assert len(self.select) == 1, \
                        "Cannot add count col with multiple cols in 'select'."
                select = Count(self.select[0], True)

            # Distinct handling is done in Count(), so don't do it at this
            # level.
            self.distinct = False
        self.select = [select]
        self.extra_select = SortedDict()

    def execute_sql(self, result_type=MULTI):
        """
        Run the query against the database and returns the result(s). The
        return value is a single data item if result_type is SINGLE, or an
        iterator over the results if the result_type is MULTI.

        result_type is either MULTI (use fetchmany() to retrieve all rows),
        SINGLE (only retrieve a single row), or NONE (no results expected).
        """
        try:
            sql, params = self.as_sql()
        except EmptyResultSet:
            raise StopIteration

        cursor = self.connection.cursor()
        cursor.execute(sql, params)

        if result_type == NONE:
            return

        if result_type == SINGLE:
            return cursor.fetchone()

        # The MULTI case.
        return results_iter(cursor)

class DeleteQuery(Query):
    """
    Delete queries are done through this class, since they are more constrained
    than general queries.
    """
    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        assert len(self.tables) == 1, \
                "Can only delete from one table at a time."
        result = ['DELETE FROM %s' % self.tables[0]]
        where, params = self.where.as_sql()
        result.append('WHERE %s' % where)
        return ' '.join(result), tuple(params)

    def do_query(self, table, where):
        self.tables = [table]
        self.where = where
        self.execute_sql(NONE)

    def delete_batch_related(self, pk_list):
        """
        Set up and execute delete queries for all the objects related to the
        primary key values in pk_list. To delete the objects themselves, use
        the delete_batch() method.

        More than one physical query may be executed if there are a
        lot of values in pk_list.
        """
        cls = self.model
        for related in cls._meta.get_all_related_many_to_many_objects():
            if not isinstance(related.field, generic.GenericRelation):
                for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                    where = WhereNode()
                    where.add((None, related.field.m2m_reverse_name(),
                            related.field, 'in',
                            pk_list[offset : offset+GET_ITERATOR_CHUNK_SIZE]),
                            AND)
                    self.do_query(related.field.m2m_db_table(), where)

        for f in cls._meta.many_to_many:
            w1 = WhereNode()
            if isinstance(f, generic.GenericRelation):
                from django.contrib.contenttypes.models import ContentType
                field = f.rel.to._meta.get_field(f.content_type_field_name)
                w1.add((None, field.column, field, 'exact',
                        ContentType.objects.get_for_model(cls).id), AND)
            for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
                where = WhereNode()
                where.add((None, f.m2m_column_name(), f, 'in',
                        pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]),
                        AND)
                if w1:
                    where.add(w1, AND)
                self.do_query(f.m2m_db_table(), where)

    def delete_batch(self, pk_list):
        """
        Set up and execute delete queries for all the objects in pk_list. This
        should be called after delete_batch_related(), if necessary.

        More than one physical query may be executed if there are a
        lot of values in pk_list.
        """
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            where = WhereNode()
            field = self.model._meta.pk
            where.add((None, field.column, field, 'in',
                    pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]), AND)
            self.do_query(self.model._meta.db_table, where)

class UpdateQuery(Query):
    """
    Represents an "update" SQL query.
    """
    def __init__(self, *args, **kwargs):
        super(UpdateQuery, self).__init__(*args, **kwargs)
        self.values = []

    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        assert len(self.tables) == 1, \
                "Can only update one table at a time."
        result = ['UPDATE %s' % self.tables[0]]
        result.append('SET')
        qn = self.quote_name_unless_alias
        values = ['%s = %s' % (qn(v[0]), v[1]) for v in self.values]
        result.append(', '.join(values))
        where, params = self.where.as_sql()
        result.append('WHERE %s' % where)
        return ' '.join(result), tuple(params)

    def do_query(self, table, values, where):
        self.tables = [table]
        self.values = values
        self.where = where
        self.execute_sql(NONE)

    def clear_related(self, related_field, pk_list):
        """
        Set up and execute an update query that clears related entries for the
        keys in pk_list.

        This is used by the QuerySet.delete_objects() method.
        """
        for offset in range(0, len(pk_list), GET_ITERATOR_CHUNK_SIZE):
            where = WhereNode()
            f = self.model._meta.pk
            where.add((None, f.column, f, 'in',
                    pk_list[offset : offset + GET_ITERATOR_CHUNK_SIZE]),
                    AND)
            values = [(related_field.column, 'NULL')]
            self.do_query(self.model._meta.db_table, values, where)

class DateQuery(Query):
    """
    A DateQuery is a normal query, except that it specifically selects a single
    date field. This requires some special handling when converting the results
    back to Python objects, so we put it in a separate class.
    """
    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        resolve_columns = hasattr(self, 'resolve_columns')
        if resolve_columns:
            from django.db.models.fields import DateTimeField
            fields = [DateTimeField()]
        else:
            from django.db.backends.util import typecast_timestamp
            needs_string_cast = self.connection.features.needs_datetime_string_cast

        for rows in self.execute_sql(MULTI):
            for row in rows:
                date = row[0]
                if resolve_columns:
                    date = self.resolve_columns([date], fields)[0]
                elif needs_string_cast:
                    date = typecast_timestamp(str(date))
                yield date

    def add_date_select(self, column, lookup_type, order='ASC'):
        """
        Converts the query into a date extraction query.
        """
        alias = self.join((None, self.model._meta.db_table, None, None))
        select = Date((alias, column), lookup_type,
                self.connection.ops.date_trunc_sql)
        self.select = [select]
        self.order_by = order == 'ASC' and [1] or [-1]
        if self.connection.features.allows_group_by_ordinal:
            self.group_by = [1]
        else:
            self.group_by = [select]

class CountQuery(Query):
    """
    A CountQuery knows how to take a normal query which would select over
    multiple distinct columns and turn it into SQL that can be used on a
    variety of backends (it requires a select in the FROM clause).
    """
    def get_from_clause(self):
        result, params = self._query.as_sql()
        return ['(%s) AS A1' % result], params

    def get_ordering(self):
        return ()

def get_order_dir(field, default='ASC'):
    """
    Returns the field name and direction for an order specification. For
    example, '-foo' is returned as ('foo', 'DESC').

    The 'default' param is used to indicate which way no prefix (or a '+'
    prefix) should sort. The '-' prefix always sorts the opposite way.
    """
    dirn = ORDER_DIR[default]
    if field[0] == '-':
        return field[1:], dirn[1]
    return field, dirn[0]

def results_iter(cursor):
    while 1:
        rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
        if not rows:
            raise StopIteration
        yield rows

def setup_join_cache(sender):
    """
    The information needed to join between model fields is something that is
    invariant over the life of the model, so we cache it in the model's Options
    class, rather than recomputing it all the time.

    This method initialises the (empty) cache when the model is created.
    """
    sender._meta._join_cache = {}

dispatcher.connect(setup_join_cache, signal=signals.class_prepared)

