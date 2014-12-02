"""
Create SQL statements for QuerySets.

The code in here encapsulates all of the SQL construction so that QuerySets
themselves do not have to (and could be backed by things other than SQL
databases). The abstraction barrier only works one way: this module has to know
all about the internals of models in order to get the information it needs.
"""

from collections import Mapping, OrderedDict
import copy
import warnings

from django.core.exceptions import FieldError
from django.db import connections, DEFAULT_DB_ALIAS
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import Col, Ref
from django.db.models.fields import FieldDoesNotExist
from django.db.models.query_utils import Q, refs_aggregate
from django.db.models.related import PathInfo
from django.db.models.aggregates import Count
from django.db.models.sql.constants import (QUERY_TERMS, ORDER_DIR, SINGLE,
        ORDER_PATTERN, SelectInfo, INNER, LOUTER)
from django.db.models.sql.datastructures import (
    EmptyResultSet, Empty, MultiJoin, Join, BaseTable)
from django.db.models.sql.where import (WhereNode, Constraint, EverythingNode,
    ExtraWhere, AND, OR, EmptyWhere)
from django.utils import six
from django.utils.deprecation import RemovedInDjango19Warning, RemovedInDjango20Warning
from django.utils.encoding import force_text
from django.utils.tree import Node

__all__ = ['Query', 'RawQuery']


class RawQuery(object):
    """
    A single raw SQL query
    """

    def __init__(self, sql, using, params=None):
        self.params = params or ()
        self.sql = sql
        self.using = using
        self.cursor = None

        # Mirror some properties of a normal query so that
        # the compiler can be used to process results.
        self.low_mark, self.high_mark = 0, None  # Used for offset/limit
        self.extra_select = {}
        self.annotation_select = {}

    def clone(self, using):
        return RawQuery(self.sql, using, params=self.params)

    def get_columns(self):
        if self.cursor is None:
            self._execute_query()
        converter = connections[self.using].introspection.column_name_converter
        return [converter(column_meta[0])
                for column_meta in self.cursor.description]

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
        return "<RawQuery: %s>" % self

    def __str__(self):
        _type = dict if isinstance(self.params, Mapping) else tuple
        return self.sql % _type(self.params)

    def _execute_query(self):
        self.cursor = connections[self.using].cursor()
        self.cursor.execute(self.sql, self.params)


