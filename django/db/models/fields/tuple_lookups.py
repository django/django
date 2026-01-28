import itertools

from django.core.exceptions import EmptyResultSet
from django.db import NotSupportedError, models
from django.db.models.expressions import (
    ColPairs,
    Exists,
    Func,
    ResolvedOuterRef,
    Subquery,
    Value,
)
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
)
from django.db.models.sql import Query
from django.db.models.sql.where import AND, OR, WhereNode


class Tuple(Func):
    allows_composite_expressions = True
    function = ""
    output_field = models.Field()

    def __len__(self):
        return len(self.source_expressions)

    def __iter__(self):
        return iter(self.source_expressions)

    def as_sqlite(self, compiler, connection):
        if connection.get_database_version() < (3, 37) and isinstance(
            first_expr := self.source_expressions[0], Tuple
        ):
            first_expr = first_expr.copy()
            first_expr.function = "VALUES"
            return Tuple(first_expr, *self.source_expressions[1:]).as_sql(
                compiler, connection
            )
        return self.as_sql(compiler, connection)


class TupleLookupMixin:
    allows_composite_expressions = True

    def get_prep_lookup(self):
        if self.rhs_is_direct_value():
            self.check_rhs_is_tuple_or_list()
            self.check_rhs_length_equals_lhs_length()
        else:
            self.check_rhs_is_supported_expression()
            super().get_prep_lookup()
        return self.rhs

    def check_rhs_is_tuple_or_list(self):
        if not isinstance(self.rhs, (tuple, list)):
            lhs_str = self.get_lhs_str()
            raise ValueError(
                f"{self.lookup_name!r} lookup of {lhs_str} must be a tuple or a list"
            )

    def check_rhs_length_equals_lhs_length(self):
        len_lhs = len(self.lhs)
        if len_lhs != len(self.rhs):
            lhs_str = self.get_lhs_str()
            raise ValueError(
                f"{self.lookup_name!r} lookup of {lhs_str} must have {len_lhs} elements"
            )

    def check_rhs_is_supported_expression(self):
        if not isinstance(self.rhs, (ResolvedOuterRef, Query)):
            lhs_str = self.get_lhs_str()
            rhs_cls = self.rhs.__class__.__name__
            raise ValueError(
                f"{self.lookup_name!r} subquery lookup of {lhs_str} "
                f"only supports OuterRef and QuerySet objects (received {rhs_cls!r})"
            )

    def get_lhs_str(self):
        if isinstance(self.lhs, ColPairs):
            return repr(self.lhs.field.name)
        else:
            names = ", ".join(repr(f.name) for f in self.lhs)
            return f"({names})"

    def get_prep_lhs(self):
        if isinstance(self.lhs, (tuple, list)):
            return Tuple(*self.lhs)
        return super().get_prep_lhs()

    def process_lhs(self, compiler, connection, lhs=None):
        sql, params = super().process_lhs(compiler, connection, lhs)
        if not isinstance(self.lhs, Tuple):
            sql = f"({sql})"
        return sql, params

    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            args = [
                (
                    val
                    if hasattr(val, "as_sql")
                    else Value(val, output_field=col.output_field)
                )
                for col, val in zip(self.lhs, self.rhs)
            ]
            return compiler.compile(Tuple(*args))
        else:
            sql, params = compiler.compile(self.rhs)
            if isinstance(self.rhs, ColPairs):
                return "(%s)" % sql, params
            elif isinstance(self.rhs, Query):
                return super().process_rhs(compiler, connection)
            else:
                raise ValueError(
                    "Composite field lookups only work with composite expressions."
                )

    def get_fallback_sql(self, compiler, connection):
        raise NotImplementedError(
            f"{self.__class__.__name__}.get_fallback_sql() must be implemented "
            f"for backends that don't have the supports_tuple_lookups feature enabled."
        )

    def as_sql(self, compiler, connection):
        if (
            not connection.features.supports_tuple_comparison_against_subquery
            and isinstance(self.rhs, Query)
            and self.rhs.subquery
            and isinstance(
                self, (GreaterThan, GreaterThanOrEqual, LessThan, LessThanOrEqual)
            )
        ):
            lookup = self.lookup_name
            msg = (
                f'"{lookup}" cannot be used to target composite fields '
                "through subqueries on this backend"
            )
            raise NotSupportedError(msg)
        if not connection.features.supports_tuple_lookups:
            return self.get_fallback_sql(compiler, connection)
        return super().as_sql(compiler, connection)


