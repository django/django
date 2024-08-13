import itertools

from django.core.exceptions import EmptyResultSet
from django.db.models.expressions import ColPairs, Func, Value
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
)
from django.db.models.sql.where import AND, OR, WhereNode


class Tuple(Func):
    function = ""


class TupleLookupMixin:
    def get_prep_lookup(self):
        self.check_tuple_lookup()
        return super().get_prep_lookup()

    def check_tuple_lookup(self):
        assert isinstance(self.lhs, ColPairs)
        self.check_rhs_is_tuple_or_list()
        self.check_rhs_length_equals_lhs_length()

    def check_rhs_is_tuple_or_list(self):
        if not isinstance(self.rhs, (tuple, list)):
            raise ValueError(
                f"'{self.lookup_name}' lookup of '{self.lhs.field.name}' field "
                "must be a tuple or a list"
            )

    def check_rhs_length_equals_lhs_length(self):
        if len(self.lhs) != len(self.rhs):
            raise ValueError(
                f"'{self.lookup_name}' lookup of '{self.lhs.field.name}' field "
                f"must have {len(self.lhs)} elements"
            )

    def check_rhs_is_collection_of_tuples_or_lists(self):
        if not all(isinstance(vals, (tuple, list)) for vals in self.rhs):
            raise ValueError(
                f"'{self.lookup_name}' lookup of '{self.lhs.field.name}' field "
                f"must be a collection of tuples or lists"
            )

    def check_rhs_elements_length_equals_lhs_length(self):
        if not all(len(self.lhs) == len(vals) for vals in self.rhs):
            raise ValueError(
                f"'{self.lookup_name}' lookup of '{self.lhs.field.name}' field "
                f"must have {len(self.lhs)} elements each"
            )

    def as_sql(self, compiler, connection):
        # e.g.: (a, b, c) == (x, y, z) as SQL:
        # WHERE (a, b, c) = (x, y, z)
        vals = [
            Value(val, output_field=col.output_field)
            for col, val in zip(self.lhs, self.rhs)
        ]
        lookup_class = self.__class__.__bases__[-1]
        lookup = lookup_class(Tuple(self.lhs), Tuple(*vals))
        return lookup.as_sql(compiler, connection)


class TupleExact(TupleLookupMixin, Exact):
    def as_oracle(self, compiler, connection):
        # e.g.: (a, b, c) == (x, y, z) as SQL:
        # WHERE a = x AND b = y AND c = z
        cols = self.lhs.get_cols()
        lookups = [Exact(col, val) for col, val in zip(cols, self.rhs)]
        root = WhereNode(lookups, connector=AND)

        return root.as_sql(compiler, connection)


class TupleIsNull(IsNull):
    def as_sql(self, compiler, connection):
        # e.g.: (a, b, c) is None as SQL:
        # WHERE a IS NULL AND b IS NULL AND c IS NULL
        vals = self.rhs
        if isinstance(vals, bool):
            vals = [vals] * len(self.lhs)

        cols = self.lhs.get_cols()
        lookups = [IsNull(col, val) for col, val in zip(cols, vals)]
        root = WhereNode(lookups, connector=AND)

        return root.as_sql(compiler, connection)


class TupleGreaterThan(TupleLookupMixin, GreaterThan):
    def as_oracle(self, compiler, connection):
        # e.g.: (a, b, c) > (x, y, z) as SQL:
        # WHERE a > x OR (a = x AND (b > y OR (b = y AND c > z)))
        cols = self.lhs.get_cols()
        lookups = itertools.cycle([GreaterThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list[:-1])
        vals_iter = iter(vals_list[:-1])
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleGreaterThanOrEqual(TupleLookupMixin, GreaterThanOrEqual):
    def as_oracle(self, compiler, connection):
        # e.g.: (a, b, c) >= (x, y, z) as SQL:
        # WHERE a > x OR (a = x AND (b > y OR (b = y AND (c > z OR c = z))))
        cols = self.lhs.get_cols()
        lookups = itertools.cycle([GreaterThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list)
        vals_iter = iter(vals_list)
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleLessThan(TupleLookupMixin, LessThan):
    def as_oracle(self, compiler, connection):
        # e.g.: (a, b, c) < (x, y, z) as SQL:
        # WHERE a < x OR (a = x AND (b < y OR (b = y AND c < z)))
        cols = self.lhs.get_cols()
        lookups = itertools.cycle([LessThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list[:-1])
        vals_iter = iter(vals_list[:-1])
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleLessThanOrEqual(TupleLookupMixin, LessThanOrEqual):
    def as_oracle(self, compiler, connection):
        # e.g.: (a, b, c) <= (x, y, z) as SQL:
        # WHERE a < x OR (a = x AND (b < y OR (b = y AND (c < z OR c = z))))
        cols = self.lhs.get_cols()
        lookups = itertools.cycle([LessThan, Exact])
        connectors = itertools.cycle([OR, AND])
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list)
        vals_iter = iter(vals_list)
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return root.as_sql(compiler, connection)


class TupleIn(TupleLookupMixin, In):
    def check_tuple_lookup(self):
        assert isinstance(self.lhs, ColPairs)
        self.check_rhs_is_tuple_or_list()
        self.check_rhs_is_collection_of_tuples_or_lists()
        self.check_rhs_elements_length_equals_lhs_length()

    def as_sql(self, compiler, connection):
        if not self.rhs:
            raise EmptyResultSet

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a, b, c) IN ((x1, y1, z1), (x2, y2, z2))
        rhs = []
        for vals in self.rhs:
            rhs.append(
                Tuple(
                    *[
                        Value(val, output_field=col.output_field)
                        for col, val in zip(self.lhs, vals)
                    ]
                )
            )

        lookup = In(Tuple(self.lhs), Tuple(*rhs))
        return lookup.as_sql(compiler, connection)

    def as_sqlite(self, compiler, connection):
        if not self.rhs:
            raise EmptyResultSet

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a = x1 AND b = y1 AND c = z1) OR (a = x2 AND b = y2 AND c = z2)
        root = WhereNode([], connector=OR)
        cols = self.lhs.get_cols()

        for vals in self.rhs:
            lookups = [Exact(col, val) for col, val in zip(cols, vals)]
            root.children.append(WhereNode(lookups, connector=AND))

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
