from copy import copy
import weakref

import django
from django.core.exceptions import EmptyResultSet
from django.db.models.expressions import Col, Expression, Ref
from django.db.models.query_utils import Q
from django.db.models.sql.constants import INNER, LOUTER
from django.db.models.sql.datastructures import BaseTable


__all__ = ["CTE", "with_cte"]


def with_cte(*ctes, select):
    """Attach Common Table Expression(s) (CTEs) to a model or queryset."""
    from django.db.models.query import QuerySet

    if isinstance(select, CTE):
        select = select.queryset()
    elif not isinstance(select, QuerySet):
        select = select._default_manager.all()
    select.query._with_ctes += ctes
    return select


class CTE:
    """Common Table Expression.

    :param queryset: A queryset to use as the body of the CTE.
    :param name: Optional name parameter for the CTE (default: "cte").
    :param materialized: Optional parameter (default: False) which enforces
        using MATERIALIZED for supporting databases.
    """

    def __init__(self, queryset, name="cte", materialized=False):
        self._set_queryset(queryset)
        self.name = name
        self.col = CTEColumns(self)
        self.materialized = materialized

    def __getstate__(self):
        return (self.query, self.name, self.materialized, self._iterable_class)

    def __setstate__(self, state):
        if len(state) == 3:
            # Keep compatibility with the previous serialization method.
            self.query, self.name, self.materialized = state
            from django.db.models.query import ValuesIterable

            self._iterable_class = ValuesIterable
        else:
            self.query, self.name, self.materialized, self._iterable_class = state
        self.col = CTEColumns(self)

    def __repr__(self):
        return f"<{type(self).__name__} {self.name}>"

    def _set_queryset(self, queryset):
        self.query = None if queryset is None else queryset.query
        from django.db.models.query import ValuesIterable

        self._iterable_class = getattr(queryset, "_iterable_class", ValuesIterable)

    @classmethod
    def recursive(cls, make_cte_queryset, name="cte", materialized=False):
        """Recursive Common Table Expression."""
        cte = cls(None, name, materialized)
        cte._set_queryset(make_cte_queryset(cte))
        return cte

    def join(self, model_or_queryset, *filter_q, **filter_kw):
        """Join this CTE to the given model or queryset."""
        if isinstance(model_or_queryset, QuerySet):
            queryset = model_or_queryset.all()
        else:
            queryset = model_or_queryset._default_manager.all()
        join_type = filter_kw.pop("_join_type", INNER)
        query = queryset.query

        # Add necessary joins to query, but no filter.
        q_object = Q(*filter_q, **filter_kw)
        map_ = query.alias_map
        existing_inner = {a for a in map_ if map_[a].join_type == INNER}
        if django.VERSION >= (5, 2):
            on_clause, _ = query._add_q(
                q_object, query.used_aliases, update_join_types=(join_type == INNER)
            )
        else:
            on_clause, _ = query._add_q(q_object, query.used_aliases)
        query.demote_joins(existing_inner)

        parent = query.get_initial_alias()
        query.join(QJoin(parent, self.name, self.name, on_clause, join_type))
        return queryset

    def queryset(self):
        """Get a queryset selecting from this CTE."""
        cte_query = self.query
        qs = cte_query.model._default_manager.get_queryset()
        qs._iterable_class = self._iterable_class
        qs._fields = ()  # Allow any field names to be used in further annotations.

        from django.db.models.sql.query import Query

        query = Query(cte_query.model)
        query.join(BaseTable(self.name, None))
        query.default_cols = cte_query.default_cols
        query.deferred_loading = cte_query.deferred_loading

        if django.VERSION < (5, 2) and cte_query.values_select:
            query.set_values(cte_query.values_select)

        if cte_query.select and not cte_query.default_cols and not getattr(
            cte_query, "selected", None
        ):
            query.select = [
                CTEColumnRef(expr.target.column, self.name, expr.output_field)
                if isinstance(expr, Col)
                else expr
                for expr in cte_query.select
            ]

        if cte_query.annotations:
            for alias, value in cte_query.annotations.items():
                col = CTEColumnRef(alias, self.name, value.output_field)
                query.add_annotation(col, alias)
        query.annotation_select_mask = cte_query.annotation_select_mask

        selected = getattr(cte_query, "_auto_cte_selected", None)
        if selected is None:
            selected = getattr(cte_query, "selected", None)
        if selected:
            selected_deferred = getattr(
                cte_query, "_auto_cte_selected_deferred", set()
            )
            for alias in selected:
                if alias in selected_deferred:
                    continue
                if alias not in cte_query.annotations:
                    output_field = cte_query.resolve_ref(alias).output_field
                    col = CTEColumnRef(alias, self.name, output_field)
                    query.add_annotation(col, alias)
            query.selected = {alias: alias for alias in selected}

        qs.query = query
        return qs

    def _resolve_ref(self, name):
        selected = getattr(self.query, "selected", None)
        if selected and name in selected and name not in self.query.annotations:
            return Ref(name, self.query.resolve_ref(name))
        return self.query.resolve_ref(name)

    def resolve_expression(self, *args, **kw):
        if self.query is None:
            raise ValueError("Cannot resolve recursive CTE without a query.")
        clone = copy(self)
        clone.query = clone.query.resolve_expression(*args, **kw)
        return clone