class TupleExact(TupleLookupMixin, Exact):
    def get_fallback_sql(self, compiler, connection):
        if isinstance(self.rhs, Query):
            return super(TupleLookupMixin, self).as_sql(compiler, connection)
        # Process right-hand-side to trigger sanitization.
        self.process_rhs(compiler, connection)
        # e.g.: (a, b, c) == (x, y, z) as SQL:
        # WHERE a = x AND b = y AND c = z
        lookups = [Exact(col, val) for col, val in zip(self.lhs, self.rhs)]
        root = WhereNode(lookups, connector=AND)

        return root.as_sql(compiler, connection)


class TupleIsNull(TupleLookupMixin, IsNull):
    def get_prep_lookup(self):
        rhs = self.rhs
        if isinstance(rhs, (tuple, list)) and len(rhs) == 1:
            rhs = rhs[0]
        if isinstance(rhs, bool):
            return rhs
        raise ValueError(
            "The QuerySet value for an isnull lookup must be True or False."
        )

    def as_sql(self, compiler, connection):
        # e.g.: (a, b, c) is None as SQL:
        # WHERE a IS NULL OR b IS NULL OR c IS NULL
        # e.g.: (a, b, c) is not None as SQL:
        # WHERE a IS NOT NULL AND b IS NOT NULL AND c IS NOT NULL
        rhs = self.rhs
        lookups = [IsNull(col, rhs) for col in self.lhs]
        root = WhereNode(lookups, connector=OR if rhs else AND)
        return root.as_sql(compiler, connection)


