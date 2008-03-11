"""
Create SQL statements for QuerySets.

The code in here encapsulates all of the SQL construction so that QuerySets
themselves do not have to (and could be backed by things other than SQL
databases). The abstraction barrier only works one way: this module has to know
all about the internals of models in order to get the information it needs.
"""

import copy

from django.utils.tree import Node
from django.utils.datastructures import SortedDict
from django.dispatch import dispatcher
from django.db.models import signals
from django.db.models.sql.where import WhereNode, EverythingNode, AND, OR
from django.db.models.sql.datastructures import Count
from django.db.models.fields import FieldDoesNotExist
from django.core.exceptions import FieldError
from datastructures import EmptyResultSet, Empty
from constants import *

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback

__all__ = ['Query']

class Query(object):
    """
    A single SQL query.
    """
    # SQL join types. These are part of the class because their string forms
    # vary from database to database and can be customised by a subclass.
    INNER = 'INNER JOIN'
    LOUTER = 'LEFT OUTER JOIN'

    alias_prefix = 'T'
    query_terms = QUERY_TERMS

    def __init__(self, model, connection, where=WhereNode):
        self.model = model
        self.connection = connection
        self.alias_map = {}     # Maps alias to table name
        self.table_map = {}     # Maps table names to list of aliases.
        self.join_map = {}      # Maps join_tuple to list of aliases.
        self.rev_join_map = {}  # Reverse of join_map.
        self.quote_cache = {}
        self.default_cols = True
        self.default_ordering = True
        self.standard_ordering = True
        self.start_meta = None

        # SQL-related attributes
        self.select = []
        self.tables = []    # Aliases in the order they are created.
        self.where = where()
        self.where_class = where
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

    def __deepcopy__(self, memo):
        result= self.clone()
        memo[id(self)] = result
        return result

    def get_meta(self):
        """
        Returns the Options instance (the model._meta) from which to start
        processing. Normally, this is self.model._meta, but it can change.
        """
        if self.start_meta:
            return self.start_meta
        return self.model._meta

    def quote_name_unless_alias(self, name):
        """
        A wrapper around connection.ops.quote_name that doesn't quote aliases
        for table names. This avoids problems with some SQL dialects that treat
        quoted strings specially (e.g. PostgreSQL).
        """
        if name in self.quote_cache:
            return self.quote_cache[name]
        if ((name in self.alias_map and name not in self.table_map) or
                name in self.extra_select):
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
        obj.default_ordering = self.default_ordering
        obj.standard_ordering = self.standard_ordering
        obj.start_meta = self.start_meta
        obj.select = self.select[:]
        obj.tables = self.tables[:]
        obj.where = copy.deepcopy(self.where)
        obj.where_class = self.where_class
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
        if hasattr(obj, '_setup_query'):
            obj._setup_query()
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
        from subqueries import CountQuery
        obj = self.clone()
        obj.clear_ordering(True)
        obj.clear_limits()
        obj.select_related = False
        if obj.distinct and len(obj.select) > 1:
            obj = self.clone(CountQuery, _query=obj, where=self.where_class(),
                    distinct=False)
            obj.select = []
            obj.extra_select = SortedDict()
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

        # FIXME: Pull this out to make life easier for Oracle et al.
        if with_limits:
            if self.high_mark:
                result.append('LIMIT %d' % (self.high_mark - self.low_mark))
            if self.low_mark:
                if not self.high_mark:
                    val = self.connection.ops.no_limit_value()
                    if val:
                        result.append('LIMIT %d' % val)
                result.append('OFFSET %d' % self.low_mark)

        params.extend(self.extra_params)
        return ' '.join(result), tuple(params)

    def combine(self, rhs, connector):
        """
        Merge the 'rhs' query into the current one (with any 'rhs' effects
        being applied *after* (that is, "to the right of") anything in the
        current query. 'rhs' is not modified during a call to this function.

        The 'connector' parameter describes how to connect filters from the
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
        conjunction = (connector == AND)
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
                # everything" where-constraint so that connections between the
                # where clauses won't exclude valid results.
                self.where.add(EverythingNode(), AND)
        elif self.where:
            # rhs has an empty where clause.
            w = self.where_class()
            w.add(EverythingNode(), AND)
        else:
            w = self.where_class()
        self.where.add(w, connector)

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
            root_pk = self.model._meta.pk.column
            seen = {None: table_alias}
            for field, model in self.model._meta.get_fields_with_model():
                if model not in seen:
                    seen[model] = self.join((table_alias, model._meta.db_table,
                            root_pk, model._meta.pk.column))
                result.append('%s.%s' % (qn(seen[model]), qn(field.column)))
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
            if join_type and not first:
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
        # FIXME: It's an SQL-92 requirement that all ordering columns appear as
        # output columns in the query (in the select statement) or be ordinals.
        # We don't enforce that here, but we should (by adding to the select
        # columns), for portability.
        if self.extra_order_by:
            ordering = self.extra_order_by
        elif not self.default_ordering:
            ordering = []
        else:
            ordering = self.order_by or self.model._meta.ordering
        qn = self.quote_name_unless_alias
        distinct = self.distinct
        select_aliases = self._select_aliases
        result = []
        if self.standard_ordering:
            asc, desc = ORDER_DIR['ASC']
        else:
            asc, desc = ORDER_DIR['DESC']
        for field in ordering:
            if field == '?':
                result.append(self.connection.ops.random_function_sql())
                continue
            if isinstance(field, int):
                if field < 0:
                    order = desc
                    field = -field
                else:
                    order = asc
                result.append('%s %s' % (field, order))
                continue
            if '.' in field:
                # This came in through an extra(ordering=...) addition. Pass it
                # on verbatim, after mapping the table name to an alias, if
                # necessary.
                col, order = get_order_dir(field, asc)
                table, col = col.split('.', 1)
                elt = '%s.%s' % (qn(self.table_alias(table)[0]), col)
                if not distinct or elt in select_aliases:
                    result.append('%s %s' % (elt, order))
            elif get_order_dir(field)[0] not in self.extra_select:
                # 'col' is of the form 'field' or 'field1__field2' or
                # '-field1__field2__field', etc.
                for table, col, order in self.find_ordering_name(field,
                        self.model._meta, default_order=asc):
                    elt = '%s.%s' % (qn(table), qn(col))
                    if not distinct or elt in select_aliases:
                        result.append('%s %s' % (elt, order))
            else:
                col, order = get_order_dir(field, asc)
                elt = qn(col)
                if not distinct or elt in select_aliases:
                    result.append('%s %s' % (elt, order))
        return result

    def find_ordering_name(self, name, opts, alias=None, default_order='ASC',
            already_seen=None):
        """
        Returns the table alias (the name might be ambiguous, the alias will
        not be) and column name for ordering by the given 'name' parameter.
        The 'name' is of the form 'field1__field2__...__fieldN'.
        """
        name, order = get_order_dir(name, default_order)
        pieces = name.split(LOOKUP_SEP)
        if not alias:
            alias = self.get_initial_alias()
        result = self.setup_joins(pieces, opts, alias, False, False)
        if isinstance(result, int):
            raise FieldError("Cannot order by many-valued field: '%s'" % name)
        field, target, opts, joins = result
        alias = joins[-1][-1]
        col = target.column

        # If we get to this point and the field is a relation to another model,
        # append the default ordering for that model.
        if len(joins) > 1 and opts.ordering:
            # Firstly, avoid infinite loops.
            if not already_seen:
                already_seen = {}
            join_tuple = tuple([tuple(j) for j in joins])
            if join_tuple in already_seen:
                raise FieldError('Infinite loop caused by ordering.')
            already_seen[join_tuple] = True

            results = []
            for item in opts.ordering:
                results.extend(self.find_ordering_name(item, opts, alias,
                        order, already_seen))
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
        """
        Promotes the join type of an alias to an outer join if it's possible
        for the join to contain NULL values on the left.
        """
        if self.alias_map[alias][ALIAS_NULLABLE]:
            self.alias_map[alias][ALIAS_JOIN][JOIN_TYPE] = self.LOUTER

    def change_alias(self, old_alias, new_alias):
        """
        Changes old_alias to new_alias, relabelling any references to it in
        select columns and the where clause.
        """
        assert new_alias not in self.alias_map

        # 1. Update references in "select" and "where".
        change_map = {old_alias: new_alias}
        self.where.relabel_aliases(change_map)
        for pos, col in enumerate(self.select):
            if isinstance(col, (list, tuple)):
                if col[0] == old_alias:
                    self.select[pos] = (new_alias, col[1])
            else:
                col.relabel_aliases(change_map)

        # 2. Rename the alias in the internal table/alias datastructures.
        alias_data = self.alias_map[old_alias]
        alias_data[ALIAS_JOIN][RHS_ALIAS] = new_alias
        table_aliases = self.table_map[alias_data[ALIAS_TABLE]]
        for pos, alias in enumerate(table_aliases):
            if alias == old_alias:
                table_aliases[pos] = new_alias
                break
        self.alias_map[new_alias] = alias_data
        del self.alias_map[old_alias]
        for pos, alias in enumerate(self.tables):
            if alias == old_alias:
                self.tables[pos] = new_alias
                break

        # 3. Update any joins that refer to the old alias.
        for data in self.alias_map.values():
            if data[ALIAS_JOIN][LHS_ALIAS] == old_alias:
                data[ALIAS_JOIN][LHS_ALIAS] = new_alias

    def get_initial_alias(self):
        """
        Returns the first alias for this query, after increasing its reference
        count.
        """
        if self.tables:
            alias = self.tables[0]
            self.ref_alias(alias)
        else:
            alias = self.join((None, self.model._meta.db_table, None, None))
        return alias

    def count_active_tables(self):
        """
        Returns the number of tables in this query with a non-zero reference
        count.
        """
        return len([1 for o in self.alias_map.values() if o[ALIAS_REFCOUNT]])

    def join(self, connection, always_create=False, exclusions=(),
            promote=False, outer_if_first=False, nullable=False):
        """
        Returns an alias for the join in 'connection', either reusing an
        existing alias for that join or creating a new one. 'connection' is a
        tuple (lhs, table, lhs_col, col) where 'lhs' is either an existing
        table alias or a table name. The join correspods to the SQL equivalent
        of::

            lhs.lhs_col = table.col

        If 'always_create' is True, a new alias is always created, regardless
        of whether one already exists or not.

        If 'exclusions' is specified, it is something satisfying the container
        protocol ("foo in exclusions" must work) and specifies a list of
        aliases that should not be returned, even if they satisfy the join.

        If 'promote' is True, the join type for the alias will be LOUTER (if
        the alias previously existed, the join type will be promoted from INNER
        to LOUTER, if necessary).

        If 'outer_if_first' is True and a new join is created, it will have the
        LOUTER join type. This is used when joining certain types of querysets
        and Q-objects together.

        If 'nullable' is True, the join can potentially involve NULL values and
        is a candidate for promotion (to "left outer") when combining querysets.
        """
        lhs, table, lhs_col, col = connection
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
                        if promote and self.alias_map[alias][ALIAS_NULLABLE]:
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
        self.alias_map[alias][ALIAS_NULLABLE] = nullable
        self.join_map.setdefault(t_ident, []).append(alias)
        self.rev_join_map[alias] = t_ident
        return alias

    def fill_related_selections(self, opts=None, root_alias=None, cur_depth=1,
            used=None, requested=None, restricted=None):
        """
        Fill in the information needed for a select_related query. The current
        depth is measured as the number of connections away from the root model
        (for example, cur_depth=1 means we are looking at models with direct
        connections to the root model).
        """
        if not restricted and self.max_depth and cur_depth > self.max_depth:
            # We've recursed far enough; bail out.
            return
        if not opts:
            opts = self.get_meta()
            root_alias = self.tables[0]
            self.select.extend([(root_alias, f.column) for f in opts.fields])
        if not used:
            used = []

        # Setup for the case when only particular related fields should be
        # included in the related selection.
        if requested is None and restricted is not False:
            if isinstance(self.select_related, dict):
                requested = self.select_related
                restricted = True
            else:
                restricted = False

        for f in opts.fields:
            if (not f.rel or (restricted and f.name not in requested) or
                    (not restricted and f.null)):
                continue
            table = f.rel.to._meta.db_table
            alias = self.join((root_alias, table, f.column,
                    f.rel.get_related_field().column), exclusions=used)
            used.append(alias)
            self.select.extend([(alias, f2.column)
                    for f2 in f.rel.to._meta.fields])
            if restricted:
                next = requested.get(f.name, {})
            else:
                next = False
            self.fill_related_selections(f.rel.to._meta, alias, cur_depth + 1,
                    used, next, restricted)

    def add_filter(self, filter_expr, connector=AND, negate=False, trim=False,
            merge_negated=False):
        """
        Add a single filter to the query. The 'filter_expr' is a pair:
        (filter_string, value). E.g. ('name__contains', 'fred')

        If 'negate' is True, this is an exclude() filter. If 'trim' is True, we
        automatically trim the final join group (used internally when
        constructing nested queries).

        If 'merge_negated' is True, this negated filter will be merged with the
        existing negated where node (if it exists). This is used when
        constructing an exclude filter from combined subfilters.
        """
        arg, value = filter_expr
        parts = arg.split(LOOKUP_SEP)
        if not parts:
            raise FieldError("Cannot parse keyword query %r" % arg)

        # Work out the lookup type and remove it from 'parts', if necessary.
        if len(parts) == 1 or parts[-1] not in self.query_terms:
            lookup_type = 'exact'
        else:
            lookup_type = parts.pop()

        # Interpret '__exact=None' as the sql 'is NULL'; otherwise, reject all
        # uses of None as a query value.
        if value is None:
            if lookup_type != 'exact':
                raise ValueError("Cannot use None as a query value")
            lookup_type = 'isnull'
            value = True
        elif callable(value):
            value = value()

        opts = self.get_meta()
        alias = self.get_initial_alias()
        allow_many = trim or not negate

        result = self.setup_joins(parts, opts, alias, (connector == AND),
                allow_many)
        if isinstance(result, int):
            self.split_exclude(filter_expr, LOOKUP_SEP.join(parts[:result]))
            return
        field, target, opts, join_list = result
        if trim and len(join_list) > 1:
            extra = join_list[-1]
            join_list = join_list[:-1]
            col = self.alias_map[extra[0]][ALIAS_JOIN][LHS_JOIN_COL]
            for alias in extra:
                self.unref_alias(alias)
        else:
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
                if len(join_list[-1]) == 1:
                    join_list = join_list[:-1]
                else:
                    join_list[-1] = join_list[-1][:-1]

        if (lookup_type == 'isnull' and value is True and not negate and
                (len(join_list) > 1 or len(join_list[0]) > 1)):
            # If the comparison is against NULL, we need to use a left outer
            # join when connecting to the previous model. We make that
            # adjustment here. We don't do this unless needed as it's less
            # efficient at the database level.
            self.promote_alias(join_list[-1][0])

        if connector == OR:
            # Some joins may need to be promoted when adding a new filter to a
            # disjunction. We walk the list of new joins and where it diverges
            # from any previous joins (ref count is 1 in the table list), we
            # make the new additions (and any existing ones not used in the new
            # join list) an outer join.
            join_it = nested_iter(join_list)
            table_it = iter(self.tables)
            join_it.next(), table_it.next()
            for join in join_it:
                table = table_it.next()
                if join == table and self.alias_map[join][ALIAS_REFCOUNT] > 1:
                    continue
                self.promote_alias(join)
                if table != join:
                    self.promote_alias(table)
                break
            for join in join_it:
                self.promote_alias(join)
            for table in table_it:
                # Some of these will have been promoted from the join_list, but
                # that's harmless.
                self.promote_alias(table)

        entry = [alias, col, field, lookup_type, value]
        if merge_negated:
            # This case is when we're doing the Q2 filter in exclude(Q1, Q2).
            # It's different from exclude(Q1).exclude(Q2).
            for node in self.where.children:
                if getattr(node, 'negated', False):
                    node.add(entry, connector)
                    merged = True
                    break
        else:
            self.where.add(entry, connector)
            merged = False

        if negate:
            count = 0
            for join in join_list:
                count += len(join)
                for alias in join:
                    self.promote_alias(alias)
            if not merged:
                self.where.negate()
            if count > 1 and lookup_type != 'isnull':
                j_col = self.alias_map[alias][ALIAS_JOIN][RHS_JOIN_COL]
                entry = Node([[alias, j_col, None, 'isnull', True]])
                entry.negate()
                self.where.add(entry, AND)

    def add_q(self, q_object):
        """
        Adds a Q-object to the current filter.

        Can also be used to add anything that has an 'add_to_query()' method.
        """
        if hasattr(q_object, 'add_to_query'):
            # Complex custom objects are responsible for adding themselves.
            q_object.add_to_query(self)
            return

        if self.where and q_object.connector != AND and len(q_object) > 1:
            self.where.start_subtree(AND)
            subtree = True
        else:
            subtree = False
        connector = AND
        merge = False
        for child in q_object.children:
            if isinstance(child, Node):
                self.where.start_subtree(connector)
                self.add_q(child)
                self.where.end_subtree()
            else:
                self.add_filter(child, connector, q_object.negated,
                        merge_negated=merge)
                merge = q_object.negated
            connector = q_object.connector
        if subtree:
            self.where.end_subtree()

    def setup_joins(self, names, opts, alias, dupe_multis, allow_many=True):
        """
        Compute the necessary table joins for the passage through the fields
        given in 'names'. 'opts' is the Options class for the current model
        (which gives the table we are joining to), 'alias' is the alias for the
        table we are joining to. If dupe_multis is True, any many-to-many or
        many-to-one joins will always create a new alias (necessary for
        disjunctive filters).

        Returns the final field involved in the join, the target database
        column (used for any 'where' constraint), the final 'opts' value and the
        list of tables joined.
        """
        joins = [[alias]]
        used = set()
        for pos, name in enumerate(names):
            used.update(joins[-1])
            if name == 'pk':
                name = opts.pk.name

            try:
                field, model, direct, m2m = opts.get_field_by_name(name)
            except FieldDoesNotExist:
                names = opts.get_all_field_names()
                raise FieldError("Cannot resolve keyword %r into field. "
                        "Choices are: %s" % (name, ", ".join(names)))
            if not allow_many and (m2m or not direct):
                for join in joins:
                    for alias in join:
                        self.unref_alias(alias)
                return pos + 1
            if model:
                # The field lives on a base class of the current model.
                alias_list = []
                for int_model in opts.get_base_chain(model):
                    lhs_col = opts.parents[int_model].column
                    opts = int_model._meta
                    alias = self.join((alias, opts.db_table, lhs_col,
                            opts.pk.column), exclusions=used)
                    alias_list.append(alias)
                joins.append(alias_list)
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
                            dupe_multis, used, nullable=True)
                    alias = self.join((int_alias, table2, from_col2, to_col2),
                            dupe_multis, used, nullable=True)
                    joins.append([int_alias, alias])
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

                    alias = self.join((alias, table, from_col, to_col),
                            exclusions=used, nullable=field.null)
                    joins.append([alias])
                else:
                    # Non-relation fields.
                    target = field
                    break
            else:
                orig_field = field
                field = field.field
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
                            dupe_multis, used, nullable=True)
                    alias = self.join((int_alias, table2, from_col2, to_col2),
                            dupe_multis, used, nullable=True)
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
                            dupe_multis, used, nullable=True)
                    joins.append([alias])

        if pos != len(names) - 1:
            raise FieldError("Join on field %r not permitted." % name)

        return field, target, opts, joins

    def split_exclude(self, filter_expr, prefix):
        """
        When doing an exclude against any kind of N-to-many relation, we need
        to use a subquery. This method constructs the nested query, given the
        original exclude filter (filter_expr) and the portion up to the first
        N-to-many relation field.
        """
        query = Query(self.model, self.connection)
        query.add_filter(filter_expr)
        query.set_start(prefix)
        query.clear_ordering(True)
        self.add_filter(('%s__in' % prefix, query), negate=True, trim=True)

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
        for alias in self.tables:
            if self.alias_map[alias][ALIAS_REFCOUNT]:
                break
        else:
            alias = self.get_initial_alias()
        self.select.extend([(alias, col) for col in columns])

    def add_ordering(self, *ordering):
        """
        Adds items from the 'ordering' sequence to the query's "order by"
        clause. These items are either field names (not column names) --
        possibly with a direction prefix ('-' or '?') -- or ordinals,
        corresponding to column positions in the 'select' list.

        If 'ordering' is empty, all ordering is cleared from the query.
        """
        errors = []
        for item in ordering:
            if not ORDER_PATTERN.match(item):
                errors.append(item)
        if errors:
            raise FieldError('Invalid order_by arguments: %s' % errors)
        if ordering:
            self.order_by.extend(ordering)
        else:
            self.default_ordering = False

    def clear_ordering(self, force_empty=False):
        """
        Removes any ordering settings. If 'force_empty' is True, there will be
        no ordering in the resulting query (not even the model's default).
        """
        self.order_by = []
        self.extra_order_by = []
        if force_empty:
            self.default_ordering = False

    def add_count_column(self):
        """
        Converts the query to do count(...) or count(distinct(pk)) in order to
        get its size.
        """
        # TODO: When group_by support is added, this needs to be adjusted so
        # that it doesn't totally overwrite the select list.
        if not self.distinct:
            if not self.select:
                select = Count()
            else:
                assert len(self.select) == 1, \
                        "Cannot add count col with multiple cols in 'select': %r" % self.select
                select = Count(self.select[0])
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

    def add_select_related(self, fields):
        """
        Sets up the select_related data structure so that we only select
        certain related models (as opposed to all models, when
        self.select_related=True).
        """
        field_dict = {}
        for field in fields:
            d = field_dict
            for part in field.split(LOOKUP_SEP):
                d = d.setdefault(part, {})
        self.select_related = field_dict

    def set_start(self, start):
        """
        Sets the table from which to start joining. The start position is
        specified by the related attribute from the base model. This will
        automatically set to the select column to be the column linked from the
        previous table.

        This method is primarily for internal use and the error checking isn't
        as friendly as add_filter(). Mostly useful for querying directly
        against the join table of many-to-many relation in a subquery.
        """
        opts = self.model._meta
        alias = self.get_initial_alias()
        field, col, opts, joins = self.setup_joins(start.split(LOOKUP_SEP),
                opts, alias, False)
        alias = joins[-1][0]
        self.select = [(alias, self.alias_map[alias][ALIAS_JOIN][RHS_JOIN_COL])]
        self.start_meta = opts

        # The call to setup_joins add an extra reference to everything in
        # joins. So we need to unref everything once, and everything prior to
        # the final join a second time.
        for join in joins[:-1]:
            for alias in join:
                self.unref_alias(alias)
                self.unref_alias(alias)
        for alias in joins[-1]:
            self.unref_alias(alias)

    def execute_sql(self, result_type=MULTI):
        """
        Run the query against the database and returns the result(s). The
        return value is a single data item if result_type is SINGLE, or an
        iterator over the results if the result_type is MULTI.

        result_type is either MULTI (use fetchmany() to retrieve all rows),
        SINGLE (only retrieve a single row), or None (no results expected, but
        the cursor is returned, since it's used by subclasses such as
        InsertQuery).
        """
        try:
            sql, params = self.as_sql()
            if not sql:
                raise EmptyResultSet
        except EmptyResultSet:
            if result_type == MULTI:
                raise StopIteration
            else:
                return

        cursor = self.connection.cursor()
        cursor.execute(sql, params)

        if result_type is None:
            return cursor

        if result_type == SINGLE:
            return cursor.fetchone()

        # The MULTI case.
        return results_iter(cursor)

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
    """
    An iterator over the result set that returns a chunk of rows at a time.
    """
    while 1:
        rows = cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)
        if not rows:
            raise StopIteration
        yield rows

def nested_iter(nested):
    """
    An iterator over a sequence of sequences. Each element is returned in turn.
    Only handles one level of nesting, since that's all we need here.
    """
    for seq in nested:
        for elt in seq:
            yield elt

def setup_join_cache(sender):
    """
    The information needed to join between model fields is something that is
    invariant over the life of the model, so we cache it in the model's Options
    class, rather than recomputing it all the time.

    This method initialises the (empty) cache when the model is created.
    """
    sender._meta._join_cache = {}

dispatcher.connect(setup_join_cache, signal=signals.class_prepared)

