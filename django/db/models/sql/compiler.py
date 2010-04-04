from django.core.exceptions import FieldError
from django.db import connections
from django.db.backends.util import truncate_name
from django.db.models.sql.constants import *
from django.db.models.sql.datastructures import EmptyResultSet
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.sql.query import get_proxied_model, get_order_dir, \
     select_related_descend, Query

class SQLCompiler(object):
    def __init__(self, query, connection, using):
        self.query = query
        self.connection = connection
        self.using = using
        self.quote_cache = {}

    def pre_sql_setup(self):
        """
        Does any necessary class setup immediately prior to producing SQL. This
        is for things that can't necessarily be done in __init__ because we
        might not have all the pieces in place at that time.
        """
        if not self.query.tables:
            self.query.join((None, self.query.model._meta.db_table, None, None))
        if (not self.query.select and self.query.default_cols and not
                self.query.included_inherited_models):
            self.query.setup_inherited_models()
        if self.query.select_related and not self.query.related_select_cols:
            self.fill_related_selections()

    def quote_name_unless_alias(self, name):
        """
        A wrapper around connection.ops.quote_name that doesn't quote aliases
        for table names. This avoids problems with some SQL dialects that treat
        quoted strings specially (e.g. PostgreSQL).
        """
        if name in self.quote_cache:
            return self.quote_cache[name]
        if ((name in self.query.alias_map and name not in self.query.table_map) or
                name in self.query.extra_select):
            self.quote_cache[name] = name
            return name
        r = self.connection.ops.quote_name(name)
        self.quote_cache[name] = r
        return r

    def as_sql(self, with_limits=True, with_col_aliases=False):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.

        If 'with_limits' is False, any limit/offset information is not included
        in the query.
        """
        self.pre_sql_setup()
        out_cols = self.get_columns(with_col_aliases)
        ordering, ordering_group_by = self.get_ordering()

        # This must come after 'select' and 'ordering' -- see docstring of
        # get_from_clause() for details.
        from_, f_params = self.get_from_clause()

        qn = self.quote_name_unless_alias

        where, w_params = self.query.where.as_sql(qn=qn, connection=self.connection)
        having, h_params = self.query.having.as_sql(qn=qn, connection=self.connection)
        params = []
        for val in self.query.extra_select.itervalues():
            params.extend(val[1])

        result = ['SELECT']
        if self.query.distinct:
            result.append('DISTINCT')
        result.append(', '.join(out_cols + self.query.ordering_aliases))

        result.append('FROM')
        result.extend(from_)
        params.extend(f_params)

        if where:
            result.append('WHERE %s' % where)
            params.extend(w_params)

        grouping, gb_params = self.get_grouping()
        if grouping:
            if ordering:
                # If the backend can't group by PK (i.e., any database
                # other than MySQL), then any fields mentioned in the
                # ordering clause needs to be in the group by clause.
                if not self.connection.features.allows_group_by_pk:
                    for col, col_params in ordering_group_by:
                        if col not in grouping:
                            grouping.append(str(col))
                            gb_params.extend(col_params)
            else:
                ordering = self.connection.ops.force_no_ordering()
            result.append('GROUP BY %s' % ', '.join(grouping))
            params.extend(gb_params)

        if having:
            result.append('HAVING %s' % having)
            params.extend(h_params)

        if ordering:
            result.append('ORDER BY %s' % ', '.join(ordering))

        if with_limits:
            if self.query.high_mark is not None:
                result.append('LIMIT %d' % (self.query.high_mark - self.query.low_mark))
            if self.query.low_mark:
                if self.query.high_mark is None:
                    val = self.connection.ops.no_limit_value()
                    if val:
                        result.append('LIMIT %d' % val)
                result.append('OFFSET %d' % self.query.low_mark)

        return ' '.join(result), tuple(params)

    def as_nested_sql(self):
        """
        Perform the same functionality as the as_sql() method, returning an
        SQL string and parameters. However, the alias prefixes are bumped
        beforehand (in a copy -- the current query isn't changed), and any
        ordering is removed if the query is unsliced.

        Used when nesting this query inside another.
        """
        obj = self.query.clone()
        if obj.low_mark == 0 and obj.high_mark is None:
            # If there is no slicing in use, then we can safely drop all ordering
            obj.clear_ordering(True)
        obj.bump_prefix()
        return obj.get_compiler(connection=self.connection).as_sql()

    def get_columns(self, with_aliases=False):
        """
        Returns the list of columns to use in the select statement. If no
        columns have been specified, returns all columns relating to fields in
        the model.

        If 'with_aliases' is true, any column names that are duplicated
        (without the table names) are given unique aliases. This is needed in
        some cases to avoid ambiguity with nested queries.
        """
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        result = ['(%s) AS %s' % (col[0], qn2(alias)) for alias, col in self.query.extra_select.iteritems()]
        aliases = set(self.query.extra_select.keys())
        if with_aliases:
            col_aliases = aliases.copy()
        else:
            col_aliases = set()
        if self.query.select:
            only_load = self.deferred_to_columns()
            for col in self.query.select:
                if isinstance(col, (list, tuple)):
                    alias, column = col
                    table = self.query.alias_map[alias][TABLE_NAME]
                    if table in only_load and col not in only_load[table]:
                        continue
                    r = '%s.%s' % (qn(alias), qn(column))
                    if with_aliases:
                        if col[1] in col_aliases:
                            c_alias = 'Col%d' % len(col_aliases)
                            result.append('%s AS %s' % (r, c_alias))
                            aliases.add(c_alias)
                            col_aliases.add(c_alias)
                        else:
                            result.append('%s AS %s' % (r, qn2(col[1])))
                            aliases.add(r)
                            col_aliases.add(col[1])
                    else:
                        result.append(r)
                        aliases.add(r)
                        col_aliases.add(col[1])
                else:
                    result.append(col.as_sql(qn, self.connection))

                    if hasattr(col, 'alias'):
                        aliases.add(col.alias)
                        col_aliases.add(col.alias)

        elif self.query.default_cols:
            cols, new_aliases = self.get_default_columns(with_aliases,
                    col_aliases)
            result.extend(cols)
            aliases.update(new_aliases)

        max_name_length = self.connection.ops.max_name_length()
        result.extend([
            '%s%s' % (
                aggregate.as_sql(qn, self.connection),
                alias is not None
                    and ' AS %s' % qn(truncate_name(alias, max_name_length))
                    or ''
            )
            for alias, aggregate in self.query.aggregate_select.items()
        ])

        for table, col in self.query.related_select_cols:
            r = '%s.%s' % (qn(table), qn(col))
            if with_aliases and col in col_aliases:
                c_alias = 'Col%d' % len(col_aliases)
                result.append('%s AS %s' % (r, c_alias))
                aliases.add(c_alias)
                col_aliases.add(c_alias)
            else:
                result.append(r)
                aliases.add(r)
                col_aliases.add(col)

        self._select_aliases = aliases
        return result

    def get_default_columns(self, with_aliases=False, col_aliases=None,
            start_alias=None, opts=None, as_pairs=False, local_only=False):
        """
        Computes the default columns for selecting every field in the base
        model. Will sometimes be called to pull in related models (e.g. via
        select_related), in which case "opts" and "start_alias" will be given
        to provide a starting point for the traversal.

        Returns a list of strings, quoted appropriately for use in SQL
        directly, as well as a set of aliases used in the select statement (if
        'as_pairs' is True, returns a list of (alias, col_name) pairs instead
        of strings as the first component and None as the second component).
        """
        result = []
        if opts is None:
            opts = self.query.model._meta
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        aliases = set()
        only_load = self.deferred_to_columns()
        # Skip all proxy to the root proxied model
        proxied_model = get_proxied_model(opts)

        if start_alias:
            seen = {None: start_alias}
        for field, model in opts.get_fields_with_model():
            if local_only and model is not None:
                continue
            if start_alias:
                try:
                    alias = seen[model]
                except KeyError:
                    if model is proxied_model:
                        alias = start_alias
                    else:
                        link_field = opts.get_ancestor_link(model)
                        alias = self.query.join((start_alias, model._meta.db_table,
                                link_field.column, model._meta.pk.column))
                    seen[model] = alias
            else:
                # If we're starting from the base model of the queryset, the
                # aliases will have already been set up in pre_sql_setup(), so
                # we can save time here.
                alias = self.query.included_inherited_models[model]
            table = self.query.alias_map[alias][TABLE_NAME]
            if table in only_load and field.column not in only_load[table]:
                continue
            if as_pairs:
                result.append((alias, field.column))
                aliases.add(alias)
                continue
            if with_aliases and field.column in col_aliases:
                c_alias = 'Col%d' % len(col_aliases)
                result.append('%s.%s AS %s' % (qn(alias),
                    qn2(field.column), c_alias))
                col_aliases.add(c_alias)
                aliases.add(c_alias)
            else:
                r = '%s.%s' % (qn(alias), qn2(field.column))
                result.append(r)
                aliases.add(r)
                if with_aliases:
                    col_aliases.add(field.column)
        return result, aliases

    def get_ordering(self):
        """
        Returns a tuple containing a list representing the SQL elements in the
        "order by" clause, and the list of SQL elements that need to be added
        to the GROUP BY clause as a result of the ordering.

        Also sets the ordering_aliases attribute on this instance to a list of
        extra aliases needed in the select.

        Determining the ordering SQL can change the tables we need to include,
        so this should be run *before* get_from_clause().
        """
        if self.query.extra_order_by:
            ordering = self.query.extra_order_by
        elif not self.query.default_ordering:
            ordering = self.query.order_by
        else:
            ordering = self.query.order_by or self.query.model._meta.ordering
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        distinct = self.query.distinct
        select_aliases = self._select_aliases
        result = []
        group_by = []
        ordering_aliases = []
        if self.query.standard_ordering:
            asc, desc = ORDER_DIR['ASC']
        else:
            asc, desc = ORDER_DIR['DESC']

        # It's possible, due to model inheritance, that normal usage might try
        # to include the same field more than once in the ordering. We track
        # the table/column pairs we use and discard any after the first use.
        processed_pairs = set()

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
                group_by.append((field, []))
                continue
            col, order = get_order_dir(field, asc)
            if col in self.query.aggregate_select:
                result.append('%s %s' % (col, order))
                continue
            if '.' in field:
                # This came in through an extra(order_by=...) addition. Pass it
                # on verbatim.
                table, col = col.split('.', 1)
                if (table, col) not in processed_pairs:
                    elt = '%s.%s' % (qn(table), col)
                    processed_pairs.add((table, col))
                    if not distinct or elt in select_aliases:
                        result.append('%s %s' % (elt, order))
                        group_by.append((elt, []))
            elif get_order_dir(field)[0] not in self.query.extra_select:
                # 'col' is of the form 'field' or 'field1__field2' or
                # '-field1__field2__field', etc.
                for table, col, order in self.find_ordering_name(field,
                        self.query.model._meta, default_order=asc):
                    if (table, col) not in processed_pairs:
                        elt = '%s.%s' % (qn(table), qn2(col))
                        processed_pairs.add((table, col))
                        if distinct and elt not in select_aliases:
                            ordering_aliases.append(elt)
                        result.append('%s %s' % (elt, order))
                        group_by.append((elt, []))
            else:
                elt = qn2(col)
                if distinct and col not in select_aliases:
                    ordering_aliases.append(elt)
                result.append('%s %s' % (elt, order))
                group_by.append(self.query.extra_select[col])
        self.query.ordering_aliases = ordering_aliases
        return result, group_by

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
            alias = self.query.get_initial_alias()
        field, target, opts, joins, last, extra = self.query.setup_joins(pieces,
                opts, alias, False)
        alias = joins[-1]
        col = target.column
        if not field.rel:
            # To avoid inadvertent trimming of a necessary alias, use the
            # refcount to show that we are referencing a non-relation field on
            # the model.
            self.query.ref_alias(alias)

        # Must use left outer joins for nullable fields and their relations.
        self.query.promote_alias_chain(joins,
            self.query.alias_map[joins[0]][JOIN_TYPE] == self.query.LOUTER)

        # If we get to this point and the field is a relation to another model,
        # append the default ordering for that model.
        if field.rel and len(joins) > 1 and opts.ordering:
            # Firstly, avoid infinite loops.
            if not already_seen:
                already_seen = set()
            join_tuple = tuple([self.query.alias_map[j][TABLE_NAME] for j in joins])
            if join_tuple in already_seen:
                raise FieldError('Infinite loop caused by ordering.')
            already_seen.add(join_tuple)

            results = []
            for item in opts.ordering:
                results.extend(self.find_ordering_name(item, opts, alias,
                        order, already_seen))
            return results

        if alias:
            # We have to do the same "final join" optimisation as in
            # add_filter, since the final column might not otherwise be part of
            # the select set (so we can't order on it).
            while 1:
                join = self.query.alias_map[alias]
                if col != join[RHS_JOIN_COL]:
                    break
                self.query.unref_alias(alias)
                alias = join[LHS_ALIAS]
                col = join[LHS_JOIN_COL]
        return [(alias, col, order)]

    def get_from_clause(self):
        """
        Returns a list of strings that are joined together to go after the
        "FROM" part of the query, as well as a list any extra parameters that
        need to be included. Sub-classes, can override this to create a
        from-clause via a "select".

        This should only be called after any SQL construction methods that
        might change the tables we need. This means the select columns and
        ordering must be done first.
        """
        result = []
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        first = True
        for alias in self.query.tables:
            if not self.query.alias_refcount[alias]:
                continue
            try:
                name, alias, join_type, lhs, lhs_col, col, nullable = self.query.alias_map[alias]
            except KeyError:
                # Extra tables can end up in self.tables, but not in the
                # alias_map if they aren't in a join. That's OK. We skip them.
                continue
            alias_str = (alias != name and ' %s' % alias or '')
            if join_type and not first:
                result.append('%s %s%s ON (%s.%s = %s.%s)'
                        % (join_type, qn(name), alias_str, qn(lhs),
                           qn2(lhs_col), qn(alias), qn2(col)))
            else:
                connector = not first and ', ' or ''
                result.append('%s%s%s' % (connector, qn(name), alias_str))
            first = False
        for t in self.query.extra_tables:
            alias, unused = self.query.table_alias(t)
            # Only add the alias if it's not already present (the table_alias()
            # calls increments the refcount, so an alias refcount of one means
            # this is the only reference.
            if alias not in self.query.alias_map or self.query.alias_refcount[alias] == 1:
                connector = not first and ', ' or ''
                result.append('%s%s' % (connector, qn(alias)))
                first = False
        return result, []

    def get_grouping(self):
        """
        Returns a tuple representing the SQL elements in the "group by" clause.
        """
        qn = self.quote_name_unless_alias
        result, params = [], []
        if self.query.group_by is not None:
            if len(self.query.model._meta.fields) == len(self.query.select) and \
                self.connection.features.allows_group_by_pk:
                self.query.group_by = [(self.query.model._meta.db_table, self.query.model._meta.pk.column)]

            group_by = self.query.group_by or []

            extra_selects = []
            for extra_select, extra_params in self.query.extra_select.itervalues():
                extra_selects.append(extra_select)
                params.extend(extra_params)
            for col in group_by + self.query.related_select_cols + extra_selects:
                if isinstance(col, (list, tuple)):
                    result.append('%s.%s' % (qn(col[0]), qn(col[1])))
                elif hasattr(col, 'as_sql'):
                    result.append(col.as_sql(qn))
                else:
                    result.append('(%s)' % str(col))
        return result, params

    def fill_related_selections(self, opts=None, root_alias=None, cur_depth=1,
            used=None, requested=None, restricted=None, nullable=None,
            dupe_set=None, avoid_set=None):
        """
        Fill in the information needed for a select_related query. The current
        depth is measured as the number of connections away from the root model
        (for example, cur_depth=1 means we are looking at models with direct
        connections to the root model).
        """
        if not restricted and self.query.max_depth and cur_depth > self.query.max_depth:
            # We've recursed far enough; bail out.
            return

        if not opts:
            opts = self.query.get_meta()
            root_alias = self.query.get_initial_alias()
            self.query.related_select_cols = []
            self.query.related_select_fields = []
        if not used:
            used = set()
        if dupe_set is None:
            dupe_set = set()
        if avoid_set is None:
            avoid_set = set()
        orig_dupe_set = dupe_set

        # Setup for the case when only particular related fields should be
        # included in the related selection.
        if requested is None:
            if isinstance(self.query.select_related, dict):
                requested = self.query.select_related
                restricted = True
            else:
                restricted = False

        for f, model in opts.get_fields_with_model():
            if not select_related_descend(f, restricted, requested):
                continue
            # The "avoid" set is aliases we want to avoid just for this
            # particular branch of the recursion. They aren't permanently
            # forbidden from reuse in the related selection tables (which is
            # what "used" specifies).
            avoid = avoid_set.copy()
            dupe_set = orig_dupe_set.copy()
            table = f.rel.to._meta.db_table
            promote = nullable or f.null
            if model:
                int_opts = opts
                alias = root_alias
                alias_chain = []
                for int_model in opts.get_base_chain(model):
                    # Proxy model have elements in base chain
                    # with no parents, assign the new options
                    # object and skip to the next base in that
                    # case
                    if not int_opts.parents[int_model]:
                        int_opts = int_model._meta
                        continue
                    lhs_col = int_opts.parents[int_model].column
                    dedupe = lhs_col in opts.duplicate_targets
                    if dedupe:
                        avoid.update(self.query.dupe_avoidance.get(id(opts), lhs_col),
                                ())
                        dupe_set.add((opts, lhs_col))
                    int_opts = int_model._meta
                    alias = self.query.join((alias, int_opts.db_table, lhs_col,
                            int_opts.pk.column), exclusions=used,
                            promote=promote)
                    alias_chain.append(alias)
                    for (dupe_opts, dupe_col) in dupe_set:
                        self.query.update_dupe_avoidance(dupe_opts, dupe_col, alias)
                if self.query.alias_map[root_alias][JOIN_TYPE] == self.query.LOUTER:
                    self.query.promote_alias_chain(alias_chain, True)
            else:
                alias = root_alias

            dedupe = f.column in opts.duplicate_targets
            if dupe_set or dedupe:
                avoid.update(self.query.dupe_avoidance.get((id(opts), f.column), ()))
                if dedupe:
                    dupe_set.add((opts, f.column))

            alias = self.query.join((alias, table, f.column,
                    f.rel.get_related_field().column),
                    exclusions=used.union(avoid), promote=promote)
            used.add(alias)
            columns, aliases = self.get_default_columns(start_alias=alias,
                    opts=f.rel.to._meta, as_pairs=True)
            self.query.related_select_cols.extend(columns)
            if self.query.alias_map[alias][JOIN_TYPE] == self.query.LOUTER:
                self.query.promote_alias_chain(aliases, True)
            self.query.related_select_fields.extend(f.rel.to._meta.fields)
            if restricted:
                next = requested.get(f.name, {})
            else:
                next = False
            new_nullable = f.null or promote
            for dupe_opts, dupe_col in dupe_set:
                self.query.update_dupe_avoidance(dupe_opts, dupe_col, alias)
            self.fill_related_selections(f.rel.to._meta, alias, cur_depth + 1,
                    used, next, restricted, new_nullable, dupe_set, avoid)

        if restricted:
            related_fields = [
                (o.field, o.model)
                for o in opts.get_all_related_objects()
                if o.field.unique
            ]
            for f, model in related_fields:
                if not select_related_descend(f, restricted, requested, reverse=True):
                    continue
                # The "avoid" set is aliases we want to avoid just for this
                # particular branch of the recursion. They aren't permanently
                # forbidden from reuse in the related selection tables (which is
                # what "used" specifies).
                avoid = avoid_set.copy()
                dupe_set = orig_dupe_set.copy()
                table = model._meta.db_table

                int_opts = opts
                alias = root_alias
                alias_chain = []
                chain = opts.get_base_chain(f.rel.to)
                if chain is not None:
                    for int_model in chain:
                        # Proxy model have elements in base chain
                        # with no parents, assign the new options
                        # object and skip to the next base in that
                        # case
                        if not int_opts.parents[int_model]:
                            int_opts = int_model._meta
                            continue
                        lhs_col = int_opts.parents[int_model].column
                        dedupe = lhs_col in opts.duplicate_targets
                        if dedupe:
                            avoid.update(self.query.dupe_avoidance.get(id(opts), lhs_col),
                                ())
                            dupe_set.add((opts, lhs_col))
                        int_opts = int_model._meta
                        alias = self.query.join(
                            (alias, int_opts.db_table, lhs_col, int_opts.pk.column),
                            exclusions=used, promote=True, reuse=used
                        )
                        alias_chain.append(alias)
                        for dupe_opts, dupe_col in dupe_set:
                            self.query.update_dupe_avoidance(dupe_opts, dupe_col, alias)
                    dedupe = f.column in opts.duplicate_targets
                    if dupe_set or dedupe:
                        avoid.update(self.query.dupe_avoidance.get((id(opts), f.column), ()))
                        if dedupe:
                            dupe_set.add((opts, f.column))
                alias = self.query.join(
                    (alias, table, f.rel.get_related_field().column, f.column),
                    exclusions=used.union(avoid),
                    promote=True
                )
                used.add(alias)
                columns, aliases = self.get_default_columns(start_alias=alias,
                    opts=model._meta, as_pairs=True, local_only=True)
                self.query.related_select_cols.extend(columns)
                self.query.related_select_fields.extend(model._meta.fields)

                next = requested.get(f.related_query_name(), {})
                new_nullable = f.null or None

                self.fill_related_selections(model._meta, table, cur_depth+1,
                    used, next, restricted, new_nullable)

    def deferred_to_columns(self):
        """
        Converts the self.deferred_loading data structure to mapping of table
        names to sets of column names which are to be loaded. Returns the
        dictionary.
        """
        columns = {}
        self.query.deferred_to_data(columns, self.query.deferred_to_columns_cb)
        return columns

    def results_iter(self):
        """
        Returns an iterator over the results from executing this query.
        """
        resolve_columns = hasattr(self, 'resolve_columns')
        fields = None
        for rows in self.execute_sql(MULTI):
            for row in rows:
                if resolve_columns:
                    if fields is None:
                        # We only set this up here because
                        # related_select_fields isn't populated until
                        # execute_sql() has been called.
                        if self.query.select_fields:
                            fields = self.query.select_fields + self.query.related_select_fields
                        else:
                            fields = self.query.model._meta.fields
                        # If the field was deferred, exclude it from being passed
                        # into `resolve_columns` because it wasn't selected.
                        only_load = self.deferred_to_columns()
                        if only_load:
                            db_table = self.query.model._meta.db_table
                            fields = [f for f in fields if db_table in only_load and
                                      f.column in only_load[db_table]]
                    row = self.resolve_columns(row, fields)

                if self.query.aggregate_select:
                    aggregate_start = len(self.query.extra_select.keys()) + len(self.query.select)
                    aggregate_end = aggregate_start + len(self.query.aggregate_select)
                    row = tuple(row[:aggregate_start]) + tuple([
                        self.query.resolve_aggregate(value, aggregate, self.connection)
                        for (alias, aggregate), value
                        in zip(self.query.aggregate_select.items(), row[aggregate_start:aggregate_end])
                    ]) + tuple(row[aggregate_end:])

                yield row

    def execute_sql(self, result_type=MULTI):
        """
        Run the query against the database and returns the result(s). The
        return value is a single data item if result_type is SINGLE, or an
        iterator over the results if the result_type is MULTI.

        result_type is either MULTI (use fetchmany() to retrieve all rows),
        SINGLE (only retrieve a single row), or None. In this last case, the
        cursor is returned if any query is executed, since it's used by
        subclasses such as InsertQuery). It's possible, however, that no query
        is needed, as the filters describe an empty set. In that case, None is
        returned, to avoid any unnecessary database interaction.
        """
        try:
            sql, params = self.as_sql()
            if not sql:
                raise EmptyResultSet
        except EmptyResultSet:
            if result_type == MULTI:
                return empty_iter()
            else:
                return

        cursor = self.connection.cursor()
        cursor.execute(sql, params)

        if not result_type:
            return cursor
        if result_type == SINGLE:
            if self.query.ordering_aliases:
                return cursor.fetchone()[:-len(self.query.ordering_aliases)]
            return cursor.fetchone()

        # The MULTI case.
        if self.query.ordering_aliases:
            result = order_modified_iter(cursor, len(self.query.ordering_aliases),
                    self.connection.features.empty_fetchmany_value)
        else:
            result = iter((lambda: cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)),
                    self.connection.features.empty_fetchmany_value)
        if not self.connection.features.can_use_chunked_reads:
            # If we are using non-chunked reads, we return the same data
            # structure as normally, but ensure it is all read into memory
            # before going any further.
            return list(result)
        return result


class SQLInsertCompiler(SQLCompiler):
    def placeholder(self, field, val):
        if field is None:
            # A field value of None means the value is raw.
            return val
        elif hasattr(field, 'get_placeholder'):
            # Some fields (e.g. geo fields) need special munging before
            # they can be inserted.
            return field.get_placeholder(val, self.connection)
        else:
            # Return the common case for the placeholder
            return '%s'

    def as_sql(self):
        # We don't need quote_name_unless_alias() here, since these are all
        # going to be column names (so we can avoid the extra overhead).
        qn = self.connection.ops.quote_name
        opts = self.query.model._meta
        result = ['INSERT INTO %s' % qn(opts.db_table)]
        result.append('(%s)' % ', '.join([qn(c) for c in self.query.columns]))
        values = [self.placeholder(*v) for v in self.query.values]
        result.append('VALUES (%s)' % ', '.join(values))
        params = self.query.params
        if self.return_id and self.connection.features.can_return_id_from_insert:
            col = "%s.%s" % (qn(opts.db_table), qn(opts.pk.column))
            r_fmt, r_params = self.connection.ops.return_insert_id()
            result.append(r_fmt % col)
            params = params + r_params
        return ' '.join(result), params

    def execute_sql(self, return_id=False):
        self.return_id = return_id
        cursor = super(SQLInsertCompiler, self).execute_sql(None)
        if not (return_id and cursor):
            return
        if self.connection.features.can_return_id_from_insert:
            return self.connection.ops.fetch_returned_insert_id(cursor)
        return self.connection.ops.last_insert_id(cursor,
                self.query.model._meta.db_table, self.query.model._meta.pk.column)


class SQLDeleteCompiler(SQLCompiler):
    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        assert len(self.query.tables) == 1, \
                "Can only delete from one table at a time."
        qn = self.quote_name_unless_alias
        result = ['DELETE FROM %s' % qn(self.query.tables[0])]
        where, params = self.query.where.as_sql(qn=qn, connection=self.connection)
        result.append('WHERE %s' % where)
        return ' '.join(result), tuple(params)

class SQLUpdateCompiler(SQLCompiler):
    def as_sql(self):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        from django.db.models.base import Model

        self.pre_sql_setup()
        if not self.query.values:
            return '', ()
        table = self.query.tables[0]
        qn = self.quote_name_unless_alias
        result = ['UPDATE %s' % qn(table)]
        result.append('SET')
        values, update_params = [], []
        for field, model, val in self.query.values:
            if hasattr(val, 'prepare_database_save'):
                val = val.prepare_database_save(field)
            else:
                val = field.get_db_prep_save(val, connection=self.connection)

            # Getting the placeholder for the field.
            if hasattr(field, 'get_placeholder'):
                placeholder = field.get_placeholder(val, self.connection)
            else:
                placeholder = '%s'

            if hasattr(val, 'evaluate'):
                val = SQLEvaluator(val, self.query, allow_joins=False)
            name = field.column
            if hasattr(val, 'as_sql'):
                sql, params = val.as_sql(qn, self.connection)
                values.append('%s = %s' % (qn(name), sql))
                update_params.extend(params)
            elif val is not None:
                values.append('%s = %s' % (qn(name), placeholder))
                update_params.append(val)
            else:
                values.append('%s = NULL' % qn(name))
        if not values:
            return '', ()
        result.append(', '.join(values))
        where, params = self.query.where.as_sql(qn=qn, connection=self.connection)
        if where:
            result.append('WHERE %s' % where)
        return ' '.join(result), tuple(update_params + params)

    def execute_sql(self, result_type):
        """
        Execute the specified update. Returns the number of rows affected by
        the primary update query. The "primary update query" is the first
        non-empty query that is executed. Row counts for any subsequent,
        related queries are not available.
        """
        cursor = super(SQLUpdateCompiler, self).execute_sql(result_type)
        rows = cursor and cursor.rowcount or 0
        is_empty = cursor is None
        del cursor
        for query in self.query.get_related_updates():
            aux_rows = query.get_compiler(self.using).execute_sql(result_type)
            if is_empty:
                rows = aux_rows
                is_empty = False
        return rows

    def pre_sql_setup(self):
        """
        If the update depends on results from other tables, we need to do some
        munging of the "where" conditions to match the format required for
        (portable) SQL updates. That is done here.

        Further, if we are going to be running multiple updates, we pull out
        the id values to update at this point so that they don't change as a
        result of the progressive updates.
        """
        self.query.select_related = False
        self.query.clear_ordering(True)
        super(SQLUpdateCompiler, self).pre_sql_setup()
        count = self.query.count_active_tables()
        if not self.query.related_updates and count == 1:
            return

        # We need to use a sub-select in the where clause to filter on things
        # from other tables.
        query = self.query.clone(klass=Query)
        query.bump_prefix()
        query.extra = {}
        query.select = []
        query.add_fields([query.model._meta.pk.name])
        must_pre_select = count > 1 and not self.connection.features.update_can_self_select

        # Now we adjust the current query: reset the where clause and get rid
        # of all the tables we don't need (since they're in the sub-select).
        self.query.where = self.query.where_class()
        if self.query.related_updates or must_pre_select:
            # Either we're using the idents in multiple update queries (so
            # don't want them to change), or the db backend doesn't support
            # selecting from the updating table (e.g. MySQL).
            idents = []
            for rows in query.get_compiler(self.using).execute_sql(MULTI):
                idents.extend([r[0] for r in rows])
            self.query.add_filter(('pk__in', idents))
            self.query.related_ids = idents
        else:
            # The fast path. Filters and updates in one query.
            self.query.add_filter(('pk__in', query))
        for alias in self.query.tables[1:]:
            self.query.alias_refcount[alias] = 0

class SQLAggregateCompiler(SQLCompiler):
    def as_sql(self, qn=None):
        """
        Creates the SQL for this query. Returns the SQL string and list of
        parameters.
        """
        if qn is None:
            qn = self.quote_name_unless_alias
        sql = ('SELECT %s FROM (%s) subquery' % (
            ', '.join([
                aggregate.as_sql(qn, self.connection)
                for aggregate in self.query.aggregate_select.values()
            ]),
            self.query.subquery)
        )
        params = self.query.sub_params
        return (sql, params)

class SQLDateCompiler(SQLCompiler):
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

        offset = len(self.query.extra_select)
        for rows in self.execute_sql(MULTI):
            for row in rows:
                date = row[offset]
                if resolve_columns:
                    date = self.resolve_columns(row, fields)[offset]
                elif needs_string_cast:
                    date = typecast_timestamp(str(date))
                yield date


def empty_iter():
    """
    Returns an iterator containing no results.
    """
    yield iter([]).next()


def order_modified_iter(cursor, trim, sentinel):
    """
    Yields blocks of rows from a cursor. We use this iterator in the special
    case when extra output columns have been added to support ordering
    requirements. We must trim those extra columns before anything else can use
    the results, since they're only needed to make the SQL valid.
    """
    for rows in iter((lambda: cursor.fetchmany(GET_ITERATOR_CHUNK_SIZE)),
            sentinel):
        yield [r[:-trim] for r in rows]