class TupleGreaterThan(TupleLookupMixin, GreaterThan):
    def get_fallback_sql(self, compiler, connection):
        # Process right-hand-side to trigger sanitization.
        self.process_rhs(compiler, connection)
        # e.g.: (a, b, c) > (x, y, z) as SQL:
        # WHERE a > x OR (a = x AND (b > y OR (b = y AND c > z)))
        lookups = itertools.cycle([GreaterThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in self.lhs for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list[:-1])
        vals_iter = iter(vals_list[:-1])
        col = next(cols_iter)
        val = next(vals_iter)
        lookup = next(lookups)
        connector = next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup = next(lookups)
            connector = next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleGreaterThanOrEqual(TupleLookupMixin, GreaterThanOrEqual):
    def get_fallback_sql(self, compiler, connection):
        # Process right-hand-side to trigger sanitization.
        self.process_rhs(compiler, connection)
        # e.g.: (a, b, c) >= (x, y, z) as SQL:
        # WHERE a > x OR (a = x AND (b > y OR (b = y AND (c > z OR c = z))))
        lookups = itertools.cycle([GreaterThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in self.lhs for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list)
        vals_iter = iter(vals_list)
        col = next(cols_iter)
        val = next(vals_iter)
        lookup = next(lookups)
        connector = next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup = next(lookups)
            connector = next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleLessThan(TupleLookupMixin, LessThan):
    def get_fallback_sql(self, compiler, connection):
        # Process right-hand-side to trigger sanitization.
        self.process_rhs(compiler, connection)
        # e.g.: (a, b, c) < (x, y, z) as SQL:
        # WHERE a < x OR (a = x AND (b < y OR (b = y AND c < z)))
        lookups = itertools.cycle([LessThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in self.lhs for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list[:-1])
        vals_iter = iter(vals_list[:-1])
        col = next(cols_iter)
        val = next(vals_iter)
        lookup = next(lookups)
        connector = next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup = next(lookups)
            connector = next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleLessThanOrEqual(TupleLookupMixin, LessThanOrEqual):
    def get_fallback_sql(self, compiler, connection):
        # Process right-hand-side to trigger sanitization.
        self.process_rhs(compiler, connection)
        # e.g.: (a, b, c) <= (x, y, z) as SQL:
        # WHERE a < x OR (a = x AND (b < y OR (b = y AND (c < z OR c = z))))
        lookups = itertools.cycle([LessThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in self.lhs for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list)
        vals_iter = iter(vals_list)
        col = next(cols_iter)
        val = next(vals_iter)
        lookup = next(lookups)
        connector = next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup = next(lookups)
            connector = next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleIn(TupleLookupMixin, In):
    def get_prep_lookup(self):
        if self.rhs_is_direct_value():
            self.check_rhs_is_tuple_or_list()
            self.check_rhs_is_collection_of_tuples_or_lists()
            self.check_rhs_elements_length_equals_lhs_length()
        else:
            self.check_rhs_is_query()
            super(TupleLookupMixin, self).get_prep_lookup()

        return self.rhs  # skip checks from mixin

    def check_rhs_is_collection_of_tuples_or_lists(self):
        if not all(isinstance(vals, (tuple, list)) for vals in self.rhs):
            lhs_str = self.get_lhs_str()
            raise ValueError(
                f"{self.lookup_name!r} lookup of {lhs_str} "
                "must be a collection of tuples or lists"
            )

    def check_rhs_elements_length_equals_lhs_length(self):
        len_lhs = len(self.lhs)
        if not all(len_lhs == len(vals) for vals in self.rhs):
            lhs_str = self.get_lhs_str()
            raise ValueError(
                f"{self.lookup_name!r} lookup of {lhs_str} "
                f"must have {len_lhs} elements each"
            )

    def check_rhs_is_query(self):
        if not isinstance(self.rhs, (Query, Subquery)):
            lhs_str = self.get_lhs_str()
            rhs_cls = self.rhs.__class__.__name__
            raise ValueError(
                f"{self.lookup_name!r} subquery lookup of {lhs_str} "
                f"must be a Query object (received {rhs_cls!r})"
            )

    def process_rhs(self, compiler, connection):
        if not self.rhs_is_direct_value():
            return super(TupleLookupMixin, self).process_rhs(compiler, connection)

        rhs = self.rhs
        if not rhs:
            raise EmptyResultSet

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a, b, c) IN ((x1, y1, z1), (x2, y2, z2))
        result = []
        lhs = self.lhs

        for vals in rhs:
            # Remove any tuple containing None from the list as NULL is never
            # equal to anything.
            if any(val is None for val in vals):
                continue
            result.append(
                Tuple(
                    *[
                        (
                            val
                            if hasattr(val, "as_sql")
                            else Value(val, output_field=col.output_field)
                        )
                        for col, val in zip(lhs, vals)
                    ]
                )
            )

        if not result:
            raise EmptyResultSet

        return compiler.compile(Tuple(*result))

    def get_fallback_sql(self, compiler, connection):
        rhs = self.rhs
        if not rhs:
            raise EmptyResultSet
        if isinstance(rhs, Query):
            rhs_exprs = itertools.chain.from_iterable(
                (
                    select_expr
                    if isinstance((select_expr := select[0]), ColPairs)
                    else [select_expr]
                )
                for select in rhs.get_compiler(connection=connection).get_select()[0]
            )
            rhs = rhs.clone()
            rhs.add_q(
                models.Q(*[Exact(col, val) for col, val in zip(self.lhs, rhs_exprs)])
            )
            return compiler.compile(Exists(rhs))
        elif not self.rhs_is_direct_value():
            return super(TupleLookupMixin, self).as_sql(compiler, connection)

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a = x1 AND b = y1 AND c = z1)
        #    OR (a = x2 AND b = y2 AND c = z2)
        root = WhereNode([], connector=OR)
        lhs = self.lhs

        for vals in rhs:
            # Remove any tuple containing None from the list as NULL is never
            # equal to anything.
            if any(val is None for val in vals):
                continue
            lookups = [Exact(col, val) for col, val in zip(lhs, vals)]
            root.children.append(WhereNode(lookups, connector=AND))

        if not root.children:
            raise EmptyResultSet
        return root.as_sql(compiler, connection)


tuple_lookups = {
    "exact": TupleExact,
    "gt": TupleGreaterThan,
    "gte": TupleGreaterThanOrEqual,
    "lt": TupleLessThan,
    "lte": TupleLessThanOrEqual,
    "in": TupleIn,
    "isnull": TupleIsNull,
}