class CTEColumns:
    def __init__(self, cte):
        self._cte = weakref.ref(cte)

    def __getattr__(self, name):
        return CTEColumn(self._cte(), name)


class CTEColumn(Expression):
    def __init__(self, cte, name, output_field=None):
        self._cte = cte
        self.table_alias = cte.name
        self.name = self.alias = name
        self._output_field = output_field

    def __repr__(self):
        return "<{} {}.{}>".format(self.__class__.__name__, self._cte.name, self.name)

    @property
    def _ref(self):
        if self._cte.query is None:
            raise ValueError(
                "cannot resolve '{cte}.{name}' in recursive CTE setup. "
                "Hint: use ExpressionWrapper({cte}.col.{name}, output_field=...).".format(
                    cte=self._cte.name, name=self.name
                )
            )
        ref = self._cte._resolve_ref(self.name)
        if ref is self or self in ref.get_source_expressions():
            raise ValueError("Circular reference: {} = {}".format(self, ref))
        return ref

    @property
    def target(self):
        return self._ref.target

    @property
    def output_field(self):
        if self._cte.query is None:
            raise AttributeError
        if self._output_field is not None:
            return self._output_field
        return self._ref.output_field

    def as_sql(self, compiler, connection):
        qn = compiler.quote_name_unless_alias
        ref = self._ref
        if isinstance(ref, Col) and self.name == "pk":
            column = ref.target.column
        else:
            column = self.name
        return "%s.%s" % (qn(self.table_alias), qn(column)), []

    def relabeled_clone(self, relabels):
        if self.table_alias is not None and self.table_alias in relabels:
            clone = self.copy()
            clone.table_alias = relabels[self.table_alias]
            return clone
        return self


class CTEColumnRef(Expression):
    def __init__(self, name, cte_name, output_field):
        self.name = name
        self.cte_name = cte_name
        self.output_field = output_field
        self._alias = None

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        if query:
            clone = self.copy()
            clone._alias = self._alias or query.table_map.get(self.cte_name, [self.cte_name])[
                0
            ]
            return clone
        return super().resolve_expression(query, allow_joins, reuse, summarize, for_save)

    def relabeled_clone(self, change_map):
        if self.cte_name not in change_map and self._alias not in change_map:
            return super().relabeled_clone(change_map)
        clone = self.copy()
        if self.cte_name in change_map:
            clone._alias = change_map[self.cte_name]
        if self._alias in change_map:
            clone._alias = change_map[self._alias]
        return clone

    def as_sql(self, compiler, connection):
        qn = compiler.quote_name_unless_alias
        table = self._alias or compiler.query.table_map.get(
            self.cte_name, [self.cte_name]
        )[0]
        return "%s.%s" % (qn(table), qn(self.name)), []