class Query(object):
    """
    A single SQL query.
    """

    alias_prefix = 'T'
    subq_aliases = frozenset([alias_prefix])
    query_terms = QUERY_TERMS

    compiler = 'SQLCompiler'

    def __init__(self, model, where=WhereNode):
        self.model = model
        self.alias_refcount = {}
        # alias_map is the most important data structure regarding joins.
        # It's used for recording which joins exist in the query and what
        # types they are. The key is the alias of the joined table (possibly
        # the table name) and the value is a Join-like object (see
        # sql.datastructures.Join for more information).
        self.alias_map = {}
        # Sometimes the query contains references to aliases in outer queries (as
        # a result of split_exclude). Correct alias quoting needs to know these
        # aliases too.
        self.external_aliases = set()
        self.table_map = {}     # Maps table names to list of aliases.
        self.default_cols = True
        self.default_ordering = True
        self.standard_ordering = True
        self.used_aliases = set()
        self.filter_is_sticky = False
        self.included_inherited_models = {}

        # SQL-related attributes
        # Select and related select clauses as SelectInfo instances.
        # The select is used for cases where we want to set up the select
        # clause to contain other than default fields (values(), annotate(),
        # subqueries...)
        self.select = []
        # The related_select_cols is used for columns needed for
        # select_related - this is populated in the compile stage.
        self.related_select_cols = []
        self.tables = []    # Aliases in the order they are created.
        self.where = where()
        self.where_class = where
        self.group_by = None
        self.having = where()
        self.order_by = []
        self.low_mark, self.high_mark = 0, None  # Used for offset/limit
        self.distinct = False
        self.distinct_fields = []
        self.select_for_update = False
        self.select_for_update_nowait = False
        self.select_related = False

        # SQL annotation-related attributes
        # The _annotations will be an OrderedDict when used. Due to the cost
        # of creating OrderedDict this attribute is created lazily (in
        # self.annotations property).
        self._annotations = None  # Maps alias -> Annotation Expression
        self.annotation_select_mask = None
        self._annotation_select_cache = None

        # Arbitrary maximum limit for select_related. Prevents infinite
        # recursion. Can be changed by the depth parameter to select_related().
        self.max_depth = 5

        # These are for extensions. The contents are more or less appended
        # verbatim to the appropriate clause.
        # The _extra attribute is an OrderedDict, lazily created similarly to
        # .annotations
        self._extra = None  # Maps col_alias -> (col_sql, params).
        self.extra_select_mask = None
        self._extra_select_cache = None

        self.extra_tables = ()
        self.extra_order_by = ()

        # A tuple that is a set of model field names and either True, if these
        # are the fields to defer, or False if these are the only fields to
        # load.
        self.deferred_loading = (set(), True)

    @property
    def extra(self):
        if self._extra is None:
            self._extra = OrderedDict()
        return self._extra

    @property
    def annotations(self):
        if self._annotations is None:
            self._annotations = OrderedDict()
        return self._annotations

    @property
    def aggregates(self):
        warnings.warn(
            "The aggregates property is deprecated. Use annotations instead.",
            RemovedInDjango20Warning, stacklevel=2)
        return self.annotations

    def __str__(self):
        """
        Returns the query as a string of SQL with the parameter values
        substituted in (use sql_with_params() to see the unsubstituted string).

        Parameter values won't necessarily be quoted correctly, since that is
        done by the database interface at execution time.
        """
        sql, params = self.sql_with_params()
        return sql % params

    def sql_with_params(self):
        """
        Returns the query as an SQL string and the parameters that will be
        substituted into the query.
        """
        return self.get_compiler(DEFAULT_DB_ALIAS).as_sql()

    def __deepcopy__(self, memo):
        result = self.clone(memo=memo)
        memo[id(self)] = result
        return result

    def _prepare(self):
        return self

    def get_compiler(self, using=None, connection=None):
        if using is None and connection is None:
            raise ValueError("Need either using or connection")
        if using:
            connection = connections[using]

        # Check that the compiler will be able to execute the query
        for alias, annotation in self.annotation_select.items():
            connection.ops.check_aggregate_support(annotation)

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
        obj.external_aliases = self.external_aliases.copy()
        obj.table_map = self.table_map.copy()
        obj.default_cols = self.default_cols
        obj.default_ordering = self.default_ordering
        obj.standard_ordering = self.standard_ordering
        obj.included_inherited_models = self.included_inherited_models.copy()
        obj.select = self.select[:]
        obj.related_select_cols = []
        obj.tables = self.tables[:]
        obj.where = self.where.clone()
        obj.where_class = self.where_class
        if self.group_by is None:
            obj.group_by = None
        else:
            obj.group_by = self.group_by[:]
        obj.having = self.having.clone()
        obj.order_by = self.order_by[:]
        obj.low_mark, obj.high_mark = self.low_mark, self.high_mark
        obj.distinct = self.distinct
        obj.distinct_fields = self.distinct_fields[:]
        obj.select_for_update = self.select_for_update
        obj.select_for_update_nowait = self.select_for_update_nowait
        obj.select_related = self.select_related
        obj.related_select_cols = []
        obj._annotations = self._annotations.copy() if self._annotations is not None else None
        if self.annotation_select_mask is None:
            obj.annotation_select_mask = None
        else:
            obj.annotation_select_mask = self.annotation_select_mask.copy()
        # _annotation_select_cache cannot be copied, as doing so breaks the
        # (necessary) state in which both annotations and
        # _annotation_select_cache point to the same underlying objects.
        # It will get re-populated in the cloned queryset the next time it's
        # used.
        obj._annotation_select_cache = None
        obj.max_depth = self.max_depth
        obj._extra = self._extra.copy() if self._extra is not None else None
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
        obj.deferred_loading = copy.copy(self.deferred_loading[0]), self.deferred_loading[1]
        if self.filter_is_sticky and self.used_aliases:
            obj.used_aliases = self.used_aliases.copy()
        else:
            obj.used_aliases = set()
        obj.filter_is_sticky = False
        if 'alias_prefix' in self.__dict__:
            obj.alias_prefix = self.alias_prefix
        if 'subq_aliases' in self.__dict__:
            obj.subq_aliases = self.subq_aliases.copy()

        obj.__dict__.update(kwargs)
        if hasattr(obj, '_setup_query'):
            obj._setup_query()
        return obj

    def relabeled_clone(self, change_map):
        clone = self.clone()
        clone.change_aliases(change_map)
        return clone

    def rewrite_cols(self, annotation, col_cnt):
        # We must make sure the inner query has the referred columns in it.
        # If we are aggregating over an annotation, then Django uses Ref()
        # instances to note this. However, if we are annotating over a column
        # of a related model, then it might be that column isn't part of the
        # SELECT clause of the inner query, and we must manually make sure
        # the column is selected. An example case is:
        #    .aggregate(Sum('author__awards'))
        # Resolving this expression results in a join to author, but there
        # is no guarantee the awards column of author is in the select clause
        # of the query. Thus we must manually add the column to the inner
        # query.
        orig_exprs = annotation.get_source_expressions()
        new_exprs = []
        for expr in orig_exprs:
            if isinstance(expr, Ref):
                # Its already a Ref to subquery (see resolve_ref() for
                # details)
                new_exprs.append(expr)
            elif isinstance(expr, Col):
                # Reference to column. Make sure the referenced column
                # is selected.
                col_cnt += 1
                col_alias = '__col%d' % col_cnt
                self.annotation_select[col_alias] = expr
                self.append_annotation_mask([col_alias])
                new_exprs.append(Ref(col_alias, expr))
            else:
                # Some other expression not referencing database values
                # directly. Its subexpression might contain Cols.
                new_expr, col_cnt = self.rewrite_cols(expr, col_cnt)
                new_exprs.append(new_expr)
        annotation.set_source_expressions(new_exprs)
        return annotation, col_cnt

    def get_aggregation(self, using, added_aggregate_names):
        """
        Returns the dictionary with the values of the existing aggregations.
        """
        if not self.annotation_select:
            return {}
        has_limit = self.low_mark != 0 or self.high_mark is not None
        has_existing_annotations = any(
            annotation for alias, annotation
            in self.annotations.items()
            if alias not in added_aggregate_names
        )
        # Decide if we need to use a subquery.
        #
        # Existing annotations would cause incorrect results as get_aggregation()
        # must produce just one result and thus must not use GROUP BY. But we
        # aren't smart enough to remove the existing annotations from the
        # query, so those would force us to use GROUP BY.
        #
        # If the query has limit or distinct, then those operations must be
        # done in a subquery so that we are aggregating on the limit and/or
        # distinct results instead of applying the distinct and limit after the
        # aggregation.
        if (self.group_by or has_limit or has_existing_annotations or self.distinct):
            from django.db.models.sql.subqueries import AggregateQuery
            outer_query = AggregateQuery(self.model)
            inner_query = self.clone()
            if not has_limit and not self.distinct_fields:
                inner_query.clear_ordering(True)
            inner_query.select_for_update = False
            inner_query.select_related = False
            inner_query.related_select_cols = []

            relabels = dict((t, 'subquery') for t in inner_query.tables)
            relabels[None] = 'subquery'
            # Remove any aggregates marked for reduction from the subquery
            # and move them to the outer AggregateQuery.
            col_cnt = 0
            for alias, expression in inner_query.annotation_select.items():
                if expression.is_summary:
                    expression, col_cnt = inner_query.rewrite_cols(expression, col_cnt)
                    outer_query.annotations[alias] = expression.relabeled_clone(relabels)
                    del inner_query.annotation_select[alias]
            try:
                outer_query.add_subquery(inner_query, using)
            except EmptyResultSet:
                return dict(
                    (alias, None)
                    for alias in outer_query.annotation_select
                )
        else:
            outer_query = self
            self.select = []
            self.default_cols = False
            self._extra = {}
            self.remove_inherited_models()

        outer_query.clear_ordering(True)
        outer_query.clear_limits()
        outer_query.select_for_update = False
        outer_query.select_related = False
        outer_query.related_select_cols = []
        compiler = outer_query.get_compiler(using)
        result = compiler.execute_sql(SINGLE)
        if result is None:
            result = [None for q in outer_query.annotation_select.items()]

        fields = [annotation.output_field
                  for alias, annotation in outer_query.annotation_select.items()]
        converters = compiler.get_converters(fields)
        for position, (alias, annotation) in enumerate(outer_query.annotation_select.items()):
            if position in converters:
                converters[position][1].insert(0, annotation.convert_value)
            else:
                converters[position] = ([], [annotation.convert_value], annotation.output_field)
        result = compiler.apply_converters(result, converters)

        return dict(
            (alias, val)
            for (alias, annotation), val
            in zip(outer_query.annotation_select.items(), result)
        )

    def get_count(self, using):
        """
        Performs a COUNT() query using the current filter constraints.
        """
        obj = self.clone()
        obj.add_annotation(Count('*'), alias='__count', is_summary=True)
        number = obj.get_aggregation(using, ['__count'])['__count']
        if number is None:
            number = 0
        return number

    def has_filters(self):
        return self.where or self.having

    def has_results(self, using):
        q = self.clone()
        if not q.distinct:
            q.clear_select_clause()
        q.clear_ordering(True)
        q.set_limits(high=1)
        compiler = q.get_compiler(using=using)
        return compiler.has_results()

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
        assert self.distinct_fields == rhs.distinct_fields, \
            "Cannot combine queries with different distinct fields."

        self.remove_inherited_models()
        # Work out how to relabel the rhs aliases, if necessary.
        change_map = {}
        conjunction = (connector == AND)

        # Determine which existing joins can be reused. When combining the
        # query with AND we must recreate all joins for m2m filters. When
        # combining with OR we can reuse joins. The reason is that in AND
        # case a single row can't fulfill a condition like:
        #     revrel__col=1 & revrel__col=2
        # But, there might be two different related rows matching this
        # condition. In OR case a single True is enough, so single row is
        # enough, too.
        #
        # Note that we will be creating duplicate joins for non-m2m joins in
        # the AND case. The results will be correct but this creates too many
        # joins. This is something that could be fixed later on.
        reuse = set() if conjunction else set(self.tables)
        # Base table must be present in the query - this is the same
        # table on both sides.
        self.get_initial_alias()
        joinpromoter = JoinPromoter(connector, 2, False)
        joinpromoter.add_votes(
            j for j in self.alias_map if self.alias_map[j].join_type == INNER)
        rhs_votes = set()
        # Now, add the joins from rhs query into the new query (skipping base
        # table).
        for alias in rhs.tables[1:]:
            join = rhs.alias_map[alias]
            # If the left side of the join was already relabeled, use the
            # updated alias.
            join = join.relabeled_clone(change_map)
            new_alias = self.join(join, reuse=reuse)
            if join.join_type == INNER:
                rhs_votes.add(new_alias)
            # We can't reuse the same join again in the query. If we have two
            # distinct joins for the same connection in rhs query, then the
            # combined query must have two joins, too.
            reuse.discard(new_alias)
            change_map[alias] = new_alias
            if not rhs.alias_refcount[alias]:
                # The alias was unused in the rhs query. Unref it so that it
                # will be unused in the new query, too. We have to add and
                # unref the alias so that join promotion has information of
                # the join type for the unused alias.
                self.unref_alias(new_alias)
        joinpromoter.add_votes(rhs_votes)
        joinpromoter.update_join_types(self)

        # Now relabel a copy of the rhs where-clause and add it to the current
        # one.
        if rhs.where:
            w = rhs.where.clone()
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
        for col, field in rhs.select:
            if isinstance(col, (list, tuple)):
                new_col = change_map.get(col[0], col[0]), col[1]
                self.select.append(SelectInfo(new_col, field))
            else:
                new_col = col.relabeled_clone(change_map)
                self.select.append(SelectInfo(new_col, field))

        if connector == OR:
            # It would be nice to be able to handle this, but the queries don't
            # really make sense (or return consistent value sets). Not worth
            # the extra complexity when you can write a real query instead.
            if self._extra and rhs._extra:
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
        self.order_by = rhs.order_by[:] if rhs.order_by else self.order_by
        self.extra_order_by = rhs.extra_order_by or self.extra_order_by

    def deferred_to_data(self, target, callback):
        """
        Converts the self.deferred_loading data structure to an alternate data
        structure, describing the field that *will* be loaded. This is used to
        compute the columns to select from the database and also by the
        QuerySet class to work out which fields are being initialized on each
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
        orig_opts = self.get_meta()
        seen = {}
        must_include = {orig_opts.concrete_model: {orig_opts.pk}}
        for field_name in field_names:
            parts = field_name.split(LOOKUP_SEP)
            cur_model = self.model._meta.concrete_model
            opts = orig_opts
            for name in parts[:-1]:
                old_model = cur_model
                source = opts.get_field(name)
                if is_reverse_o2o(source):
                    cur_model = source.model
                else:
                    cur_model = source.rel.to
                opts = cur_model._meta
                # Even if we're "just passing through" this model, we must add
                # both the current model's pk and the related reference field
                # (if it's not a reverse relation) to the things we select.
                if not is_reverse_o2o(source):
                    must_include[old_model].add(source)
                add_to_dict(must_include, cur_model, opts.pk)
            field = opts.get_field(parts[-1])
            model = field.parent_model._meta.concrete_model
            if model == opts.model:
                model = cur_model
            if not is_reverse_o2o(field):
                add_to_dict(seen, model, field)

        if defer:
            # We need to load all fields for each model, except those that
            # appear in "seen" (for all models that appear in "seen"). The only
            # slight complexity here is handling fields that exist on parent
            # models.
            workset = {}
            for model, values in six.iteritems(seen):
                for field in model._meta.fields:
                    if field in values:
                        continue
                    m = field.parent_model._meta.concrete_model
                    add_to_dict(workset, m, field)
            for model, values in six.iteritems(must_include):
                # If we haven't included a model in workset, we don't add the
                # corresponding must_include fields for that model, since an
                # empty set means "include all fields". That's why there's no
                # "else" branch here.
                if model in workset:
                    workset[model].update(values)
            for model, values in six.iteritems(workset):
                callback(target, model, values)
        else:
            for model, values in six.iteritems(must_include):
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
            for model, values in six.iteritems(seen):
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
        alias_list = self.table_map.get(table_name)
        if not create and alias_list:
            alias = alias_list[0]
            self.alias_refcount[alias] += 1
            return alias, False

        # Create a new alias for this table.
        if alias_list:
            alias = '%s%d' % (self.alias_prefix, len(self.alias_map) + 1)
            alias_list.append(alias)
        else:
            # The first occurrence of a table uses the table name directly.
            alias = table_name
            self.table_map[alias] = [alias]
        self.alias_refcount[alias] = 1
        self.tables.append(alias)
        return alias, True

    def ref_alias(self, alias):
        """ Increases the reference count for this alias. """
        self.alias_refcount[alias] += 1

    def unref_alias(self, alias, amount=1):
        """ Decreases the reference count for this alias. """
        self.alias_refcount[alias] -= amount

    def promote_joins(self, aliases):
        """
        Promotes recursively the join type of given aliases and its children to
        an outer join. If 'unconditional' is False, the join is only promoted if
        it is nullable or the parent join is an outer join.

        The children promotion is done to avoid join chains that contain a LOUTER
        b INNER c. So, if we have currently a INNER b INNER c and a->b is promoted,
        then we must also promote b->c automatically, or otherwise the promotion
        of a->b doesn't actually change anything in the query results.
        """
        aliases = list(aliases)
        while aliases:
            alias = aliases.pop(0)
            if self.alias_map[alias].join_type is None:
                # This is the base table (first FROM entry) - this table
                # isn't really joined at all in the query, so we should not
                # alter its join type.
                continue
            # Only the first alias (skipped above) should have None join_type
            assert self.alias_map[alias].join_type is not None
            parent_alias = self.alias_map[alias].parent_alias
            parent_louter = (
                parent_alias
                and self.alias_map[parent_alias].join_type == LOUTER)
            already_louter = self.alias_map[alias].join_type == LOUTER
            if ((self.alias_map[alias].nullable or parent_louter) and
                    not already_louter):
                self.alias_map[alias] = self.alias_map[alias].promote()
                # Join type of 'alias' changed, so re-examine all aliases that
                # refer to this one.
                aliases.extend(
                    join for join in self.alias_map.keys()
                    if (self.alias_map[join].parent_alias == alias
                        and join not in aliases))

    def demote_joins(self, aliases):
        """
        Change join type from LOUTER to INNER for all joins in aliases.

        Similarly to promote_joins(), this method must ensure no join chains
        containing first an outer, then an inner join are generated. If we
        are demoting b->c join in chain a LOUTER b LOUTER c then we must
        demote a->b automatically, or otherwise the demotion of b->c doesn't
        actually change anything in the query results. .
        """
        aliases = list(aliases)
        while aliases:
            alias = aliases.pop(0)
            if self.alias_map[alias].join_type == LOUTER:
                self.alias_map[alias] = self.alias_map[alias].demote()
                parent_alias = self.alias_map[alias].parent_alias
                if self.alias_map[parent_alias].join_type == INNER:
                    aliases.append(parent_alias)

    def reset_refcounts(self, to_counts):
        """
        This method will reset reference counts for aliases so that they match
        the value passed in :param to_counts:.
        """
        for alias, cur_refcount in self.alias_refcount.copy().items():
            unref_amount = cur_refcount - to_counts.get(alias, 0)
            self.unref_alias(alias, unref_amount)

    def change_aliases(self, change_map):
        """
        Changes the aliases in change_map (which maps old-alias -> new-alias),
        relabelling any references to them in select columns and the where
        clause.
        """
        assert set(change_map.keys()).intersection(set(change_map.values())) == set()

        def relabel_column(col):
            if isinstance(col, (list, tuple)):
                old_alias = col[0]
                return (change_map.get(old_alias, old_alias), col[1])
            else:
                return col.relabeled_clone(change_map)
        # 1. Update references in "select" (normal columns plus aliases),
        # "group by", "where" and "having".
        self.where.relabel_aliases(change_map)
        self.having.relabel_aliases(change_map)
        if self.group_by:
            self.group_by = [relabel_column(col) for col in self.group_by]
        self.select = [SelectInfo(relabel_column(s.col), s.field)
                       for s in self.select]
        if self._annotations:
            self._annotations = OrderedDict(
                (key, relabel_column(col)) for key, col in self._annotations.items())

        # 2. Rename the alias in the internal table/alias datastructures.
        for old_alias, new_alias in six.iteritems(change_map):
            if old_alias not in self.alias_map:
                continue
            alias_data = self.alias_map[old_alias].relabeled_clone(change_map)
            self.alias_map[new_alias] = alias_data
            self.alias_refcount[new_alias] = self.alias_refcount[old_alias]
            del self.alias_refcount[old_alias]
            del self.alias_map[old_alias]

            table_aliases = self.table_map[alias_data.table_name]
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
        self.external_aliases = {change_map.get(alias, alias)
                                 for alias in self.external_aliases}

    def bump_prefix(self, outer_query):
        """
        Changes the alias prefix to the next letter in the alphabet in a way
        that the outer query's aliases and this query's aliases will not
        conflict. Even tables that previously had no alias will get an alias
        after this call.
        """
        if self.alias_prefix != outer_query.alias_prefix:
            # No clashes between self and outer query should be possible.
            return
        self.alias_prefix = chr(ord(self.alias_prefix) + 1)
        while self.alias_prefix in self.subq_aliases:
            self.alias_prefix = chr(ord(self.alias_prefix) + 1)
            assert self.alias_prefix < 'Z'
        self.subq_aliases = self.subq_aliases.union([self.alias_prefix])
        outer_query.subq_aliases = outer_query.subq_aliases.union(self.subq_aliases)
        change_map = OrderedDict()
        for pos, alias in enumerate(self.tables):
            new_alias = '%s%d' % (self.alias_prefix, pos)
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
            alias = self.join(BaseTable(self.get_meta().db_table, None))
        return alias

    def count_active_tables(self):
        """
        Returns the number of tables in this query with a non-zero reference
        count. Note that after execution, the reference counts are zeroed, so
        tables added in compiler will not be seen by this method.
        """
        return len([1 for count in self.alias_refcount.values() if count])

    def join(self, join, reuse=None):
        """
        Returns an alias for the join in 'connection', either reusing an
        existing alias for that join or creating a new one. 'connection' is a
        tuple (lhs, table, join_cols) where 'lhs' is either an existing
        table alias or a table name. 'join_cols' is a tuple of tuples containing
        columns to join on ((l_id1, r_id1), (l_id2, r_id2)). The join corresponds
        to the SQL equivalent of::

            lhs.l_id1 = table.r_id1 AND lhs.l_id2 = table.r_id2

        The 'reuse' parameter can be either None which means all joins
        (matching the connection) are reusable, or it can be a set containing
        the aliases that can be reused.

        A join is always created as LOUTER if the lhs alias is LOUTER to make
        sure we do not generate chains like t1 LOUTER t2 INNER t3. All new
        joins are created as LOUTER if nullable is True.

        If 'nullable' is True, the join can potentially involve NULL values and
        is a candidate for promotion (to "left outer") when combining querysets.

        The 'join_field' is the field we are joining along (if any).
        """
        reuse = [a for a, j in self.alias_map.items()
                 if (reuse is None or a in reuse) and j == join]
        if reuse:
            self.ref_alias(reuse[0])
            return reuse[0]

        # No reuse is possible, so we need a new alias.
        alias, _ = self.table_alias(join.table_name, create=True)
        if join.join_type:
            if self.alias_map[join.parent_alias].join_type == LOUTER or join.nullable:
                join_type = LOUTER
            else:
                join_type = INNER
            join.join_type = join_type
        join.table_alias = alias
        self.alias_map[alias] = join
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
        opts = self.get_meta()
        root_alias = self.tables[0]
        seen = {None: root_alias}

        for field in opts.fields:
            model = field.parent_model._meta.concrete_model
            if model is not opts.model and model not in seen:
                self.join_parent_model(opts, model, root_alias, seen)
        self.included_inherited_models = seen

    def join_parent_model(self, opts, model, alias, seen):
        """
        Makes sure the given 'model' is joined in the query. If 'model' isn't
        a parent of 'opts' or if it is None this method is a no-op.

        The 'alias' is the root alias for starting the join, 'seen' is a dict
        of model -> alias of existing joins. It must also contain a mapping
        of None -> some alias. This will be returned in the no-op case.
        """
        if model in seen:
            return seen[model]
        chain = opts.get_base_chain(model)
        if chain is None:
            return alias
        curr_opts = opts
        for int_model in chain:
            if int_model in seen:
                return seen[int_model]
            # Proxy model have elements in base chain
            # with no parents, assign the new options
            # object and skip to the next base in that
            # case
            if not curr_opts.parents[int_model]:
                curr_opts = int_model._meta
                continue
            link_field = curr_opts.get_ancestor_link(int_model)
            _, _, _, joins, _ = self.setup_joins(
                [link_field.name], curr_opts, alias)
            curr_opts = int_model._meta
            alias = seen[int_model] = joins[-1]
        return alias or seen[None]

    def remove_inherited_models(self):
        """
        Undoes the effects of setup_inherited_models(). Should be called
        whenever select columns (self.select) are set explicitly.
        """
        for key, alias in self.included_inherited_models.items():
            if key:
                self.unref_alias(alias)
        self.included_inherited_models = {}

    def add_aggregate(self, aggregate, model, alias, is_summary):
        warnings.warn(
            "add_aggregate() is deprecated. Use add_annotation() instead.",
            RemovedInDjango20Warning, stacklevel=2)
        self.add_annotation(aggregate, alias, is_summary)

    def add_annotation(self, annotation, alias, is_summary):
        """
        Adds a single annotation expression to the Query
        """
        annotation = annotation.resolve_expression(self, allow_joins=True, reuse=None,
                                                   summarize=is_summary)
        self.append_annotation_mask([alias])
        self.annotations[alias] = annotation

    def prepare_lookup_value(self, value, lookups, can_reuse):
        # Default lookup if none given is exact.
        if len(lookups) == 0:
            lookups = ['exact']
        # Interpret '__exact=None' as the sql 'is NULL'; otherwise, reject all
        # uses of None as a query value.
        if value is None:
            if lookups[-1] not in ('exact', 'iexact'):
                raise ValueError("Cannot use None as a query value")
            lookups[-1] = 'isnull'
            value = True
        elif callable(value):
            warnings.warn(
                "Passing callable arguments to queryset is deprecated.",
                RemovedInDjango19Warning, stacklevel=2)
            value = value()
        elif hasattr(value, 'resolve_expression'):
            value = value.resolve_expression(self, reuse=can_reuse)
        # Subqueries need to use a different set of aliases than the
        # outer query. Call bump_prefix to change aliases of the inner
        # query (the value).
        if hasattr(value, 'query') and hasattr(value.query, 'bump_prefix'):
            value = value._clone()
            value.query.bump_prefix(self)
        if hasattr(value, 'bump_prefix'):
            value = value.clone()
            value.bump_prefix(self)
        # For Oracle '' is equivalent to null. The check needs to be done
        # at this stage because join promotion can't be done at compiler
        # stage. Using DEFAULT_DB_ALIAS isn't nice, but it is the best we
        # can do here. Similar thing is done in is_nullable(), too.
        if (connections[DEFAULT_DB_ALIAS].features.interprets_empty_strings_as_nulls and
                lookups[-1] == 'exact' and value == ''):
            value = True
            lookups[-1] = 'isnull'
        return value, lookups

    def solve_lookup_type(self, lookup):
        """
        Solve the lookup type from the lookup (eg: 'foobar__id__icontains')
        """
        lookup_splitted = lookup.split(LOOKUP_SEP)
        if self._annotations:
            aggregate, aggregate_lookups = refs_aggregate(lookup_splitted, self.annotations)
            if aggregate:
                return aggregate_lookups, (), aggregate
        _, field, _, lookup_parts = self.names_to_path(lookup_splitted, self.get_meta())
        field_parts = lookup_splitted[0:len(lookup_splitted) - len(lookup_parts)]
        if len(lookup_parts) == 0:
            lookup_parts = ['exact']
        elif len(lookup_parts) > 1:
            if not field_parts:
                raise FieldError(
                    'Invalid lookup "%s" for model %s".' %
                    (lookup, self.get_meta().model.__name__))
        return lookup_parts, field_parts, False

    def check_query_object_type(self, value, opts):
        """
        Checks whether the object passed while querying is of the correct type.
        If not, it raises a ValueError specifying the wrong object.
        """
        if hasattr(value, '_meta'):
            if not (value._meta.concrete_model == opts.concrete_model
                    or opts.concrete_model in value._meta.get_parent_list()
                    or value._meta.concrete_model in opts.get_parent_list()):
                raise ValueError(
                    'Cannot query "%s": Must be "%s" instance.' %
                    (value, opts.object_name))

    def check_related_objects(self, field, value, opts):
        """
        Checks the type of object passed to query relations.
        """
        if field.rel:
            # QuerySets implement is_compatible_query_object_type() to
            # determine compatibility with the given field.
            if hasattr(value, 'is_compatible_query_object_type'):
                if not value.is_compatible_query_object_type(opts):
                    raise ValueError(
                        'Cannot use QuerySet for "%s": Use a QuerySet for "%s".' %
                        (value.model._meta.model_name, opts.object_name)
                    )
            elif hasattr(value, '_meta'):
                self.check_query_object_type(value, opts)
            elif hasattr(value, '__iter__'):
                for v in value:
                    self.check_query_object_type(v, opts)

    def build_lookup(self, lookups, lhs, rhs):
        """
        Tries to extract transforms and lookup from given lhs.

        The lhs value is something that works like SQLExpression.
        The rhs value is what the lookup is going to compare against.
        The lookups is a list of names to extract using get_lookup()
        and get_transform().
        """
        lookups = lookups[:]
        while lookups:
            name = lookups[0]
            # If there is just one part left, try first get_lookup() so
            # that if the lhs supports both transform and lookup for the
            # name, then lookup will be picked.
            if len(lookups) == 1:
                final_lookup = lhs.get_lookup(name)
                if not final_lookup:
                    # We didn't find a lookup. We are going to interpret
                    # the name as transform, and do an Exact lookup against
                    # it.
                    lhs = self.try_transform(lhs, name, lookups)
                    final_lookup = lhs.get_lookup('exact')
                return final_lookup(lhs, rhs)
            lhs = self.try_transform(lhs, name, lookups)
            lookups = lookups[1:]

    def try_transform(self, lhs, name, rest_of_lookups):
        """
        Helper method for build_lookup. Tries to fetch and initialize
        a transform for name parameter from lhs.
        """
        next = lhs.get_transform(name)
        if next:
            return next(lhs, rest_of_lookups)
        else:
            raise FieldError(
                "Unsupported lookup '%s' for %s or join on the field not "
                "permitted." %
                (name, lhs.output_field.__class__.__name__))

    def build_filter(self, filter_expr, branch_negated=False, current_negated=False,
                     can_reuse=None, connector=AND):
        """
        Builds a WhereNode for a single filter clause, but doesn't add it
        to this Query. Query.add_q() will then add this filter to the where
        or having Node.

        The 'branch_negated' tells us if the current branch contains any
        negations. This will be used to determine if subqueries are needed.

        The 'current_negated' is used to determine if the current filter is
        negated or not and this will be used to determine if IS NULL filtering
        is needed.

        The difference between current_netageted and branch_negated is that
        branch_negated is set on first negation, but current_negated is
        flipped for each negation.

        Note that add_filter will not do any negating itself, that is done
        upper in the code by add_q().

        The 'can_reuse' is a set of reusable joins for multijoins.

        The method will create a filter clause that can be added to the current
        query. However, if the filter isn't added to the query then the caller
        is responsible for unreffing the joins used.
        """
        arg, value = filter_expr
        if not arg:
            raise FieldError("Cannot parse keyword query %r" % arg)
        lookups, parts, reffed_aggregate = self.solve_lookup_type(arg)

        # Work out the lookup type and remove it from the end of 'parts',
        # if necessary.
        value, lookups = self.prepare_lookup_value(value, lookups, can_reuse)
        used_joins = getattr(value, '_used_joins', [])

        clause = self.where_class()
        if reffed_aggregate:
            condition = self.build_lookup(lookups, reffed_aggregate, value)
            if not condition:
                # Backwards compat for custom lookups
                assert len(lookups) == 1
                condition = (reffed_aggregate, lookups[0], value)
            clause.add(condition, AND)
            return clause, []

        opts = self.get_meta()
        alias = self.get_initial_alias()
        allow_many = not branch_negated

        try:
            field, sources, opts, join_list, path = self.setup_joins(
                parts, opts, alias, can_reuse=can_reuse, allow_many=allow_many)

            self.check_related_objects(field, value, opts)

            # split_exclude() needs to know which joins were generated for the
            # lookup parts
            self._lookup_joins = join_list
        except MultiJoin as e:
            return self.split_exclude(filter_expr, LOOKUP_SEP.join(parts[:e.level]),
                                      can_reuse, e.names_with_path)

        if can_reuse is not None:
            can_reuse.update(join_list)
        used_joins = set(used_joins).union(set(join_list))

        # Process the join list to see if we can remove any non-needed joins from
        # the far end (fewer tables in a query is better).
        targets, alias, join_list = self.trim_joins(sources, join_list, path)

        if hasattr(field, 'get_lookup_constraint'):
            # For now foreign keys get special treatment. This should be
            # refactored when composite fields lands.
            condition = field.get_lookup_constraint(self.where_class, alias, targets, sources,
                                                    lookups, value)
            lookup_type = lookups[-1]
        else:
            assert(len(targets) == 1)
            if hasattr(targets[0], 'as_sql'):
                # handle Expressions as annotations
                col = targets[0]
            else:
                col = Col(alias, targets[0], field)
            condition = self.build_lookup(lookups, col, value)
            if not condition:
                # Backwards compat for custom lookups
                if lookups[0] not in self.query_terms:
                    raise FieldError(
                        "Join on field '%s' not permitted. Did you "
                        "misspell '%s' for the lookup type?" %
                        (col.output_field.name, lookups[0]))
                if len(lookups) > 1:
                    raise FieldError("Nested lookup '%s' not supported." %
                                     LOOKUP_SEP.join(lookups))
                condition = (Constraint(alias, targets[0].column, field), lookups[0], value)
                lookup_type = lookups[-1]
            else:
                lookup_type = condition.lookup_name

        clause.add(condition, AND)

        require_outer = lookup_type == 'isnull' and value is True and not current_negated
        if current_negated and (lookup_type != 'isnull' or value is False):
            require_outer = True
            if (lookup_type != 'isnull' and (
                    self.is_nullable(targets[0]) or
                    self.alias_map[join_list[-1]].join_type == LOUTER)):
                # The condition added here will be SQL like this:
                # NOT (col IS NOT NULL), where the first NOT is added in
                # upper layers of code. The reason for addition is that if col
                # is null, then col != someval will result in SQL "unknown"
                # which isn't the same as in Python. The Python None handling
                # is wanted, and it can be gotten by
                # (col IS NULL OR col != someval)
                #   <=>
                # NOT (col IS NOT NULL AND col = someval).
                lookup_class = targets[0].get_lookup('isnull')
                clause.add(lookup_class(Col(alias, targets[0], sources[0]), False), AND)
        return clause, used_joins if not require_outer else ()

    def add_filter(self, filter_clause):
        self.add_q(Q(**{filter_clause[0]: filter_clause[1]}))

    def need_having(self, obj):
        """
        Returns whether or not all elements of this q_object need to be put
        together in the HAVING clause.
        """
        if not self._annotations:
            return False
        if not isinstance(obj, Node):
            return (refs_aggregate(obj[0].split(LOOKUP_SEP), self.annotations)[0]
                    or (hasattr(obj[1], 'refs_aggregate')
                        and obj[1].refs_aggregate(self.annotations)[0]))
        return any(self.need_having(c) for c in obj.children)

    def split_having_parts(self, q_object, negated=False):
        """
        Returns a list of q_objects which need to go into the having clause
        instead of the where clause. Removes the splitted out nodes from the
        given q_object. Note that the q_object is altered, so cloning it is
        needed.
        """
        having_parts = []
        for c in q_object.children[:]:
            # When constructing the having nodes we need to take care to
            # preserve the negation status from the upper parts of the tree
            if isinstance(c, Node):
                # For each negated child, flip the in_negated flag.
                in_negated = c.negated ^ negated
                if c.connector == OR and self.need_having(c):
                    # A subtree starting from OR clause must go into having in
                    # whole if any part of that tree references an aggregate.
                    q_object.children.remove(c)
                    having_parts.append(c)
                    c.negated = in_negated
                else:
                    having_parts.extend(
                        self.split_having_parts(c, in_negated)[1])
            elif self.need_having(c):
                q_object.children.remove(c)
                new_q = self.where_class(children=[c], negated=negated)
                having_parts.append(new_q)
        return q_object, having_parts

    def add_q(self, q_object):
        """
        A preprocessor for the internal _add_q(). Responsible for
        splitting the given q_object into where and having parts and
        setting up some internal variables.
        """
        if not self.need_having(q_object):
            where_part, having_parts = q_object, []
        else:
            where_part, having_parts = self.split_having_parts(
                q_object.clone(), q_object.negated)
        # For join promotion this case is doing an AND for the added q_object
        # and existing conditions. So, any existing inner join forces the join
        # type to remain inner. Existing outer joins can however be demoted.
        # (Consider case where rel_a is LOUTER and rel_a__col=1 is added - if
        # rel_a doesn't produce any rows, then the whole condition must fail.
        # So, demotion is OK.
        existing_inner = set(
            (a for a in self.alias_map if self.alias_map[a].join_type == INNER))
        clause, require_inner = self._add_q(where_part, self.used_aliases)
        self.where.add(clause, AND)
        for hp in having_parts:
            clause, _ = self._add_q(hp, self.used_aliases)
            self.having.add(clause, AND)
        self.demote_joins(existing_inner)

    def _add_q(self, q_object, used_aliases, branch_negated=False,
               current_negated=False):
        """
        Adds a Q-object to the current filter.
        """
        connector = q_object.connector
        current_negated = current_negated ^ q_object.negated
        branch_negated = branch_negated or q_object.negated
        target_clause = self.where_class(connector=connector,
                                         negated=q_object.negated)
        joinpromoter = JoinPromoter(q_object.connector, len(q_object.children), current_negated)
        for child in q_object.children:
            if isinstance(child, Node):
                child_clause, needed_inner = self._add_q(
                    child, used_aliases, branch_negated,
                    current_negated)
                joinpromoter.add_votes(needed_inner)
            else:
                child_clause, needed_inner = self.build_filter(
                    child, can_reuse=used_aliases, branch_negated=branch_negated,
                    current_negated=current_negated, connector=connector)
                joinpromoter.add_votes(needed_inner)
            target_clause.add(child_clause, connector)
        needed_inner = joinpromoter.update_join_types(self)
        return target_clause, needed_inner

    def names_to_path(self, names, opts, allow_many=True, fail_on_missing=False):
        """
        Walks the list of names and turns them into PathInfo tuples. Note that
        a single name in 'names' can generate multiple PathInfos (m2m for
        example).

        'names' is the path of names to travel, 'opts' is the model Options we
        start the name resolving from, 'allow_many' is as for setup_joins().
        If fail_on_missing is set to True, then a name that can't be resolved
        will generate a FieldError.

        Returns a list of PathInfo tuples. In addition returns the final field
        (the last used join field), and target (which is a field guaranteed to
        contain the same value as the final field). Finally, the method returns
        those names that weren't found (which are likely transforms and the
        final lookup).
        """
        path, names_with_path = [], []
        for pos, name in enumerate(names):
            cur_names_with_path = (name, [])
            if name == 'pk':
                name = opts.pk.name
            try:
                field = opts.get_field(name)

                # Fields like a GenericForeignKey cannot generate reverse relations
                # therefore they cannote be used for reverse querying.
                if hasattr(field, 'is_gfk'):
                    raise FieldError("Field %r is a GenericForeignKey. This field "
                                      "type does not generate a reverse relation "
                                      "by default and therefore cannot be used for "
                                      "reverse querying. Consider using a "
                                      "GenericRelation." % name)
                model = field.parent_model._meta.concrete_model
            except FieldDoesNotExist:
                # is it an annotation?
                if self._annotations and name in self._annotations:
                    field, model = self._annotations[name], None
                    if not field.contains_aggregate:
                        # Local non-relational field.
                        final_field = field
                        targets = (field,)
                        break
                # We didn't find the current field, so move position back
                # one step.
                pos -= 1
                if pos == -1 or fail_on_missing:
                    field_names = [f.name for f in opts.get_fields()]
                    available = sorted(field_names + list(self.aggregate_select))
                    raise FieldError("Cannot resolve keyword %r into field. "
                                     "Choices are: %s" % (name, ", ".join(available)))
                break
            # Check if we need any joins for concrete inheritance cases (the
            # field lives in parent, but we are currently in one of its
            # children)
            if model is not opts.model:
                # The field lives on a base class of the current model.
                # Skip the chain of proxy to the concrete proxied model
                proxied_model = opts.concrete_model

                for int_model in opts.get_base_chain(model):
                    if int_model is proxied_model:
                        opts = int_model._meta
                    else:
                        final_field = opts.parents[int_model]
                        targets = (final_field.rel.get_related_field(),)
                        opts = int_model._meta
                        path.append(PathInfo(final_field.model._meta, opts, targets, final_field, False, True))
                        cur_names_with_path[1].append(
                            PathInfo(final_field.model._meta, opts, targets, final_field, False, True)
                        )
            if hasattr(field, 'get_path_info'):
                pathinfos = field.get_path_info()
                if not allow_many:
                    for inner_pos, p in enumerate(pathinfos):
                        if p.m2m:
                            cur_names_with_path[1].extend(pathinfos[0:inner_pos + 1])
                            names_with_path.append(cur_names_with_path)
                            raise MultiJoin(pos + 1, names_with_path)
                last = pathinfos[-1]
                path.extend(pathinfos)
                final_field = last.join_field
                opts = last.to_opts
                targets = last.target_fields
                cur_names_with_path[1].extend(pathinfos)
                names_with_path.append(cur_names_with_path)
            else:
                # Local non-relational field.
                final_field = field
                targets = (field,)
                if fail_on_missing and pos + 1 != len(names):
                    raise FieldError(
                        "Cannot resolve keyword %r into field. Join on '%s'"
                        " not permitted." % (names[pos + 1], name))
                break
        return path, final_field, targets, names[pos + 1:]

    def raise_field_error(self, opts, name):
        available = opts.get_all_field_names() + list(self.annotation_select)
        raise FieldError("Cannot resolve keyword %r into field. "
                         "Choices are: %s" % (name, ", ".join(available)))

    def setup_joins(self, names, opts, alias, can_reuse=None, allow_many=True):
        """
        Compute the necessary table joins for the passage through the fields
        given in 'names'. 'opts' is the Options class for the current model
        (which gives the table we are starting from), 'alias' is the alias for
        the table to start the joining from.

        The 'can_reuse' defines the reverse foreign key joins we can reuse. It
        can be None in which case all joins are reusable or a set of aliases
        that can be reused. Note that non-reverse foreign keys are always
        reusable when using setup_joins().

        If 'allow_many' is False, then any reverse foreign key seen will
        generate a MultiJoin exception.

        Returns the final field involved in the joins, the target field (used
        for any 'where' constraint), the final 'opts' value, the joins and the
        field path travelled to generate the joins.

        The target field is the field containing the concrete value. Final
        field can be something different, for example foreign key pointing to
        that value. Final field is needed for example in some value
        conversions (convert 'obj' in fk__id=obj to pk val using the foreign
        key field for example).
        """
        joins = [alias]
        # First, generate the path for the names
        path, final_field, targets, rest = self.names_to_path(
            names, opts, allow_many, fail_on_missing=True)

        # Then, add the path to the query's joins. Note that we can't trim
        # joins at this stage - we will need the information about join type
        # of the trimmed joins.
        for join in path:
            opts = join.to_opts
            if join.direct:
                nullable = self.is_nullable(join.join_field)
            else:
                nullable = True
            connection = Join(opts.db_table, alias, None, INNER, join.join_field, nullable)
            reuse = can_reuse if join.m2m else None
            alias = self.join(connection, reuse=reuse)
            joins.append(alias)
        if hasattr(final_field, 'field'):
            final_field = final_field.field
        return final_field, targets, opts, joins, path

    def trim_joins(self, targets, joins, path):
        """
        The 'target' parameter is the final field being joined to, 'joins'
        is the full list of join aliases. The 'path' contain the PathInfos
        used to create the joins.

        Returns the final target field and table alias and the new active
        joins.

        We will always trim any direct join if we have the target column
        available already in the previous table. Reverse joins can't be
        trimmed as we don't know if there is anything on the other side of
        the join.
        """
        joins = joins[:]
        for pos, info in enumerate(reversed(path)):
            if len(joins) == 1 or not info.direct:
                break
            join_targets = set(t.column for t in info.join_field.foreign_related_fields)
            cur_targets = set(t.column for t in targets)
            if not cur_targets.issubset(join_targets):
                break
            targets = tuple(r[0] for r in info.join_field.related_fields if r[1].column in cur_targets)
            self.unref_alias(joins.pop())
        return targets, joins[-1], joins

    def resolve_ref(self, name, allow_joins, reuse, summarize):
        if not allow_joins and LOOKUP_SEP in name:
            raise FieldError("Joined field references are not permitted in this query")
        if name in self.annotations:
            if summarize:
                # Summarize currently means we are doing an aggregate() query
                # which is executed as a wrapped subquery if any of the
                # aggregate() elements reference an existing annotation. In
                # that case we need to return a Ref to the subquery's annotation.
                return Ref(name, self.annotation_select[name])
            else:
                return self.annotation_select[name]
        else:
            field_list = name.split(LOOKUP_SEP)
            field, sources, opts, join_list, path = self.setup_joins(
                field_list, self.get_meta(),
                self.get_initial_alias(), reuse)
            targets, _, join_list = self.trim_joins(sources, join_list, path)
            if len(targets) > 1:
                raise FieldError("Referencing multicolumn fields with F() objects "
                                 "isn't supported")
            if reuse is not None:
                reuse.update(join_list)
            col = Col(join_list[-1], targets[0], sources[0])
            col._used_joins = join_list
            return col

    def split_exclude(self, filter_expr, prefix, can_reuse, names_with_path):
        """
        When doing an exclude against any kind of N-to-many relation, we need
        to use a subquery. This method constructs the nested query, given the
        original exclude filter (filter_expr) and the portion up to the first
        N-to-many relation field.

        As an example we could have original filter ~Q(child__name='foo').
        We would get here with filter_expr = child__name, prefix = child and
        can_reuse is a set of joins usable for filters in the original query.

        We will turn this into equivalent of:
            WHERE NOT (pk IN (SELECT parent_id FROM thetable
                              WHERE name = 'foo' AND parent_id IS NOT NULL))

        It might be worth it to consider using WHERE NOT EXISTS as that has
        saner null handling, and is easier for the backend's optimizer to
        handle.
        """
        # Generate the inner query.
        query = Query(self.model)
        query.add_filter(filter_expr)
        query.clear_ordering(True)
        # Try to have as simple as possible subquery -> trim leading joins from
        # the subquery.
        trimmed_prefix, contains_louter = query.trim_start(names_with_path)
        query.remove_inherited_models()

        # Add extra check to make sure the selected field will not be null
        # since we are adding an IN <subquery> clause. This prevents the
        # database from tripping over IN (...,NULL,...) selects and returning
        # nothing
        alias, col = query.select[0].col
        if self.is_nullable(query.select[0].field):
            lookup_class = query.select[0].field.get_lookup('isnull')
            lookup = lookup_class(Col(alias, query.select[0].field, query.select[0].field), False)
            query.where.add(lookup, AND)
        if alias in can_reuse:
            select_field = query.select[0].field
            pk = select_field.model._meta.pk
            # Need to add a restriction so that outer query's filters are in effect for
            # the subquery, too.
            query.bump_prefix(self)
            lookup_class = select_field.get_lookup('exact')
            lookup = lookup_class(Col(query.select[0].col[0], pk, pk),
                                  Col(alias, pk, pk))
            query.where.add(lookup, AND)
            query.external_aliases.add(alias)

        condition, needed_inner = self.build_filter(
            ('%s__in' % trimmed_prefix, query),
            current_negated=True, branch_negated=True, can_reuse=can_reuse)
        if contains_louter:
            or_null_condition, _ = self.build_filter(
                ('%s__isnull' % trimmed_prefix, True),
                current_negated=True, branch_negated=True, can_reuse=can_reuse)
            condition.add(or_null_condition, OR)
            # Note that the end result will be:
            # (outercol NOT IN innerq AND outercol IS NOT NULL) OR outercol IS NULL.
            # This might look crazy but due to how IN works, this seems to be
            # correct. If the IS NOT NULL check is removed then outercol NOT
            # IN will return UNKNOWN. If the IS NULL check is removed, then if
            # outercol IS NULL we will not match the row.
        return condition, needed_inner

    def set_empty(self):
        self.where = EmptyWhere()
        self.having = EmptyWhere()

    def is_empty(self):
        return isinstance(self.where, EmptyWhere) or isinstance(self.having, EmptyWhere)

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

    def clear_select_clause(self):
        """
        Removes all fields from SELECT clause.
        """
        self.select = []
        self.default_cols = False
        self.select_related = False
        self.set_extra_mask(())
        self.set_annotation_mask(())

    def clear_select_fields(self):
        """
        Clears the list of fields to select (but not extra_select columns).
        Some queryset types completely replace any existing list of select
        columns.
        """
        self.select = []

    def add_distinct_fields(self, *field_names):
        """
        Adds and resolves the given fields to the query's "distinct on" clause.
        """
        self.distinct_fields = field_names
        self.distinct = True

    def add_fields(self, field_names, allow_m2m=True):
        """
        Adds the given (model) fields to the select set. The field names are
        added in the order specified.
        """
        alias = self.get_initial_alias()
        opts = self.get_meta()

        try:
            for name in field_names:
                # Join promotion note - we must not remove any rows here, so
                # if there is no existing joins, use outer join.
                _, targets, _, joins, path = self.setup_joins(
                    name.split(LOOKUP_SEP), opts, alias, allow_many=allow_m2m)
                targets, final_alias, joins = self.trim_joins(targets, joins, path)
                for target in targets:
                    self.select.append(SelectInfo((final_alias, target.column), target))
        except MultiJoin:
            raise FieldError("Invalid field name: '%s'" % name)
        except FieldError:
            if LOOKUP_SEP in name:
                # For lookups spanning over relationships, show the error
                # from the model on which the lookup failed.
                raise
            else:
                names = sorted([f.name for f in opts.get_fields()] + list(self.extra)
                               + list(self.annotation_select))
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

    def clear_ordering(self, force_empty):
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

        for col, _ in self.select:
            self.group_by.append(col)

        if self._annotations:
            for alias, annotation in six.iteritems(self.annotations):
                for col in annotation.get_group_by_cols():
                    self.group_by.append(col)

    def add_select_related(self, fields):
        """
        Sets up the select_related data structure so that we only select
        certain related models (as opposed to all models, when
        self.select_related=True).
        """
        if isinstance(self.select_related, bool):
            field_dict = {}
        else:
            field_dict = self.select_related
        for field in fields:
            d = field_dict
            for part in field.split(LOOKUP_SEP):
                d = d.setdefault(part, {})
        self.select_related = field_dict
        self.related_select_cols = []

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
            select_pairs = OrderedDict()
            if select_params:
                param_iter = iter(select_params)
            else:
                param_iter = iter([])
            for name, entry in select.items():
                entry = force_text(entry)
                entry_params = []
                pos = entry.find("%s")
                while pos != -1:
                    if pos == 0 or entry[pos - 1] != '%':
                        entry_params.append(next(param_iter))
                    pos = entry.find("%s", pos + 2)
                select_pairs[name] = (entry, entry_params)
            # This is order preserving, since self.extra_select is an OrderedDict.
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
        # splitting and handling when computing the SQL column names (as part of
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
        field_names = set(field_names)
        if 'pk' in field_names:
            field_names.remove('pk')
            field_names.add(self.get_meta().pk.name)

        if defer:
            # Remove any existing deferred names from the current set before
            # setting the new names.
            self.deferred_loading = field_names.difference(existing), False
        else:
            # Replace any existing "immediate load" field names.
            self.deferred_loading = field_names, False

    def get_loaded_field_names(self):
        """
        If any fields are marked to be deferred, returns a dictionary mapping
        models to a set of names in those fields that will be loaded. If a
        model is not in the returned dictionary, none of its fields are
        deferred.

        If no fields are marked for deferral, returns an empty dictionary.
        """
        # We cache this because we call this function multiple times
        # (compiler.fill_related_selections, query.iterator)
        try:
            return self._loaded_field_names_cache
        except AttributeError:
            collection = {}
            self.deferred_to_data(collection, self.get_loaded_field_names_cb)
            self._loaded_field_names_cache = collection
            return collection

    def get_loaded_field_names_cb(self, target, model, fields):
        """
        Callback used by get_deferred_field_names().
        """
        target[model] = set(f.name for f in fields)

    def set_aggregate_mask(self, names):
        warnings.warn(
            "set_aggregate_mask() is deprecated. Use set_annotation_mask() instead.",
            RemovedInDjango20Warning, stacklevel=2)
        self.set_annotation_mask(names)

    def set_annotation_mask(self, names):
        "Set the mask of annotations that will actually be returned by the SELECT"
        if names is None:
            self.annotation_select_mask = None
        else:
            self.annotation_select_mask = set(names)
        self._annotation_select_cache = None

    def append_aggregate_mask(self, names):
        warnings.warn(
            "append_aggregate_mask() is deprecated. Use append_annotation_mask() instead.",
            RemovedInDjango20Warning, stacklevel=2)
        self.append_annotation_mask(names)

    def append_annotation_mask(self, names):
        if self.annotation_select_mask is not None:
            self.set_annotation_mask(set(names).union(self.annotation_select_mask))

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

    @property
    def annotation_select(self):
        """The OrderedDict of aggregate columns that are not masked, and should
        be used in the SELECT clause.

        This result is cached for optimization purposes.
        """
        if self._annotation_select_cache is not None:
            return self._annotation_select_cache
        elif not self._annotations:
            return {}
        elif self.annotation_select_mask is not None:
            self._annotation_select_cache = OrderedDict(
                (k, v) for k, v in self.annotations.items()
                if k in self.annotation_select_mask
            )
            return self._annotation_select_cache
        else:
            return self.annotations

    @property
    def aggregate_select(self):
        warnings.warn(
            "aggregate_select() is deprecated. Use annotation_select() instead.",
            RemovedInDjango20Warning, stacklevel=2)
        return self.annotation_select

    @property
    def extra_select(self):
        if self._extra_select_cache is not None:
            return self._extra_select_cache
        if not self._extra:
            return {}
        elif self.extra_select_mask is not None:
            self._extra_select_cache = OrderedDict(
                (k, v) for k, v in self.extra.items()
                if k in self.extra_select_mask
            )
            return self._extra_select_cache
        else:
            return self.extra

    def trim_start(self, names_with_path):
        """
        Trims joins from the start of the join path. The candidates for trim
        are the PathInfos in names_with_path structure that are m2m joins.

        Also sets the select column so the start matches the join.

        This method is meant to be used for generating the subquery joins &
        cols in split_exclude().

        Returns a lookup usable for doing outerq.filter(lookup=self). Returns
        also if the joins in the prefix contain a LEFT OUTER join.
        _"""
        all_paths = []
        for _, paths in names_with_path:
            all_paths.extend(paths)
        contains_louter = False
        # Trim and operate only on tables that were generated for
        # the lookup part of the query. That is, avoid trimming
        # joins generated for F() expressions.
        lookup_tables = [t for t in self.tables if t in self._lookup_joins or t == self.tables[0]]
        for trimmed_paths, path in enumerate(all_paths):
            if path.m2m:
                break
            if self.alias_map[lookup_tables[trimmed_paths + 1]].join_type == LOUTER:
                contains_louter = True
            alias = lookup_tables[trimmed_paths]
            self.unref_alias(alias)
        # The path.join_field is a Rel, lets get the other side's field
        join_field = path.join_field.field
        # Build the filter prefix.
        paths_in_prefix = trimmed_paths
        trimmed_prefix = []
        for name, path in names_with_path:
            if paths_in_prefix - len(path) < 0:
                break
            trimmed_prefix.append(name)
            paths_in_prefix -= len(path)
        trimmed_prefix.append(
            join_field.foreign_related_fields[0].name)
        trimmed_prefix = LOOKUP_SEP.join(trimmed_prefix)
        # Lets still see if we can trim the first join from the inner query
        # (that is, self). We can't do this for LEFT JOINs because we would
        # miss those rows that have nothing on the outer side.
        if self.alias_map[lookup_tables[trimmed_paths + 1]].join_type != LOUTER:
            select_fields = [r[0] for r in join_field.related_fields]
            select_alias = lookup_tables[trimmed_paths + 1]
            self.unref_alias(lookup_tables[trimmed_paths])
            extra_restriction = join_field.get_extra_restriction(
                self.where_class, None, lookup_tables[trimmed_paths + 1])
            if extra_restriction:
                self.where.add(extra_restriction, AND)
        else:
            # TODO: It might be possible to trim more joins from the start of the
            # inner query if it happens to have a longer join chain containing the
            # values in select_fields. Lets punt this one for now.
            select_fields = [r[1] for r in join_field.related_fields]
            select_alias = lookup_tables[trimmed_paths]
        # The found starting point is likely a Join instead of a BaseTable reference.
        # But the first entry in the query's FROM clause must not be a JOIN.
        for table in self.tables:
            if self.alias_refcount[table] > 0:
                self.alias_map[table] = BaseTable(self.alias_map[table].table_name, table)
                break
        self.select = [SelectInfo((select_alias, f.column), f) for f in select_fields]
        return trimmed_prefix, contains_louter

    def is_nullable(self, field):
        """
        A helper to check if the given field should be treated as nullable.

        Some backends treat '' as null and Django treats such fields as
        nullable for those backends. In such situations field.null can be
        False even if we should treat the field as nullable.
        """
        # We need to use DEFAULT_DB_ALIAS here, as QuerySet does not have
        # (nor should it have) knowledge of which connection is going to be
        # used. The proper fix would be to defer all decisions where
        # is_nullable() is needed to the compiler stage, but that is not easy
        # to do currently.
        if ((connections[DEFAULT_DB_ALIAS].features.interprets_empty_strings_as_nulls)
                and field.empty_strings_allowed):
            return True
        else:
            return field.null


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


def add_to_dict(data, key, value):
    """
    A helper function to add "value" to the set of values for "key", whether or
    not "key" already exists.
    """
    if key in data:
        data[key].add(value)
    else:
        data[key] = {value}


def is_reverse_o2o(field):
    """
    A little helper to check if the given field is reverse-o2o. The field is
    expected to be some sort of relation field or related object.
    """
    return not hasattr(field, 'rel') and field.field.unique


def alias_diff(refcounts_before, refcounts_after):
    """
    Given the before and after copies of refcounts works out which aliases
    have been added to the after copy.
    """
    # Use -1 as default value so that any join that is created, then trimmed
    # is seen as added.
    return set(t for t in refcounts_after
               if refcounts_after[t] > refcounts_before.get(t, -1))


class JoinPromoter(object):
    """
    A class to abstract away join promotion problems for complex filter
    conditions.
    """

    def __init__(self, connector, num_children, negated):
        self.connector = connector
        self.negated = negated
        if self.negated:
            if connector == AND:
                self.effective_connector = OR
            else:
                self.effective_connector = AND
        else:
            self.effective_connector = self.connector
        self.num_children = num_children
        # Maps of table alias to how many times it is seen as required for
        # inner and/or outer joins.
        self.outer_votes = {}
        self.inner_votes = {}

    def add_votes(self, inner_votes):
        """
        Add single vote per item to self.inner_votes. Parameter can be any
        iterable.
        """
        for voted in inner_votes:
            self.inner_votes[voted] = self.inner_votes.get(voted, 0) + 1

    def update_join_types(self, query):
        """
        Change join types so that the generated query is as efficient as
        possible, but still correct. So, change as many joins as possible
        to INNER, but don't make OUTER joins INNER if that could remove
        results from the query.
        """
        to_promote = set()
        to_demote = set()
        # The effective_connector is used so that NOT (a AND b) is treated
        # similarly to (a OR b) for join promotion.
        for table, votes in self.inner_votes.items():
            # We must use outer joins in OR case when the join isn't contained
            # in all of the joins. Otherwise the INNER JOIN itself could remove
            # valid results. Consider the case where a model with rel_a and
            # rel_b relations is queried with rel_a__col=1 | rel_b__col=2. Now,
            # if rel_a join doesn't produce any results is null (for example
            # reverse foreign key or null value in direct foreign key), and
            # there is a matching row in rel_b with col=2, then an INNER join
            # to rel_a would remove a valid match from the query. So, we need
            # to promote any existing INNER to LOUTER (it is possible this
            # promotion in turn will be demoted later on).
            if self.effective_connector == 'OR' and votes < self.num_children:
                to_promote.add(table)
            # If connector is AND and there is a filter that can match only
            # when there is a joinable row, then use INNER. For example, in
            # rel_a__col=1 & rel_b__col=2, if either of the rels produce NULL
            # as join output, then the col=1 or col=2 can't match (as
            # NULL=anything is always false).
            # For the OR case, if all children voted for a join to be inner,
            # then we can use INNER for the join. For example:
            #     (rel_a__col__icontains=Alex | rel_a__col__icontains=Russell)
            # then if rel_a doesn't produce any rows, the whole condition
            # can't match. Hence we can safely use INNER join.
            if self.effective_connector == 'AND' or (
                    self.effective_connector == 'OR' and votes == self.num_children):
                to_demote.add(table)
            # Finally, what happens in cases where we have:
            #    (rel_a__col=1|rel_b__col=2) & rel_a__col__gte=0
            # Now, we first generate the OR clause, and promote joins for it
            # in the first if branch above. Both rel_a and rel_b are promoted
            # to LOUTER joins. After that we do the AND case. The OR case
            # voted no inner joins but the rel_a__col__gte=0 votes inner join
            # for rel_a. We demote it back to INNER join (in AND case a single
            # vote is enough). The demotion is OK, if rel_a doesn't produce
            # rows, then the rel_a__col__gte=0 clause can't be true, and thus
            # the whole clause must be false. So, it is safe to use INNER
            # join.
            # Note that in this example we could just as well have the __gte
            # clause and the OR clause swapped. Or we could replace the __gte
            # clause with an OR clause containing rel_a__col=1|rel_a__col=2,
            # and again we could safely demote to INNER.
        query.promote_joins(to_promote)
        query.demote_joins(to_demote)
        return to_demote
