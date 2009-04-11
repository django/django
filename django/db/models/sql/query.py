"""
Create SQL statements for QuerySets.

The code in here encapsulates all of the SQL construction so that QuerySets
themselves do not have to (and could be backed by things other than SQL
databases). The abstraction barrier only works one way: this module has to know
all about the internals of models in order to get the information it needs.
"""

from copy import deepcopy

from django.utils.tree import Node
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode
from django.db.backends.util import truncate_name
from django.db import connection
from django.db.models import signals
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query_utils import select_related_descend
from django.db.models.sql import aggregates as base_aggregates_module
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.sql.where import WhereNode, Constraint, EverythingNode, AND, OR
from django.core.exceptions import FieldError
from datastructures import EmptyResultSet, Empty, MultiJoin
from constants import *

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback

__all__ = ['Query', 'BaseQuery']

class BaseQuery(object):
    """
    A single SQL query.
    """
    # SQL join types. These are part of the class because their string forms
    # vary from database to database and can be customised by a subclass.
    INNER = 'INNER JOIN'
    LOUTER = 'LEFT OUTER JOIN'

    alias_prefix = 'T'
    query_terms = QUERY_TERMS
    aggregates_module = base_aggregates_module

    def __init__(self, model, connection, where=WhereNode):
        self.model = model
        self.connection = connection
        self.alias_refcount = {}
        self.alias_map = {}     # Maps alias to join information
        self.table_map = {}     # Maps table names to list of aliases.
        self.join_map = {}
        self.rev_join_map = {}  # Reverse of join_map.
        self.quote_cache = {}
        self.default_cols = True
        self.default_ordering = True
        self.standard_ordering = True
        self.ordering_aliases = []
        self.select_fields = []
        self.related_select_fields = []
        self.dupe_avoidance = {}
        self.used_aliases = set()
        self.filter_is_sticky = False
        self.included_inherited_models = {}

        # SQL-related attributes
        self.select = []
        self.tables = []    # Aliases in the order they are created.
        self.where = where()
        self.where_class = where
        self.group_by = None
        self.having = where()
        self.order_by = []
        self.low_mark, self.high_mark = 0, None  # Used for offset/limit
        self.distinct = False
        self.select_related = False
        self.related_select_cols = []

        # SQL aggregate-related attributes
        self.aggregates = SortedDict() # Maps alias -> SQL aggregate function
        self.aggregate_select_mask = None
        self._aggregate_select_cache = None

        # Arbitrary maximum limit for select_related. Prevents infinite
        # recursion. Can be changed by the depth parameter to select_related().
        self.max_depth = 5

        # These are for extensions. The contents are more or less appended
        # verbatim to the appropriate clause.
        self.extra_select = SortedDict()  # Maps col_alias -> (col_sql, params).
        self.extra_tables = ()
        self.extra_where = ()
        self.extra_params = ()
        self.extra_order_by = ()

        # A tuple that is a set of model field names and either True, if these
        # are the fields to defer, or False if these are the only fields to
        # load.
        self.deferred_loading = (set(), True)

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

    def __getstate__(self):
        """
        Pickling support.
        """
        obj_dict = self.__dict__.copy()
        obj_dict['related_select_fields'] = []
        obj_dict['related_select_cols'] = []
        del obj_dict['connection']

        # Fields can't be pickled, so we pickle the list of field names instead.
        obj_dict['select_fields'] = [f.name for f in obj_dict['select_fields']]
        return obj_dict

    def __setstate__(self, obj_dict):
        """
        Unpickling support.
        """
        # Rebuild list of field instances
        obj_dict['select_fields'] = [obj_dict['model']._meta.get_field(name) for name in obj_dict['select_fields']]

        self.__dict__.update(obj_dict)
        # XXX: Need a better solution for this when multi-db stuff is
        # supported. It's the only class-reference to the module-level
        # connection variable.
        self.connection = connection

    def get_meta(self):
        """
        Returns the Options instance (the model._meta) from which to start
        processing. Normally, this is self.model._meta, but it can be changed
        by subclasses.
        """
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
        obj.alias_refcount = self.alias_refcount.copy()
        obj.alias_map = self.alias_map.copy()
        obj.table_map = self.table_map.copy()
        obj.join_map = self.join_map.copy()
        obj.rev_join_map = self.rev_join_map.copy()
        obj.quote_cache = {}
        obj.default_cols = self.default_cols
        obj.default_ordering = self.default_ordering
        obj.standard_ordering = self.standard_ordering
        obj.included_inherited_models = self.included_inherited_models.copy()
        obj.ordering_aliases = []
        obj.select_fields = self.select_fields[:]
        obj.related_select_fields = self.related_select_fields[:]
        obj.dupe_avoidance = self.dupe_avoidance.copy()
        obj.select = self.select[:]
        obj.tables = self.tables[:]
        obj.where = deepcopy(self.where)
        obj.where_class = self.where_class
        if self.group_by is None:
            obj.group_by = None
        else:
            obj.group_by = self.group_by[:]
        obj.having = deepcopy(self.having)
        obj.order_by = self.order_by[:]
        obj.low_mark, obj.high_mark = self.low_mark, self.high_mark
        obj.distinct = self.distinct
        obj.select_related = self.select_related
        obj.related_select_cols = []
        obj.aggregates = deepcopy(self.aggregates)
        if self.aggregate_select_mask is None:
            obj.aggregate_select_mask = None
        else:
            obj.aggregate_select_mask = self.aggregate_select_mask[:]
        if self._aggregate_select_cache is None:
            obj._aggregate_select_cache = None
        else:
            obj._aggregate_select_cache = self._aggregate_select_cache.copy()
        obj.max_depth = self.max_depth
        obj.extra_select = self.extra_select.copy()
        obj.extra_tables = self.extra_tables
        obj.extra_where = self.extra_where
        obj.extra_params = self.extra_params
        obj.extra_order_by = self.extra_order_by
        obj.deferred_loading = deepcopy(self.deferred_loading)
        if self.filter_is_sticky and self.used_aliases:
            obj.used_aliases = self.used_aliases.copy()
        else:
            obj.used_aliases = set()
        obj.filter_is_sticky = False
        obj.__dict__.update(kwargs)
        if hasattr(obj, '_setup_query'):
            obj._setup_query()
        return obj

    def convert_values(self, value, field):
        """Convert the database-returned value into a type that is consistent
        across database backends.

        By default, this defers to the underlying backend operations, but
        it can be overridden by Query classes for specific backends.
        """
        return self.connection.ops.convert_values(value, field)

    def resolve_aggregate(self, value, aggregate):
        """Resolve the value of aggregates returned by the database to
        consistent (and reasonable) types.

        This is required because of the predisposition of certain backends
        to return Decimal and long types when they are not needed.
        """
        if value is None:
            if aggregate.is_ordinal:
                return 0
            # Return None as-is
            return value
        elif aggregate.is_ordinal:
            # Any ordinal aggregate (e.g., count) returns an int
            return int(value)
        elif aggregate.is_computed:
            # Any computed aggregate (e.g., avg) returns a float
            return float(value)
        else:
            # Return value depends on the type of the field being processed.
            return self.convert_values(value, aggregate.field)

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
                        if self.select_fields:
                            fields = self.select_fields + self.related_select_fields
                        else:
                            fields = self.model._meta.fields
                    row = self.resolve_columns(row, fields)

                if self.aggregate_select:
                    aggregate_start = len(self.extra_select.keys()) + len(self.select)
                    aggregate_end = aggregate_start + len(self.aggregate_select)
                    row = tuple(row[:aggregate_start]) + tuple([
                        self.resolve_aggregate(value, aggregate)
                        for (alias, aggregate), value
                        in zip(self.aggregate_select.items(), row[aggregate_start:aggregate_end])
                    ]) + tuple(row[aggregate_end:])

                yield row

    def get_aggregation(self):
        """
        Returns the dictionary with the values of the existing aggregations.
        """
        if not self.aggregate_select:
            return {}

        # If there is a group by clause, aggregating does not add useful
        # information but retrieves only the first row. Aggregate
        # over the subquery instead.
        if self.group_by is not None:
            from subqueries import AggregateQuery
            query = AggregateQuery(self.model, self.connection)

            obj = self.clone()

            # Remove any aggregates marked for reduction from the subquery
            # and move them to the outer AggregateQuery.
            for alias, aggregate in self.aggregate_select.items():
                if aggregate.is_summary:
                    query.aggregate_select[alias] = aggregate
                    del obj.aggregate_select[alias]

            query.add_subquery(obj)
        else:
            query = self
            self.select = []
            self.default_cols = False
            self.extra_select = {}
            self.remove_inherited_models()

        query.clear_ordering(True)
        query.clear_limits()
        query.select_related = False
        query.related_select_cols = []
        query.related_select_fields = []

        result = query.execute_sql(SINGLE)
        if result is None:
            result = [None for q in query.aggregate_select.items()]

        return dict([
            (alias, self.resolve_aggregate(val, aggregate))
            for (alias, aggregate), val
            in zip(query.aggregate_select.items(), result)
        ])

    def get_count(self):
        """
        Performs a COUNT() query using the current filter constraints.
        """
        obj = self.clone()
        if len(self.select) > 1 or self.aggregate_select:
            # If a select clause exists, then the query has already started to
            # specify the columns that are to be returned.
            # In this case, we need to use a subquery to evaluate the count.
            from subqueries import AggregateQuery
            subquery = obj
            subquery.clear_ordering(True)
            subquery.clear_limits()

            obj = AggregateQuery(obj.model, obj.connection)
            obj.add_subquery(subquery)

        obj.add_count_column()
        number = obj.get_aggregation()[None]

        # Apply offset and limit constraints manually, since using LIMIT/OFFSET
        # in SQL (in variants that provide them) doesn't change the COUNT
        # output.
        number = max(0, number - self.low_mark)
        if self.high_mark is not None:
            number = min(number, self.high_mark - self.low_mark)

        return number

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
        where, w_params = self.where.as_sql(qn=qn)
        having, h_params = self.having.as_sql(qn=qn)
        params = []
        for val in self.extra_select.itervalues():
            params.extend(val[1])

        result = ['SELECT']
        if self.distinct:
            result.append('DISTINCT')
        result.append(', '.join(out_cols + self.ordering_aliases))

        result.append('FROM')
        result.extend(from_)
        params.extend(f_params)

        if where:
            result.append('WHERE %s' % where)
            params.extend(w_params)
        if self.extra_where:
            if not where:
                result.append('WHERE')
            else:
                result.append('AND')
            result.append(' AND '.join(self.extra_where))

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
            if self.high_mark is not None:
                result.append('LIMIT %d' % (self.high_mark - self.low_mark))
            if self.low_mark:
                if self.high_mark is None:
                    val = self.connection.ops.no_limit_value()
                    if val:
                        result.append('LIMIT %d' % val)
                result.append('OFFSET %d' % self.low_mark)

        params.extend(self.extra_params)
        return ' '.join(result), tuple(params)

    def as_nested_sql(self):
        """
        Perform the same functionality as the as_sql() method, returning an
        SQL string and parameters. However, the alias prefixes are bumped
        beforehand (in a copy -- the current query isn't changed) and any
        ordering is removed.

        Used when nesting this query inside another.
        """
        obj = self.clone()
        obj.clear_ordering(True)
        obj.bump_prefix()
        return obj.as_sql()

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

        self.remove_inherited_models()
        # Work out how to relabel the rhs aliases, if necessary.
        change_map = {}
        used = set()
        conjunction = (connector == AND)
        first = True
        for alias in rhs.tables:
            if not rhs.alias_refcount[alias]:
                # An unused alias.
                continue
            promote = (rhs.alias_map[alias][JOIN_TYPE] == self.LOUTER)
            new_alias = self.join(rhs.rev_join_map[alias],
                    (conjunction and not first), used, promote, not conjunction)
            used.add(new_alias)
            change_map[alias] = new_alias
            first = False

        # So that we don't exclude valid results in an "or" query combination,
        # the first join that is exclusive to the lhs (self) must be converted
        # to an outer join.
        if not conjunction:
            for alias in self.tables[1:]:
                if self.alias_refcount[alias] == 1:
                    self.promote_alias(alias, True)
                    break

        # Now relabel a copy of the rhs where-clause and add it to the current
        # one.
        if rhs.where:
            w = deepcopy(rhs.where)
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
                item = deepcopy(col)
                item.relabel_aliases(change_map)
                self.select.append(item)
        self.select_fields = rhs.select_fields[:]

        if connector == OR:
            # It would be nice to be able to handle this, but the queries don't
            # really make sense (or return consistent value sets). Not worth
            # the extra complexity when you can write a real query instead.
            if self.extra_select and rhs.extra_select:
                raise ValueError("When merging querysets using 'or', you "
                        "cannot have extra(select=...) on both sides.")
            if self.extra_where and rhs.extra_where:
                raise ValueError("When merging querysets using 'or', you "
                        "cannot have extra(where=...) on both sides.")
        self.extra_select.update(rhs.extra_select)
        self.extra_tables += rhs.extra_tables
        self.extra_where += rhs.extra_where
        self.extra_params += rhs.extra_params

        # Ordering uses the 'rhs' ordering, unless it has none, in which case
        # the current ordering is used.
        self.order_by = rhs.order_by and rhs.order_by[:] or self.order_by
        self.extra_order_by = rhs.extra_order_by or self.extra_order_by

    def pre_sql_setup(self):
        """
        Does any necessary class setup immediately prior to producing SQL. This
        is for things that can't necessarily be done in __init__ because we
        might not have all the pieces in place at that time.
        """
        if not self.tables:
            self.join((None, self.model._meta.db_table, None, None))
        if (not self.select and self.default_cols and not
                self.included_inherited_models):
            self.setup_inherited_models()
        if self.select_related and not self.related_select_cols:
            self.fill_related_selections()

    def deferred_to_data(self, target, callback):
        """
        Converts the self.deferred_loading data structure to an alternate data
        structure, describing the field that *will* be loaded. This is used to
        compute the columns to select from the database and also by the
        QuerySet class to work out which fields are being initialised on each
        model. Models that have all their fields included aren't mentioned in
        the result, only those that have field restrictions in place.

        The "target" parameter is the instance that is populated (in place).
        The "callback" is a function that is called whenever a (model, field)
        pair need to be added to "target". It accepts three parameters:
        "target", and the model and list of fields being added for that model.
        """
        field_names, defer = self.deferred_loading
        if not field_names:
            return
        columns = set()
        orig_opts = self.model._meta
        seen = {}
        must_include = {self.model: set([orig_opts.pk])}
        for field_name in field_names:
            parts = field_name.split(LOOKUP_SEP)
            cur_model = self.model
            opts = orig_opts
            for name in parts[:-1]:
                old_model = cur_model
                source = opts.get_field_by_name(name)[0]
                cur_model = opts.get_field_by_name(name)[0].rel.to
                opts = cur_model._meta
                # Even if we're "just passing through" this model, we must add
                # both the current model's pk and the related reference field
                # to the things we select.
                must_include[old_model].add(source)
                add_to_dict(must_include, cur_model, opts.pk)
            field, model, _, _ = opts.get_field_by_name(parts[-1])
            if model is None:
                model = cur_model
            add_to_dict(seen, model, field)

        if defer:
            # We need to load all fields for each model, except those that
            # appear in "seen" (for all models that appear in "seen"). The only
            # slight complexity here is handling fields that exist on parent
            # models.
            workset = {}
            for model, values in seen.iteritems():
                for field, f_model in model._meta.get_fields_with_model():
                    if field in values:
                        continue
                    add_to_dict(workset, f_model or model, field)
            for model, values in must_include.iteritems():
                # If we haven't included a model in workset, we don't add the
                # corresponding must_include fields for that model, since an
                # empty set means "include all fields". That's why there's no
                # "else" branch here.
                if model in workset:
                    workset[model].update(values)
            for model, values in workset.iteritems():
                callback(target, model, values)
        else:
            for model, values in must_include.iteritems():
                if model in seen:
                    seen[model].update(values)
                else:
                    # As we've passed through this model, but not explicitly
                    # included any fields, we have to make sure it's mentioned
                    # so that only the "must include" fields are pulled in.
                    seen[model] = values
            for model, values in seen.iteritems():
                callback(target, model, values)

    def deferred_to_columns(self):
        """
        Converts the self.deferred_loading data structure to mapping of table
        names to sets of column names which are to be loaded. Returns the
        dictionary.
        """
        columns = {}
        self.deferred_to_data(columns, self.deferred_to_columns_cb)
        return columns

    def deferred_to_columns_cb(self, target, model, fields):
        """
        Callback used by deferred_to_columns(). The "target" parameter should
        be a set instance.
        """
        table = model._meta.db_table
        if table not in target:
            target[table] = set()
        for field in fields:
            target[table].add(field.column)

    def get_columns(self, with_aliases=False):
        """
        Returns the list of columns to use in the select statement. If no
        columns have been specified, returns all columns relating to fields in
        the model.

        If 'with_aliases' is true, any column names that are duplicated
        (without the table names) are given unique aliases. This is needed in
        some cases to avoid ambiguitity with nested queries.
        """
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        result = ['(%s) AS %s' % (col[0], qn2(alias)) for alias, col in self.extra_select.iteritems()]
        aliases = set(self.extra_select.keys())
        if with_aliases:
            col_aliases = aliases.copy()
        else:
            col_aliases = set()
        if self.select:
            only_load = self.deferred_to_columns()
            for col in self.select:
                if isinstance(col, (list, tuple)):
                    alias, column = col
                    table = self.alias_map[alias][TABLE_NAME]
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
                    result.append(col.as_sql(quote_func=qn))

                    if hasattr(col, 'alias'):
                        aliases.add(col.alias)
                        col_aliases.add(col.alias)

        elif self.default_cols:
            cols, new_aliases = self.get_default_columns(with_aliases,
                    col_aliases)
            result.extend(cols)
            aliases.update(new_aliases)

        result.extend([
            '%s%s' % (
                aggregate.as_sql(quote_func=qn),
                alias is not None and ' AS %s' % qn(alias) or ''
            )
            for alias, aggregate in self.aggregate_select.items()
        ])

        for table, col in self.related_select_cols:
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
            start_alias=None, opts=None, as_pairs=False):
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
            opts = self.model._meta
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        aliases = set()
        only_load = self.deferred_to_columns()
        proxied_model = opts.proxy and opts.proxy_for_model or 0
        if start_alias:
            seen = {None: start_alias}
        for field, model in opts.get_fields_with_model():
            if start_alias:
                try:
                    alias = seen[model]
                except KeyError:
                    if model is proxied_model:
                        alias = start_alias
                    else:
                        link_field = opts.get_ancestor_link(model)
                        alias = self.join((start_alias, model._meta.db_table,
                                link_field.column, model._meta.pk.column))
                    seen[model] = alias
            else:
                # If we're starting from the base model of the queryset, the
                # aliases will have already been set up in pre_sql_setup(), so
                # we can save time here.
                alias = self.included_inherited_models[model]
            table = self.alias_map[alias][TABLE_NAME]
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
        for alias in self.tables:
            if not self.alias_refcount[alias]:
                continue
            try:
                name, alias, join_type, lhs, lhs_col, col, nullable = self.alias_map[alias]
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
        for t in self.extra_tables:
            alias, unused = self.table_alias(t)
            # Only add the alias if it's not already present (the table_alias()
            # calls increments the refcount, so an alias refcount of one means
            # this is the only reference.
            if alias not in self.alias_map or self.alias_refcount[alias] == 1:
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
        if self.group_by is not None:
            group_by = self.group_by or []

            extra_selects = []
            for extra_select, extra_params in self.extra_select.itervalues():
                extra_selects.append(extra_select)
                params.extend(extra_params)
            for col in group_by + self.related_select_cols + extra_selects:
                if isinstance(col, (list, tuple)):
                    result.append('%s.%s' % (qn(col[0]), qn(col[1])))
                elif hasattr(col, 'as_sql'):
                    result.append(col.as_sql(qn))
                else:
                    result.append(str(col))
        return result, params

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
        if self.extra_order_by:
            ordering = self.extra_order_by
        elif not self.default_ordering:
            ordering = self.order_by
        else:
            ordering = self.order_by or self.model._meta.ordering
        qn = self.quote_name_unless_alias
        qn2 = self.connection.ops.quote_name
        distinct = self.distinct
        select_aliases = self._select_aliases
        result = []
        group_by = []
        ordering_aliases = []
        if self.standard_ordering:
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
            if col in self.aggregate_select:
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
            elif get_order_dir(field)[0] not in self.extra_select:
                # 'col' is of the form 'field' or 'field1__field2' or
                # '-field1__field2__field', etc.
                for table, col, order in self.find_ordering_name(field,
                        self.model._meta, default_order=asc):
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
                group_by.append(self.extra_select[col])
        self.ordering_aliases = ordering_aliases
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
            alias = self.get_initial_alias()
        field, target, opts, joins, last, extra = self.setup_joins(pieces,
                opts, alias, False)
        alias = joins[-1]
        col = target.column
        if not field.rel:
            # To avoid inadvertent trimming of a necessary alias, use the
            # refcount to show that we are referencing a non-relation field on
            # the model.
            self.ref_alias(alias)

        # Must use left outer joins for nullable fields and their relations.
        self.promote_alias_chain(joins,
                self.alias_map[joins[0]][JOIN_TYPE] == self.LOUTER)

        # If we get to this point and the field is a relation to another model,
        # append the default ordering for that model.
        if field.rel and len(joins) > 1 and opts.ordering:
            # Firstly, avoid infinite loops.
            if not already_seen:
                already_seen = set()
            join_tuple = tuple([self.alias_map[j][TABLE_NAME] for j in joins])
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
                join = self.alias_map[alias]
                if col != join[RHS_JOIN_COL]:
                    break
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
        current = self.table_map.get(table_name)
        if not create and current:
            alias = current[0]
            self.alias_refcount[alias] += 1
            return alias, False

        # Create a new alias for this table.
        if current:
            alias = '%s%d' % (self.alias_prefix, len(self.alias_map) + 1)
            current.append(alias)
        else:
            # The first occurence of a table uses the table name directly.
            alias = table_name
            self.table_map[alias] = [alias]
        self.alias_refcount[alias] = 1
        self.tables.append(alias)
        return alias, True

    def ref_alias(self, alias):
        """ Increases the reference count for this alias. """
        self.alias_refcount[alias] += 1

    def unref_alias(self, alias):
        """ Decreases the reference count for this alias. """
        self.alias_refcount[alias] -= 1

    def promote_alias(self, alias, unconditional=False):
        """
        Promotes the join type of an alias to an outer join if it's possible
        for the join to contain NULL values on the left. If 'unconditional' is
        False, the join is only promoted if it is nullable, otherwise it is
        always promoted.

        Returns True if the join was promoted.
        """
        if ((unconditional or self.alias_map[alias][NULLABLE]) and
                self.alias_map[alias][JOIN_TYPE] != self.LOUTER):
            data = list(self.alias_map[alias])
            data[JOIN_TYPE] = self.LOUTER
            self.alias_map[alias] = tuple(data)
            return True
        return False

    def promote_alias_chain(self, chain, must_promote=False):
        """
        Walks along a chain of aliases, promoting the first nullable join and
        any joins following that. If 'must_promote' is True, all the aliases in
        the chain are promoted.
        """
        for alias in chain:
            if self.promote_alias(alias, must_promote):
                must_promote = True

    def promote_unused_aliases(self, initial_refcounts, used_aliases):
        """
        Given a "before" copy of the alias_refcounts dictionary (as
        'initial_refcounts') and a collection of aliases that may have been
        changed or created, works out which aliases have been created since
        then and which ones haven't been used and promotes all of those
        aliases, plus any children of theirs in the alias tree, to outer joins.
        """
        # FIXME: There's some (a lot of!) overlap with the similar OR promotion
        # in add_filter(). It's not quite identical, but is very similar. So
        # pulling out the common bits is something for later.
        considered = {}
        for alias in self.tables:
            if alias not in used_aliases:
                continue
            if (alias not in initial_refcounts or
                    self.alias_refcount[alias] == initial_refcounts[alias]):
                parent = self.alias_map[alias][LHS_ALIAS]
                must_promote = considered.get(parent, False)
                promoted = self.promote_alias(alias, must_promote)
                considered[alias] = must_promote or promoted

    def change_aliases(self, change_map):
        """
        Changes the aliases in change_map (which maps old-alias -> new-alias),
        relabelling any references to them in select columns and the where
        clause.
        """
        assert set(change_map.keys()).intersection(set(change_map.values())) == set()

        # 1. Update references in "select" (normal columns plus aliases),
        # "group by", "where" and "having".
        self.where.relabel_aliases(change_map)
        self.having.relabel_aliases(change_map)
        for columns in (self.select, self.aggregates.values(), self.group_by or []):
            for pos, col in enumerate(columns):
                if isinstance(col, (list, tuple)):
                    old_alias = col[0]
                    columns[pos] = (change_map.get(old_alias, old_alias), col[1])
                else:
                    col.relabel_aliases(change_map)

        # 2. Rename the alias in the internal table/alias datastructures.
        for old_alias, new_alias in change_map.iteritems():
            alias_data = list(self.alias_map[old_alias])
            alias_data[RHS_ALIAS] = new_alias

            t = self.rev_join_map[old_alias]
            data = list(self.join_map[t])
            data[data.index(old_alias)] = new_alias
            self.join_map[t] = tuple(data)
            self.rev_join_map[new_alias] = t
            del self.rev_join_map[old_alias]
            self.alias_refcount[new_alias] = self.alias_refcount[old_alias]
            del self.alias_refcount[old_alias]
            self.alias_map[new_alias] = tuple(alias_data)
            del self.alias_map[old_alias]

            table_aliases = self.table_map[alias_data[TABLE_NAME]]
            for pos, alias in enumerate(table_aliases):
                if alias == old_alias:
                    table_aliases[pos] = new_alias
                    break
            for pos, alias in enumerate(self.tables):
                if alias == old_alias:
                    self.tables[pos] = new_alias
                    break
        for key, alias in self.included_inherited_models.items():
            if alias in change_map:
                self.included_inherited_models[key] = change_map[alias]

        # 3. Update any joins that refer to the old alias.
        for alias, data in self.alias_map.iteritems():
            lhs = data[LHS_ALIAS]
            if lhs in change_map:
                data = list(data)
                data[LHS_ALIAS] = change_map[lhs]
                self.alias_map[alias] = tuple(data)

    def bump_prefix(self, exceptions=()):
        """
        Changes the alias prefix to the next letter in the alphabet and
        relabels all the aliases. Even tables that previously had no alias will
        get an alias after this call (it's mostly used for nested queries and
        the outer query will already be using the non-aliased table name).

        Subclasses who create their own prefix should override this method to
        produce a similar result (a new prefix and relabelled aliases).

        The 'exceptions' parameter is a container that holds alias names which
        should not be changed.
        """
        current = ord(self.alias_prefix)
        assert current < ord('Z')
        prefix = chr(current + 1)
        self.alias_prefix = prefix
        change_map = {}
        for pos, alias in enumerate(self.tables):
            if alias in exceptions:
                continue
            new_alias = '%s%d' % (prefix, pos)
            change_map[alias] = new_alias
            self.tables[pos] = new_alias
        self.change_aliases(change_map)

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
        return len([1 for count in self.alias_refcount.itervalues() if count])

    def join(self, connection, always_create=False, exclusions=(),
            promote=False, outer_if_first=False, nullable=False, reuse=None):
        """
        Returns an alias for the join in 'connection', either reusing an
        existing alias for that join or creating a new one. 'connection' is a
        tuple (lhs, table, lhs_col, col) where 'lhs' is either an existing
        table alias or a table name. The join correspods to the SQL equivalent
        of::

            lhs.lhs_col = table.col

        If 'always_create' is True and 'reuse' is None, a new alias is always
        created, regardless of whether one already exists or not. If
        'always_create' is True and 'reuse' is a set, an alias in 'reuse' that
        matches the connection will be returned, if possible.  If
        'always_create' is False, the first existing alias that matches the
        'connection' is returned, if any. Otherwise a new join is created.

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
        if lhs in self.alias_map:
            lhs_table = self.alias_map[lhs][TABLE_NAME]
        else:
            lhs_table = lhs

        if reuse and always_create and table in self.table_map:
            # Convert the 'reuse' to case to be "exclude everything but the
            # reusable set, minus exclusions, for this table".
            exclusions = set(self.table_map[table]).difference(reuse).union(set(exclusions))
            always_create = False
        t_ident = (lhs_table, table, lhs_col, col)
        if not always_create:
            for alias in self.join_map.get(t_ident, ()):
                if alias not in exclusions:
                    if lhs_table and not self.alias_refcount[self.alias_map[alias][LHS_ALIAS]]:
                        # The LHS of this join tuple is no longer part of the
                        # query, so skip this possibility.
                        continue
                    if self.alias_map[alias][LHS_ALIAS] != lhs:
                        continue
                    self.ref_alias(alias)
                    if promote:
                        self.promote_alias(alias)
                    return alias

        # No reuse is possible, so we need a new alias.
        alias, _ = self.table_alias(table, True)
        if not lhs:
            # Not all tables need to be joined to anything. No join type
            # means the later columns are ignored.
            join_type = None
        elif promote or outer_if_first:
            join_type = self.LOUTER
        else:
            join_type = self.INNER
        join = (table, alias, join_type, lhs, lhs_col, col, nullable)
        self.alias_map[alias] = join
        if t_ident in self.join_map:
            self.join_map[t_ident] += (alias,)
        else:
            self.join_map[t_ident] = (alias,)
        self.rev_join_map[alias] = t_ident
        return alias

    def setup_inherited_models(self):
        """
        If the model that is the basis for this QuerySet inherits other models,
        we need to ensure that those other models have their tables included in
        the query.

        We do this as a separate step so that subclasses know which
        tables are going to be active in the query, without needing to compute
        all the select columns (this method is called from pre_sql_setup(),
        whereas column determination is a later part, and side-effect, of
        as_sql()).
        """
        opts = self.model._meta
        root_alias = self.tables[0]
        seen = {None: root_alias}
        proxied_model = opts.proxy and opts.proxy_for_model or 0
        for field, model in opts.get_fields_with_model():
            if model not in seen:
                if model is proxied_model:
                    seen[model] = root_alias
                else:
                    link_field = opts.get_ancestor_link(model)
                    seen[model] = self.join((root_alias, model._meta.db_table,
                            link_field.column, model._meta.pk.column))
        self.included_inherited_models = seen

    def remove_inherited_models(self):
        """
        Undoes the effects of setup_inherited_models(). Should be called
        whenever select columns (self.select) are set explicitly.
        """
        for key, alias in self.included_inherited_models.items():
            if key:
                self.unref_alias(alias)
        self.included_inherited_models = {}

    def fill_related_selections(self, opts=None, root_alias=None, cur_depth=1,
            used=None, requested=None, restricted=None, nullable=None,
            dupe_set=None, avoid_set=None):
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
            root_alias = self.get_initial_alias()
            self.related_select_cols = []
            self.related_select_fields = []
        if not used:
            used = set()
        if dupe_set is None:
            dupe_set = set()
        if avoid_set is None:
            avoid_set = set()
        orig_dupe_set = dupe_set

        # Setup for the case when only particular related fields should be
        # included in the related selection.
        if requested is None and restricted is not False:
            if isinstance(self.select_related, dict):
                requested = self.select_related
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
            if nullable or f.null:
                promote = True
            else:
                promote = False
            if model:
                int_opts = opts
                alias = root_alias
                alias_chain = []
                for int_model in opts.get_base_chain(model):
                    lhs_col = int_opts.parents[int_model].column
                    dedupe = lhs_col in opts.duplicate_targets
                    if dedupe:
                        avoid.update(self.dupe_avoidance.get(id(opts), lhs_col),
                                ())
                        dupe_set.add((opts, lhs_col))
                    int_opts = int_model._meta
                    alias = self.join((alias, int_opts.db_table, lhs_col,
                            int_opts.pk.column), exclusions=used,
                            promote=promote)
                    alias_chain.append(alias)
                    for (dupe_opts, dupe_col) in dupe_set:
                        self.update_dupe_avoidance(dupe_opts, dupe_col, alias)
                if self.alias_map[root_alias][JOIN_TYPE] == self.LOUTER:
                    self.promote_alias_chain(alias_chain, True)
            else:
                alias = root_alias

            dedupe = f.column in opts.duplicate_targets
            if dupe_set or dedupe:
                avoid.update(self.dupe_avoidance.get((id(opts), f.column), ()))
                if dedupe:
                    dupe_set.add((opts, f.column))

            alias = self.join((alias, table, f.column,
                    f.rel.get_related_field().column),
                    exclusions=used.union(avoid), promote=promote)
            used.add(alias)
            columns, aliases = self.get_default_columns(start_alias=alias,
                    opts=f.rel.to._meta, as_pairs=True)
            self.related_select_cols.extend(columns)
            if self.alias_map[alias][JOIN_TYPE] == self.LOUTER:
                self.promote_alias_chain(aliases, True)
            self.related_select_fields.extend(f.rel.to._meta.fields)
            if restricted:
                next = requested.get(f.name, {})
            else:
                next = False
            if f.null is not None:
                new_nullable = f.null
            else:
                new_nullable = None
            for dupe_opts, dupe_col in dupe_set:
                self.update_dupe_avoidance(dupe_opts, dupe_col, alias)
            self.fill_related_selections(f.rel.to._meta, alias, cur_depth + 1,
                    used, next, restricted, new_nullable, dupe_set, avoid)

    def add_aggregate(self, aggregate, model, alias, is_summary):
        """
        Adds a single aggregate expression to the Query
        """
        opts = model._meta
        field_list = aggregate.lookup.split(LOOKUP_SEP)
        if (len(field_list) == 1 and
            aggregate.lookup in self.aggregates.keys()):
            # Aggregate is over an annotation
            field_name = field_list[0]
            col = field_name
            source = self.aggregates[field_name]
            if not is_summary:
                raise FieldError("Cannot compute %s('%s'): '%s' is an aggregate" % (
                    aggregate.name, field_name, field_name))
        elif ((len(field_list) > 1) or
            (field_list[0] not in [i.name for i in opts.fields]) or
            self.group_by is None or
            not is_summary):
            # If:
            #   - the field descriptor has more than one part (foo__bar), or
            #   - the field descriptor is referencing an m2m/m2o field, or
            #   - this is a reference to a model field (possibly inherited), or
            #   - this is an annotation over a model field
            # then we need to explore the joins that are required.

            field, source, opts, join_list, last, _ = self.setup_joins(
                field_list, opts, self.get_initial_alias(), False)

            # Process the join chain to see if it can be trimmed
            col, _, join_list = self.trim_joins(source, join_list, last, False)

            # If the aggregate references a model or field that requires a join,
            # those joins must be LEFT OUTER - empty join rows must be returned
            # in order for zeros to be returned for those aggregates.
            for column_alias in join_list:
                self.promote_alias(column_alias, unconditional=True)

            col = (join_list[-1], col)
        else:
            # The simplest cases. No joins required -
            # just reference the provided column alias.
            field_name = field_list[0]
            source = opts.get_field(field_name)
            col = field_name

        # Add the aggregate to the query
        alias = truncate_name(alias, self.connection.ops.max_name_length())
        aggregate.add_to_query(self, alias, col=col, source=source, is_summary=is_summary)

    def add_filter(self, filter_expr, connector=AND, negate=False, trim=False,
            can_reuse=None, process_extras=True):
        """
        Add a single filter to the query. The 'filter_expr' is a pair:
        (filter_string, value). E.g. ('name__contains', 'fred')

        If 'negate' is True, this is an exclude() filter. It's important to
        note that this method does not negate anything in the where-clause
        object when inserting the filter constraints. This is because negated
        filters often require multiple calls to add_filter() and the negation
        should only happen once. So the caller is responsible for this (the
        caller will normally be add_q(), so that as an example).

        If 'trim' is True, we automatically trim the final join group (used
        internally when constructing nested queries).

        If 'can_reuse' is a set, we are processing a component of a
        multi-component filter (e.g. filter(Q1, Q2)). In this case, 'can_reuse'
        will be a set of table aliases that can be reused in this filter, even
        if we would otherwise force the creation of new aliases for a join
        (needed for nested Q-filters). The set is updated by this method.

        If 'process_extras' is set, any extra filters returned from the table
        joining process will be processed. This parameter is set to False
        during the processing of extra filters to avoid infinite recursion.
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

        # By default, this is a WHERE clause. If an aggregate is referenced
        # in the value, the filter will be promoted to a HAVING
        having_clause = False

        # Interpret '__exact=None' as the sql 'is NULL'; otherwise, reject all
        # uses of None as a query value.
        if value is None:
            if lookup_type != 'exact':
                raise ValueError("Cannot use None as a query value")
            lookup_type = 'isnull'
            value = True
        elif (value == '' and lookup_type == 'exact' and
              connection.features.interprets_empty_strings_as_nulls):
            lookup_type = 'isnull'
            value = True
        elif callable(value):
            value = value()
        elif hasattr(value, 'evaluate'):
            # If value is a query expression, evaluate it
            value = SQLEvaluator(value, self)
            having_clause = value.contains_aggregate

        for alias, aggregate in self.aggregates.items():
            if alias == parts[0]:
                entry = self.where_class()
                entry.add((aggregate, lookup_type, value), AND)
                if negate:
                    entry.negate()
                self.having.add(entry, AND)
                return

        opts = self.get_meta()
        alias = self.get_initial_alias()
        allow_many = trim or not negate

        try:
            field, target, opts, join_list, last, extra_filters = self.setup_joins(
                    parts, opts, alias, True, allow_many, can_reuse=can_reuse,
                    negate=negate, process_extras=process_extras)
        except MultiJoin, e:
            self.split_exclude(filter_expr, LOOKUP_SEP.join(parts[:e.level]),
                    can_reuse)
            return

        if (lookup_type == 'isnull' and value is True and not negate and
                len(join_list) > 1):
            # If the comparison is against NULL, we may need to use some left
            # outer joins when creating the join chain. This is only done when
            # needed, as it's less efficient at the database level.
            self.promote_alias_chain(join_list)

        # Process the join list to see if we can remove any inner joins from
        # the far end (fewer tables in a query is better).
        col, alias, join_list = self.trim_joins(target, join_list, last, trim)

        if connector == OR:
            # Some joins may need to be promoted when adding a new filter to a
            # disjunction. We walk the list of new joins and where it diverges
            # from any previous joins (ref count is 1 in the table list), we
            # make the new additions (and any existing ones not used in the new
            # join list) an outer join.
            join_it = iter(join_list)
            table_it = iter(self.tables)
            join_it.next(), table_it.next()
            table_promote = False
            join_promote = False
            for join in join_it:
                table = table_it.next()
                if join == table and self.alias_refcount[join] > 1:
                    continue
                join_promote = self.promote_alias(join)
                if table != join:
                    table_promote = self.promote_alias(table)
                break
            self.promote_alias_chain(join_it, join_promote)
            self.promote_alias_chain(table_it, table_promote)


        if having_clause:
            self.having.add((Constraint(alias, col, field), lookup_type, value),
                connector)
        else:
            self.where.add((Constraint(alias, col, field), lookup_type, value),
                connector)

        if negate:
            self.promote_alias_chain(join_list)
            if lookup_type != 'isnull':
                if len(join_list) > 1:
                    for alias in join_list:
                        if self.alias_map[alias][JOIN_TYPE] == self.LOUTER:
                            j_col = self.alias_map[alias][RHS_JOIN_COL]
                            entry = self.where_class()
                            entry.add((Constraint(alias, j_col, None), 'isnull', True), AND)
                            entry.negate()
                            self.where.add(entry, AND)
                            break
                elif not (lookup_type == 'in' and not value) and field.null:
                    # Leaky abstraction artifact: We have to specifically
                    # exclude the "foo__in=[]" case from this handling, because
                    # it's short-circuited in the Where class.
                    entry = self.where_class()
                    entry.add((Constraint(alias, col, None), 'isnull', True), AND)
                    entry.negate()
                    self.where.add(entry, AND)

        if can_reuse is not None:
            can_reuse.update(join_list)
        if process_extras:
            for filter in extra_filters:
                self.add_filter(filter, negate=negate, can_reuse=can_reuse,
                        process_extras=False)

    def add_q(self, q_object, used_aliases=None):
        """
        Adds a Q-object to the current filter.

        Can also be used to add anything that has an 'add_to_query()' method.
        """
        if used_aliases is None:
            used_aliases = self.used_aliases
        if hasattr(q_object, 'add_to_query'):
            # Complex custom objects are responsible for adding themselves.
            q_object.add_to_query(self, used_aliases)
        else:
            if self.where and q_object.connector != AND and len(q_object) > 1:
                self.where.start_subtree(AND)
                subtree = True
            else:
                subtree = False
            connector = AND
            for child in q_object.children:
                if connector == OR:
                    refcounts_before = self.alias_refcount.copy()
                if isinstance(child, Node):
                    self.where.start_subtree(connector)
                    self.add_q(child, used_aliases)
                    self.where.end_subtree()
                else:
                    self.add_filter(child, connector, q_object.negated,
                            can_reuse=used_aliases)
                if connector == OR:
                    # Aliases that were newly added or not used at all need to
                    # be promoted to outer joins if they are nullable relations.
                    # (they shouldn't turn the whole conditional into the empty
                    # set just because they don't match anything).
                    self.promote_unused_aliases(refcounts_before, used_aliases)
                connector = q_object.connector
            if q_object.negated:
                self.where.negate()
            if subtree:
                self.where.end_subtree()
        if self.filter_is_sticky:
            self.used_aliases = used_aliases

    def setup_joins(self, names, opts, alias, dupe_multis, allow_many=True,
            allow_explicit_fk=False, can_reuse=None, negate=False,
            process_extras=True):
        """
        Compute the necessary table joins for the passage through the fields
        given in 'names'. 'opts' is the Options class for the current model
        (which gives the table we are joining to), 'alias' is the alias for the
        table we are joining to. If dupe_multis is True, any many-to-many or
        many-to-one joins will always create a new alias (necessary for
        disjunctive filters). If can_reuse is not None, it's a list of aliases
        that can be reused in these joins (nothing else can be reused in this
        case). Finally, 'negate' is used in the same sense as for add_filter()
        -- it indicates an exclude() filter, or something similar. It is only
        passed in here so that it can be passed to a field's extra_filter() for
        customised behaviour.

        Returns the final field involved in the join, the target database
        column (used for any 'where' constraint), the final 'opts' value and the
        list of tables joined.
        """
        joins = [alias]
        last = [0]
        dupe_set = set()
        exclusions = set()
        extra_filters = []
        for pos, name in enumerate(names):
            try:
                exclusions.add(int_alias)
            except NameError:
                pass
            exclusions.add(alias)
            last.append(len(joins))
            if name == 'pk':
                name = opts.pk.name
            try:
                field, model, direct, m2m = opts.get_field_by_name(name)
            except FieldDoesNotExist:
                for f in opts.fields:
                    if allow_explicit_fk and name == f.attname:
                        # XXX: A hack to allow foo_id to work in values() for
                        # backwards compatibility purposes. If we dropped that
                        # feature, this could be removed.
                        field, model, direct, m2m = opts.get_field_by_name(f.name)
                        break
                else:
                    names = opts.get_all_field_names() + self.aggregate_select.keys()
                    raise FieldError("Cannot resolve keyword %r into field. "
                            "Choices are: %s" % (name, ", ".join(names)))

            if not allow_many and (m2m or not direct):
                for alias in joins:
                    self.unref_alias(alias)
                raise MultiJoin(pos + 1)
            if model:
                # The field lives on a base class of the current model.
                proxied_model = opts.proxy and opts.proxy_for_model or 0
                for int_model in opts.get_base_chain(model):
                    if int_model is proxied_model:
                        opts = int_model._meta
                    else:
                        lhs_col = opts.parents[int_model].column
                        dedupe = lhs_col in opts.duplicate_targets
                        if dedupe:
                            exclusions.update(self.dupe_avoidance.get(
                                    (id(opts), lhs_col), ()))
                            dupe_set.add((opts, lhs_col))
                        opts = int_model._meta
                        alias = self.join((alias, opts.db_table, lhs_col,
                                opts.pk.column), exclusions=exclusions)
                        joins.append(alias)
                        exclusions.add(alias)
                        for (dupe_opts, dupe_col) in dupe_set:
                            self.update_dupe_avoidance(dupe_opts, dupe_col,
                                    alias)
            cached_data = opts._join_cache.get(name)
            orig_opts = opts
            dupe_col = direct and field.column or field.field.column
            dedupe = dupe_col in opts.duplicate_targets
            if dupe_set or dedupe:
                if dedupe:
                    dupe_set.add((opts, dupe_col))
                exclusions.update(self.dupe_avoidance.get((id(opts), dupe_col),
                        ()))

            if process_extras and hasattr(field, 'extra_filters'):
                extra_filters.extend(field.extra_filters(names, pos, negate))
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
                            dupe_multis, exclusions, nullable=True,
                            reuse=can_reuse)
                    if int_alias == table2 and from_col2 == to_col2:
                        joins.append(int_alias)
                        alias = int_alias
                    else:
                        alias = self.join(
                                (int_alias, table2, from_col2, to_col2),
                                dupe_multis, exclusions, nullable=True,
                                reuse=can_reuse)
                        joins.extend([int_alias, alias])
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
                            exclusions=exclusions, nullable=field.null)
                    joins.append(alias)
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
                            dupe_multis, exclusions, nullable=True,
                            reuse=can_reuse)
                    alias = self.join((int_alias, table2, from_col2, to_col2),
                            dupe_multis, exclusions, nullable=True,
                            reuse=can_reuse)
                    joins.extend([int_alias, alias])
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
                            dupe_multis, exclusions, nullable=True,
                            reuse=can_reuse)
                    joins.append(alias)

            for (dupe_opts, dupe_col) in dupe_set:
                try:
                    self.update_dupe_avoidance(dupe_opts, dupe_col, int_alias)
                except NameError:
                    self.update_dupe_avoidance(dupe_opts, dupe_col, alias)

        if pos != len(names) - 1:
            if pos == len(names) - 2:
                raise FieldError("Join on field %r not permitted. Did you misspell %r for the lookup type?" % (name, names[pos + 1]))
            else:
                raise FieldError("Join on field %r not permitted." % name)

        return field, target, opts, joins, last, extra_filters

    def trim_joins(self, target, join_list, last, trim):
        """
        Sometimes joins at the end of a multi-table sequence can be trimmed. If
        the final join is against the same column as we are comparing against,
        and is an inner join, we can go back one step in a join chain and
        compare against the LHS of the join instead (and then repeat the
        optimization). The result, potentially, involves less table joins.

        The 'target' parameter is the final field being joined to, 'join_list'
        is the full list of join aliases.

        The 'last' list contains offsets into 'join_list', corresponding to
        each component of the filter.  Many-to-many relations, for example, add
        two tables to the join list and we want to deal with both tables the
        same way, so 'last' has an entry for the first of the two tables and
        then the table immediately after the second table, in that case.

        The 'trim' parameter forces the final piece of the join list to be
        trimmed before anything. See the documentation of add_filter() for
        details about this.

        Returns the final active column and table alias and the new active
        join_list.
        """
        final = len(join_list)
        penultimate = last.pop()
        if penultimate == final:
            penultimate = last.pop()
        if trim and len(join_list) > 1:
            extra = join_list[penultimate:]
            join_list = join_list[:penultimate]
            final = penultimate
            penultimate = last.pop()
            col = self.alias_map[extra[0]][LHS_JOIN_COL]
            for alias in extra:
                self.unref_alias(alias)
        else:
            col = target.column
        alias = join_list[-1]
        while final > 1:
            join = self.alias_map[alias]
            if col != join[RHS_JOIN_COL] or join[JOIN_TYPE] != self.INNER:
                break
            self.unref_alias(alias)
            alias = join[LHS_ALIAS]
            col = join[LHS_JOIN_COL]
            join_list = join_list[:-1]
            final -= 1
            if final == penultimate:
                penultimate = last.pop()
        return col, alias, join_list

    def update_dupe_avoidance(self, opts, col, alias):
        """
        For a column that is one of multiple pointing to the same table, update
        the internal data structures to note that this alias shouldn't be used
        for those other columns.
        """
        ident = id(opts)
        for name in opts.duplicate_targets[col]:
            try:
                self.dupe_avoidance[ident, name].add(alias)
            except KeyError:
                self.dupe_avoidance[ident, name] = set([alias])

    def split_exclude(self, filter_expr, prefix, can_reuse):
        """
        When doing an exclude against any kind of N-to-many relation, we need
        to use a subquery. This method constructs the nested query, given the
        original exclude filter (filter_expr) and the portion up to the first
        N-to-many relation field.
        """
        query = Query(self.model, self.connection)
        query.add_filter(filter_expr, can_reuse=can_reuse)
        query.bump_prefix()
        query.clear_ordering(True)
        query.set_start(prefix)
        self.add_filter(('%s__in' % prefix, query), negate=True, trim=True,
                can_reuse=can_reuse)

        # If there's more than one join in the inner query (before any initial
        # bits were trimmed -- which means the last active table is more than
        # two places into the alias list), we need to also handle the
        # possibility that the earlier joins don't match anything by adding a
        # comparison to NULL (e.g. in
        # Tag.objects.exclude(parent__parent__name='t1'), a tag with no parent
        # would otherwise be overlooked).
        active_positions = [pos for (pos, count) in
                enumerate(query.alias_refcount.itervalues()) if count]
        if active_positions[-1] > 1:
            self.add_filter(('%s__isnull' % prefix, False), negate=True,
                    trim=True, can_reuse=can_reuse)

    def set_limits(self, low=None, high=None):
        """
        Adjusts the limits on the rows retrieved. We use low/high to set these,
        as it makes it more Pythonic to read and write. When the SQL query is
        created, they are converted to the appropriate offset and limit values.

        Any limits passed in here are applied relative to the existing
        constraints. So low is added to the current low value and both will be
        clamped to any existing high value.
        """
        if high is not None:
            if self.high_mark is not None:
                self.high_mark = min(self.high_mark, self.low_mark + high)
            else:
                self.high_mark = self.low_mark + high
        if low is not None:
            if self.high_mark is not None:
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
        return not self.low_mark and self.high_mark is None

    def clear_select_fields(self):
        """
        Clears the list of fields to select (but not extra_select columns).
        Some queryset types completely replace any existing list of select
        columns.
        """
        self.select = []
        self.select_fields = []

    def add_fields(self, field_names, allow_m2m=True):
        """
        Adds the given (model) fields to the select set. The field names are
        added in the order specified.
        """
        alias = self.get_initial_alias()
        opts = self.get_meta()

        try:
            for name in field_names:
                field, target, u2, joins, u3, u4 = self.setup_joins(
                        name.split(LOOKUP_SEP), opts, alias, False, allow_m2m,
                        True)
                final_alias = joins[-1]
                col = target.column
                if len(joins) > 1:
                    join = self.alias_map[final_alias]
                    if col == join[RHS_JOIN_COL]:
                        self.unref_alias(final_alias)
                        final_alias = join[LHS_ALIAS]
                        col = join[LHS_JOIN_COL]
                        joins = joins[:-1]
                self.promote_alias_chain(joins[1:])
                self.select.append((final_alias, col))
                self.select_fields.append(field)
        except MultiJoin:
            raise FieldError("Invalid field name: '%s'" % name)
        except FieldError:
            names = opts.get_all_field_names() + self.extra_select.keys() + self.aggregate_select.keys()
            names.sort()
            raise FieldError("Cannot resolve keyword %r into field. "
                    "Choices are: %s" % (name, ", ".join(names)))
        self.remove_inherited_models()

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
        self.extra_order_by = ()
        if force_empty:
            self.default_ordering = False

    def set_group_by(self):
        """
        Expands the GROUP BY clause required by the query.

        This will usually be the set of all non-aggregate fields in the
        return data. If the database backend supports grouping by the
        primary key, and the query would be equivalent, the optimization
        will be made automatically.
        """
        self.group_by = []
        if self.connection.features.allows_group_by_pk:
            if len(self.select) == len(self.model._meta.fields):
                self.group_by.append((self.model._meta.db_table,
                                      self.model._meta.pk.column))
                return

        for sel in self.select:
            self.group_by.append(sel)

    def add_count_column(self):
        """
        Converts the query to do count(...) or count(distinct(pk)) in order to
        get its size.
        """
        if not self.distinct:
            if not self.select:
                count = self.aggregates_module.Count('*', is_summary=True)
            else:
                assert len(self.select) == 1, \
                        "Cannot add count col with multiple cols in 'select': %r" % self.select
                count = self.aggregates_module.Count(self.select[0])
        else:
            opts = self.model._meta
            if not self.select:
                count = self.aggregates_module.Count((self.join((None, opts.db_table, None, None)), opts.pk.column),
                                         is_summary=True, distinct=True)
            else:
                # Because of SQL portability issues, multi-column, distinct
                # counts need a sub-query -- see get_count() for details.
                assert len(self.select) == 1, \
                        "Cannot add count col with multiple cols in 'select'."

                count = self.aggregates_module.Count(self.select[0], distinct=True)
            # Distinct handling is done in Count(), so don't do it at this
            # level.
            self.distinct = False

        # Set only aggregate to be the count column.
        # Clear out the select cache to reflect the new unmasked aggregates.
        self.aggregates = {None: count}
        self.set_aggregate_mask(None)
        self.group_by = None

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
        self.related_select_cols = []
        self.related_select_fields = []

    def add_extra(self, select, select_params, where, params, tables, order_by):
        """
        Adds data to the various extra_* attributes for user-created additions
        to the query.
        """
        if select:
            # We need to pair any placeholder markers in the 'select'
            # dictionary with their parameters in 'select_params' so that
            # subsequent updates to the select dictionary also adjust the
            # parameters appropriately.
            select_pairs = SortedDict()
            if select_params:
                param_iter = iter(select_params)
            else:
                param_iter = iter([])
            for name, entry in select.items():
                entry = force_unicode(entry)
                entry_params = []
                pos = entry.find("%s")
                while pos != -1:
                    entry_params.append(param_iter.next())
                    pos = entry.find("%s", pos + 2)
                select_pairs[name] = (entry, entry_params)
            # This is order preserving, since self.extra_select is a SortedDict.
            self.extra_select.update(select_pairs)
        if where:
            self.extra_where += tuple(where)
        if params:
            self.extra_params += tuple(params)
        if tables:
            self.extra_tables += tuple(tables)
        if order_by:
            self.extra_order_by = order_by

    def clear_deferred_loading(self):
        """
        Remove any fields from the deferred loading set.
        """
        self.deferred_loading = (set(), True)

    def add_deferred_loading(self, field_names):
        """
        Add the given list of model field names to the set of fields to
        exclude from loading from the database when automatic column selection
        is done. The new field names are added to any existing field names that
        are deferred (or removed from any existing field names that are marked
        as the only ones for immediate loading).
        """
        # Fields on related models are stored in the literal double-underscore
        # format, so that we can use a set datastructure. We do the foo__bar
        # splitting and handling when computing the SQL colum names (as part of
        # get_columns()).
        existing, defer = self.deferred_loading
        if defer:
            # Add to existing deferred names.
            self.deferred_loading = existing.union(field_names), True
        else:
            # Remove names from the set of any existing "immediate load" names.
            self.deferred_loading = existing.difference(field_names), False

    def add_immediate_loading(self, field_names):
        """
        Add the given list of model field names to the set of fields to
        retrieve when the SQL is executed ("immediate loading" fields). The
        field names replace any existing immediate loading field names. If
        there are field names already specified for deferred loading, those
        names are removed from the new field_names before storing the new names
        for immediate loading. (That is, immediate loading overrides any
        existing immediate values, but respects existing deferrals.)
        """
        existing, defer = self.deferred_loading
        if defer:
            # Remove any existing deferred names from the current set before
            # setting the new names.
            self.deferred_loading = set(field_names).difference(existing), False
        else:
            # Replace any existing "immediate load" field names.
            self.deferred_loading = set(field_names), False

    def get_loaded_field_names(self):
        """
        If any fields are marked to be deferred, returns a dictionary mapping
        models to a set of names in those fields that will be loaded. If a
        model is not in the returned dictionary, none of it's fields are
        deferred.

        If no fields are marked for deferral, returns an empty dictionary.
        """
        collection = {}
        self.deferred_to_data(collection, self.get_loaded_field_names_cb)
        return collection

    def get_loaded_field_names_cb(self, target, model, fields):
        """
        Callback used by get_deferred_field_names().
        """
        target[model] = set([f.name for f in fields])

    def trim_extra_select(self, names):
        """
        Removes any aliases in the extra_select dictionary that aren't in
        'names'.

        This is needed if we are selecting certain values that don't incldue
        all of the extra_select names.
        """
        for key in set(self.extra_select).difference(set(names)):
            del self.extra_select[key]

    def set_aggregate_mask(self, names):
        "Set the mask of aggregates that will actually be returned by the SELECT"
        self.aggregate_select_mask = names
        self._aggregate_select_cache = None

    def _aggregate_select(self):
        """The SortedDict of aggregate columns that are not masked, and should
        be used in the SELECT clause.

        This result is cached for optimization purposes.
        """
        if self._aggregate_select_cache is not None:
            return self._aggregate_select_cache
        elif self.aggregate_select_mask is not None:
            self._aggregate_select_cache = SortedDict([
                (k,v) for k,v in self.aggregates.items()
                if k in self.aggregate_select_mask
            ])
            return self._aggregate_select_cache
        else:
            return self.aggregates
    aggregate_select = property(_aggregate_select)

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
        field, col, opts, joins, last, extra = self.setup_joins(
                start.split(LOOKUP_SEP), opts, alias, False)
        select_col = self.alias_map[joins[1]][LHS_JOIN_COL]
        select_alias = alias

        # The call to setup_joins added an extra reference to everything in
        # joins. Reverse that.
        for alias in joins:
            self.unref_alias(alias)

        # We might be able to trim some joins from the front of this query,
        # providing that we only traverse "always equal" connections (i.e. rhs
        # is *always* the same value as lhs).
        for alias in joins[1:]:
            join_info = self.alias_map[alias]
            if (join_info[LHS_JOIN_COL] != select_col
                    or join_info[JOIN_TYPE] != self.INNER):
                break
            self.unref_alias(select_alias)
            select_alias = join_info[RHS_ALIAS]
            select_col = join_info[RHS_JOIN_COL]
        self.select = [(select_alias, select_col)]
        self.remove_inherited_models()

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
            if self.ordering_aliases:
                return cursor.fetchone()[:-len(results.ordering_aliases)]
            return cursor.fetchone()

        # The MULTI case.
        if self.ordering_aliases:
            result = order_modified_iter(cursor, len(self.ordering_aliases),
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

# Use the backend's custom Query class if it defines one. Otherwise, use the
# default.
if connection.features.uses_custom_query_class:
    Query = connection.ops.query_class(BaseQuery)
else:
    Query = BaseQuery

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

def setup_join_cache(sender, **kwargs):
    """
    The information needed to join between model fields is something that is
    invariant over the life of the model, so we cache it in the model's Options
    class, rather than recomputing it all the time.

    This method initialises the (empty) cache when the model is created.
    """
    sender._meta._join_cache = {}

signals.class_prepared.connect(setup_join_cache)

def add_to_dict(data, key, value):
    """
    A helper function to add "value" to the set of values for "key", whether or
    not "key" already exists.
    """
    if key in data:
        data[key].add(value)
    else:
        data[key] = set([value])
