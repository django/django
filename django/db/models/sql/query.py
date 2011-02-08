"""
Create SQL statements for QuerySets.

The code in here encapsulates all of the SQL construction so that QuerySets
themselves do not have to (and could be backed by things other than SQL
databases). The abstraction barrier only works one way: this module has to know
all about the internals of models in order to get the information it needs.
"""

from django.utils.copycompat import deepcopy
from django.utils.tree import Node
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_unicode
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models import signals
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query_utils import select_related_descend, InvalidQuery
from django.db.models.sql import aggregates as base_aggregates_module
from django.db.models.sql.constants import *
from django.db.models.sql.datastructures import EmptyResultSet, Empty, MultiJoin
from django.db.models.sql.expressions import SQLEvaluator
from django.db.models.sql.where import (WhereNode, Constraint, EverythingNode,
    ExtraWhere, AND, OR)
from django.core.exceptions import FieldError

__all__ = ['Query', 'RawQuery']

class RawQuery(object):
    """
    A single raw SQL query
    """

    def __init__(self, sql, using, params=None):
        self.validate_sql(sql)
        self.params = params or ()
        self.sql = sql
        self.using = using
        self.cursor = None

        # Mirror some properties of a normal query so that
        # the compiler can be used to process results.
        self.low_mark, self.high_mark = 0, None  # Used for offset/limit
        self.extra_select = {}
        self.aggregate_select = {}

    def clone(self, using):
        return RawQuery(self.sql, using, params=self.params)

    def convert_values(self, value, field, connection):
        """Convert the database-returned value into a type that is consistent
        across database backends.

        By default, this defers to the underlying backend operations, but
        it can be overridden by Query classes for specific backends.
        """
        return connection.ops.convert_values(value, field)

    def get_columns(self):
        if self.cursor is None:
            self._execute_query()
        converter = connections[self.using].introspection.table_name_converter
        return [converter(column_meta[0])
                for column_meta in self.cursor.description]

    def validate_sql(self, sql):
        if not sql.lower().strip().startswith('select'):
            raise InvalidQuery('Raw queries are limited to SELECT queries. Use '
                               'connection.cursor directly for other types of queries.')

    def __iter__(self):
        # Always execute a new query for a new iterator.
        # This could be optimized with a cache at the expense of RAM.
        self._execute_query()
        if not connections[self.using].features.can_use_chunked_reads:
            # If the database can't use chunked reads we need to make sure we
            # evaluate the entire query up front.
            result = list(self.cursor)
        else:
            result = self.cursor
        return iter(result)

    def __repr__(self):
        return "<RawQuery: %r>" % (self.sql % self.params)

    def _execute_query(self):
        self.cursor = connections[self.using].cursor()
        self.cursor.execute(self.sql, self.params)


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
    aggregates_module = base_aggregates_module

    compiler = 'SQLCompiler'

    def __init__(self, model, where=WhereNode):
        self.model = model
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
        self.extra = SortedDict()  # Maps col_alias -> (col_sql, params).
        self.extra_select_mask = None
        self._extra_select_cache = None

        self.extra_tables = ()
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
        sql, params = self.get_compiler(DEFAULT_DB_ALIAS).as_sql()
        return sql % params

    def __deepcopy__(self, memo):
        result = self.clone(memo=memo)
        memo[id(self)] = result
        return result

    def __getstate__(self):
        """
        Pickling support.
        """
        obj_dict = self.__dict__.copy()
        obj_dict['related_select_fields'] = []
        obj_dict['related_select_cols'] = []

        # Fields can't be pickled, so if a field list has been
        # specified, we pickle the list of field names instead.
        # None is also a possible value; that can pass as-is
        obj_dict['select_fields'] = [
            f is not None and f.name or None
            for f in obj_dict['select_fields']
        ]
        return obj_dict

    def __setstate__(self, obj_dict):
        """
        Unpickling support.
        """
        # Rebuild list of field instances
        opts = obj_dict['model']._meta
        obj_dict['select_fields'] = [
            name is not None and opts.get_field(name) or None
            for name in obj_dict['select_fields']
        ]

        self.__dict__.update(obj_dict)

    def prepare(self):
        return self

    def get_compiler(self, using=None, connection=None):
        if using is None and connection is None:
            raise ValueError("Need either using or connection")
        if using:
            connection = connections[using]

        # Check that the compiler will be able to execute the query
        for alias, aggregate in self.aggregate_select.items():
            connection.ops.check_aggregate_support(aggregate)

        return connection.ops.compiler(self.compiler)(self, connection, using)

    def get_meta(self):
        """
        Returns the Options instance (the model._meta) from which to start
        processing. Normally, this is self.model._meta, but it can be changed
        by subclasses.
        """
        return self.model._meta

    def clone(self, klass=None, memo=None, **kwargs):
        """
        Creates a copy of the current instance. The 'kwargs' parameter can be
        used by clients to update attributes after copying has taken place.
        """
        obj = Empty()
        obj.__class__ = klass or self.__class__
        obj.model = self.model
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
        obj.where = deepcopy(self.where, memo=memo)
        obj.where_class = self.where_class
        if self.group_by is None:
            obj.group_by = None
        else:
            obj.group_by = self.group_by[:]
        obj.having = deepcopy(self.having, memo=memo)
        obj.order_by = self.order_by[:]
        obj.low_mark, obj.high_mark = self.low_mark, self.high_mark
        obj.distinct = self.distinct
        obj.select_related = self.select_related
        obj.related_select_cols = []
        obj.aggregates = deepcopy(self.aggregates, memo=memo)
        if self.aggregate_select_mask is None:
            obj.aggregate_select_mask = None
        else:
            obj.aggregate_select_mask = self.aggregate_select_mask.copy()
        # _aggregate_select_cache cannot be copied, as doing so breaks the
        # (necessary) state in which both aggregates and
        # _aggregate_select_cache point to the same underlying objects.
        # It will get re-populated in the cloned queryset the next time it's
        # used.
        obj._aggregate_select_cache = None
        obj.max_depth = self.max_depth
        obj.extra = self.extra.copy()
        if self.extra_select_mask is None:
            obj.extra_select_mask = None
        else:
            obj.extra_select_mask = self.extra_select_mask.copy()
        if self._extra_select_cache is None:
            obj._extra_select_cache = None
        else:
            obj._extra_select_cache = self._extra_select_cache.copy()
        obj.extra_tables = self.extra_tables
        obj.extra_order_by = self.extra_order_by
        obj.deferred_loading = deepcopy(self.deferred_loading, memo=memo)
        if self.filter_is_sticky and self.used_aliases:
            obj.used_aliases = self.used_aliases.copy()
        else:
            obj.used_aliases = set()
        obj.filter_is_sticky = False
        obj.__dict__.update(kwargs)
        if hasattr(obj, '_setup_query'):
            obj._setup_query()
        return obj

    def convert_values(self, value, field, connection):
        """Convert the database-returned value into a type that is consistent
        across database backends.

        By default, this defers to the underlying backend operations, but
        it can be overridden by Query classes for specific backends.
        """
        return connection.ops.convert_values(value, field)

    def resolve_aggregate(self, value, aggregate, connection):
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
            return self.convert_values(value, aggregate.field, connection)

    def get_aggregation(self, using):
        """
        Returns the dictionary with the values of the existing aggregations.
        """
        if not self.aggregate_select:
            return {}

        # If there is a group by clause, aggregating does not add useful
        # information but retrieves only the first row. Aggregate
        # over the subquery instead.
        if self.group_by is not None:
            from django.db.models.sql.subqueries import AggregateQuery
            query = AggregateQuery(self.model)

            obj = self.clone()

            # Remove any aggregates marked for reduction from the subquery
            # and move them to the outer AggregateQuery.
            for alias, aggregate in self.aggregate_select.items():
                if aggregate.is_summary:
                    query.aggregate_select[alias] = aggregate
                    del obj.aggregate_select[alias]

            try:
                query.add_subquery(obj, using)
            except EmptyResultSet:
                return dict(
                    (alias, None)
                    for alias in query.aggregate_select
                )
        else:
            query = self
            self.select = []
            self.default_cols = False
            self.extra = {}
            self.remove_inherited_models()

        query.clear_ordering(True)
        query.clear_limits()
        query.select_related = False
        query.related_select_cols = []
        query.related_select_fields = []

        result = query.get_compiler(using).execute_sql(SINGLE)
        if result is None:
            result = [None for q in query.aggregate_select.items()]

        return dict([
            (alias, self.resolve_aggregate(val, aggregate, connection=connections[using]))
            for (alias, aggregate), val
            in zip(query.aggregate_select.items(), result)
        ])

    def get_count(self, using):
        """
        Performs a COUNT() query using the current filter constraints.
        """
        obj = self.clone()
        if len(self.select) > 1 or self.aggregate_select:
            # If a select clause exists, then the query has already started to
            # specify the columns that are to be returned.
            # In this case, we need to use a subquery to evaluate the count.
            from django.db.models.sql.subqueries import AggregateQuery
            subquery = obj
            subquery.clear_ordering(True)
            subquery.clear_limits()

            obj = AggregateQuery(obj.model)
            try:
                obj.add_subquery(subquery, using=using)
            except EmptyResultSet:
                # add_subquery evaluates the query, if it's an EmptyResultSet
                # then there are can be no results, and therefore there the
                # count is obviously 0
                return 0

        obj.add_count_column()
        number = obj.get_aggregation(using=using)[None]

        # Apply offset and limit constraints manually, since using LIMIT/OFFSET
        # in SQL (in variants that provide them) doesn't change the COUNT
        # output.
        number = max(0, number - self.low_mark)
        if self.high_mark is not None:
            number = min(number, self.high_mark - self.low_mark)

        return number

    def has_results(self, using):
        q = self.clone()
        q.add_extra({'a': 1}, None, None, None, None, None)
        q.select = []
        q.select_fields = []
        q.default_cols = False
        q.select_related = False
        q.set_extra_mask(('a',))
        q.set_aggregate_mask(())
        q.clear_ordering(True)
        q.set_limits(high=1)
        compiler = q.get_compiler(using=using)
        return bool(compiler.execute_sql(SINGLE))

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
            if self.extra and rhs.extra:
                raise ValueError("When merging querysets using 'or', you "
                        "cannot have extra(select=...) on both sides.")
        self.extra.update(rhs.extra)
        extra_select_mask = set()
        if self.extra_select_mask is not None:
            extra_select_mask.update(self.extra_select_mask)
        if rhs.extra_select_mask is not None:
            extra_select_mask.update(rhs.extra_select_mask)
        if extra_select_mask:
            self.set_extra_mask(extra_select_mask)
        self.extra_tables += rhs.extra_tables

        # Ordering uses the 'rhs' ordering, unless it has none, in which case
        # the current ordering is used.
        self.order_by = rhs.order_by and rhs.order_by[:] or self.order_by
        self.extra_order_by = rhs.extra_order_by or self.extra_order_by

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
                for field, m in model._meta.get_fields_with_model():
                    if field in values:
                        continue
                    add_to_dict(workset, m or model, field)
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
            # Now ensure that every model in the inheritance chain is mentioned
            # in the parent list. Again, it must be mentioned to ensure that
            # only "must include" fields are pulled in.
            for model in orig_opts.get_parent_list():
                if model not in seen:
                    seen[model] = set()
            for model, values in seen.iteritems():
                callback(target, model, values)


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
        for columns in [self.select, self.group_by or []]:
            for pos, col in enumerate(columns):
                if isinstance(col, (list, tuple)):
                    old_alias = col[0]
                    columns[pos] = (change_map.get(old_alias, old_alias), col[1])
                else:
                    col.relabel_aliases(change_map)
        for mapping in [self.aggregates]:
            for key, col in mapping.items():
                if isinstance(col, (list, tuple)):
                    old_alias = col[0]
                    mapping[key] = (change_map.get(old_alias, old_alias), col[1])
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

        # Skip all proxy to the root proxied model
        proxied_model = get_proxied_model(opts)

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

    def need_force_having(self, q_object):
        """
        Returns whether or not all elements of this q_object need to be put
        together in the HAVING clause.
        """
        for child in q_object.children:
            if isinstance(child, Node):
                if self.need_force_having(child):
                    return True
            else:
                if child[0].split(LOOKUP_SEP)[0] in self.aggregates:
                    return True
        return False

    def add_aggregate(self, aggregate, model, alias, is_summary):
        """
        Adds a single aggregate expression to the Query
        """
        opts = model._meta
        field_list = aggregate.lookup.split(LOOKUP_SEP)
        if len(field_list) == 1 and aggregate.lookup in self.aggregates:
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
        aggregate.add_to_query(self, alias, col=col, source=source, is_summary=is_summary)

    def add_filter(self, filter_expr, connector=AND, negate=False, trim=False,
            can_reuse=None, process_extras=True, force_having=False):
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
        elif callable(value):
            value = value()
        elif hasattr(value, 'evaluate'):
            # If value is a query expression, evaluate it
            value = SQLEvaluator(value, self)
            having_clause = value.contains_aggregate

        if parts[0] in self.aggregates:
            aggregate = self.aggregates[parts[0]]
            entry = self.where_class()
            entry.add((aggregate, lookup_type, value), AND)
            if negate:
                entry.negate()
            self.having.add(entry, connector)
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


        if having_clause or force_having:
            if (alias, col) not in self.group_by:
                self.group_by.append((alias, col))
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
                            entry.add(
                                (Constraint(alias, j_col, None), 'isnull', True),
                                AND
                            )
                            entry.negate()
                            self.where.add(entry, AND)
                            break
                if not (lookup_type == 'in'
                            and not hasattr(value, 'as_sql')
                            and not hasattr(value, '_as_sql')
                            and not value) and field.null:
                    # Leaky abstraction artifact: We have to specifically
                    # exclude the "foo__in=[]" case from this handling, because
                    # it's short-circuited in the Where class.
                    # We also need to handle the case where a subquery is provided
                    self.where.add((Constraint(alias, col, None), 'isnull', False), AND)

        if can_reuse is not None:
            can_reuse.update(join_list)
        if process_extras:
            for filter in extra_filters:
                self.add_filter(filter, negate=negate, can_reuse=can_reuse,
                        process_extras=False)

    def add_q(self, q_object, used_aliases=None, force_having=False):
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
            if q_object.connector == OR and not force_having:
                force_having = self.need_force_having(q_object)
            for child in q_object.children:
                if connector == OR:
                    refcounts_before = self.alias_refcount.copy()
                if force_having:
                    self.having.start_subtree(connector)
                else:
                    self.where.start_subtree(connector)
                if isinstance(child, Node):
                    self.add_q(child, used_aliases, force_having=force_having)
                else:
                    self.add_filter(child, connector, q_object.negated,
                            can_reuse=used_aliases, force_having=force_having)
                if force_having:
                    self.having.end_subtree()
                else:
                    self.where.end_subtree()

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
        int_alias = None
        for pos, name in enumerate(names):
            if int_alias is not None:
                exclusions.add(int_alias)
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
                # Skip the chain of proxy to the concrete proxied model
                proxied_model = get_proxied_model(opts)

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
                        from_col1 = opts.get_field_by_name(
                            field.m2m_target_field_name())[0].column
                        to_col1 = field.m2m_column_name()
                        opts = field.rel.to._meta
                        table2 = opts.db_table
                        from_col2 = field.m2m_reverse_name()
                        to_col2 = opts.get_field_by_name(
                            field.m2m_reverse_target_field_name())[0].column
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
                        from_col1 = opts.get_field_by_name(
                            field.m2m_reverse_target_field_name())[0].column
                        to_col1 = field.m2m_reverse_name()
                        opts = orig_field.opts
                        table2 = opts.db_table
                        from_col2 = field.m2m_column_name()
                        to_col2 = opts.get_field_by_name(
                            field.m2m_target_field_name())[0].column
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
                        # In case of a recursive FK, use the to_field for
                        # reverse lookups as well
                        if orig_field.model is local_field.model:
                            target = opts.get_field_by_name(
                                field.rel.field_name)[0]
                        else:
                            target = opts.pk
                        orig_opts._join_cache[name] = (table, from_col, to_col,
                                opts, target)

                    alias = self.join((alias, table, from_col, to_col),
                            dupe_multis, exclusions, nullable=True,
                            reuse=can_reuse)
                    joins.append(alias)

            for (dupe_opts, dupe_col) in dupe_set:
                if int_alias is None:
                    to_avoid = alias
                else:
                    to_avoid = int_alias
                self.update_dupe_avoidance(dupe_opts, dupe_col, to_avoid)

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
        query = Query(self.model)
        query.add_filter(filter_expr, can_reuse=can_reuse)
        query.bump_prefix()
        query.clear_ordering(True)
        query.set_start(prefix)
        # Adding extra check to make sure the selected field will not be null
        # since we are adding a IN <subquery> clause. This prevents the
        # database from tripping over IN (...,NULL,...) selects and returning
        # nothing
        alias, col = query.select[0]
        query.where.add((Constraint(alias, col, None), 'isnull', False), AND)

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
            names = opts.get_all_field_names() + self.extra.keys() + self.aggregate_select.keys()
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
            self.extra.update(select_pairs)
        if where or params:
            self.where.add(ExtraWhere(where, params), AND)
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

    def set_aggregate_mask(self, names):
        "Set the mask of aggregates that will actually be returned by the SELECT"
        if names is None:
            self.aggregate_select_mask = None
        else:
            self.aggregate_select_mask = set(names)
        self._aggregate_select_cache = None

    def set_extra_mask(self, names):
        """
        Set the mask of extra select items that will be returned by SELECT,
        we don't actually remove them from the Query since they might be used
        later
        """
        if names is None:
            self.extra_select_mask = None
        else:
            self.extra_select_mask = set(names)
        self._extra_select_cache = None

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

    def _extra_select(self):
        if self._extra_select_cache is not None:
            return self._extra_select_cache
        elif self.extra_select_mask is not None:
            self._extra_select_cache = SortedDict([
                (k,v) for k,v in self.extra.items()
                if k in self.extra_select_mask
            ])
            return self._extra_select_cache
        else:
            return self.extra
    extra_select = property(_extra_select)

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

def get_proxied_model(opts):
    int_opts = opts
    proxied_model = None
    while int_opts.proxy:
        proxied_model = int_opts.proxy_for_model
        int_opts = proxied_model._meta
    return proxied_model