class QJoin:
    """Join clause with join condition from Q object clause."""

    filtered_relation = None

    def __init__(self, parent_alias, table_name, table_alias, on_clause, join_type=INNER, nullable=None):
        self.parent_alias = parent_alias
        self.table_name = table_name
        self.table_alias = table_alias
        self.on_clause = on_clause
        self.join_type = join_type  # LOUTER or INNER
        self.nullable = join_type != INNER if nullable is None else nullable

    @property
    def identity(self):
        return (self.__class__, self.table_name, self.parent_alias, self.join_type, self.on_clause)

    def __hash__(self):
        return hash(self.identity)

    def __eq__(self, other):
        if not isinstance(other, QJoin):
            return NotImplemented
        return self.identity == other.identity

    def equals(self, other):
        return self.identity == other.identity

    def as_sql(self, compiler, connection):
        """Generate join clause SQL."""
        on_clause_sql, params = self.on_clause.as_sql(compiler, connection)
        if self.table_alias == self.table_name:
            alias = ""
        else:
            alias = " %s" % self.table_alias
        qn = compiler.quote_name_unless_alias
        sql = "%s %s%s ON %s" % (self.join_type, qn(self.table_name), alias, on_clause_sql)
        return sql, params

    def relabeled_clone(self, change_map):
        return self.__class__(
            parent_alias=change_map.get(self.parent_alias, self.parent_alias),
            table_name=self.table_name,
            table_alias=change_map.get(self.table_alias, self.table_alias),
            on_clause=self.on_clause.relabeled_clone(change_map),
            join_type=self.join_type,
            nullable=self.nullable,
        )

    class join_field:
        class related_model:
            class _meta:
                local_concrete_fields = ()


def generate_cte_sql(connection, query, as_sql):
    if not query._with_ctes:
        return as_sql()

    explain_attribute = "explain_info"
    explain_info = getattr(query, explain_attribute, None)
    explain_format = getattr(explain_info, "format", None)
    explain_options = dict(getattr(explain_info, "options", {}))

    explain_query_or_info = getattr(query, explain_attribute, None)
    sql = []
    if explain_query_or_info:
        sql.append(
            connection.ops.explain_query_prefix(explain_format, **explain_options)
        )
        # Ensure EXPLAIN stays outside the WITH clause.
        setattr(query, explain_attribute, None)

    base_sql, base_params = as_sql()

    if explain_query_or_info:
        setattr(query, explain_attribute, explain_query_or_info)

    ctes = []
    params = []
    cte_entries = []
    quoted_names = {
        cte.name: connection.ops.quote_name(cte.name) for cte in query._with_ctes
    }
    for cte in query._with_ctes:
        if django.VERSION > (4, 2):
            _ignore_with_col_aliases(cte.query)

        alias = query.alias_map.get(cte.name)
        should_elide_empty = not isinstance(alias, QJoin) or alias.join_type != LOUTER

        compiler = cte.query.get_compiler(connection=connection, elide_empty=should_elide_empty)
        qn = compiler.quote_name_unless_alias
        ignore_cte_name = getattr(cte.query, "_ignore_cte_name", None)
        if getattr(cte.query, "_cte_name", None):
            cte.query._ignore_cte_name = True
        cte_explain_info = getattr(cte.query, explain_attribute, None)
        if cte_explain_info is not None:
            setattr(cte.query, explain_attribute, None)
        try:
            cte_sql, cte_params = compiler.as_sql()
        finally:
            if getattr(cte.query, "_cte_name", None):
                if ignore_cte_name is None:
                    delattr(cte.query, "_ignore_cte_name")
                else:
                    cte.query._ignore_cte_name = ignore_cte_name
            if cte_explain_info is not None:
                setattr(cte.query, explain_attribute, cte_explain_info)
        cte_entries.append((cte, qn(cte.name), cte_sql, cte_params))

    used = {
        name for name, quoted in quoted_names.items() if quoted in base_sql
    }
    queue = list(used)
    sql_by_name = {cte.name: cte_sql for cte, _, cte_sql, _ in cte_entries}
    while queue:
        name = queue.pop()
        cte_sql = sql_by_name.get(name)
        if cte_sql is None:
            continue
        for other_name, quoted in quoted_names.items():
            if other_name == name:
                continue
            if quoted in cte_sql and other_name not in used:
                used.add(other_name)
                queue.append(other_name)

    for cte, cte_name_sql, cte_sql, cte_params in cte_entries:
        if cte.name not in used:
            continue
        template = get_cte_query_template(cte)
        ctes.append(template.format(name=cte_name_sql, query=cte_sql))
        params.extend(cte_params)

    if ctes:
        # Always use WITH RECURSIVE.
        sql.extend(["WITH RECURSIVE", ", ".join(ctes)])
    sql.append(base_sql)
    params.extend(base_params)
    return " ".join(sql), tuple(params)


def get_cte_query_template(cte):
    if cte.materialized:
        return "{name} AS MATERIALIZED ({query})"
    return "{name} AS ({query})"


def _ignore_with_col_aliases(cte_query):
    if getattr(cte_query, "combined_queries", None):
        for query in cte_query.combined_queries:
            query._ignore_with_col_aliases = True
