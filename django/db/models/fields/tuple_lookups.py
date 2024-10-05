import itertools

from django.core.exceptions import EmptyResultSet
from django.db.models import Field
from django.db.models.expressions import Func, Value
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
    output_field = Field()

    def __len__(self):
        return len(self.source_expressions)

    def __iter__(self):
        return iter(self.source_expressions)


class TupleLookupMixin:
    def get_prep_lookup(self):
        self.check_rhs_length_equals_lhs_length()
        return self.rhs

    def check_rhs_length_equals_lhs_length(self):
        len_lhs = len(self.lhs)
        if len_lhs != len(self.rhs):
            raise ValueError(
                f"'{self.lookup_name}' lookup of '{self.lhs.field.name}' field "
                f"must have {len_lhs} elements"
            )

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
        values = [
            Value(val, output_field=col.output_field)
            for col, val in zip(self.lhs, self.rhs)
        ]
        return Tuple(*values).as_sql(compiler, connection)


class TupleExact(TupleLookupMixin, Exact):
    def as_oracle(self, compiler, connection):
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
    def as_oracle(self, compiler, connection):
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
    def as_oracle(self, compiler, connection):
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
    def as_oracle(self, compiler, connection):
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
    def as_oracle(self, compiler, connection):
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
        self.check_rhs_elements_length_equals_lhs_length()
        return super(TupleLookupMixin, self).get_prep_lookup()

    def check_rhs_elements_length_equals_lhs_length(self):
        len_lhs = len(self.lhs)
        if not all(len_lhs == len(vals) for vals in self.rhs):
            raise ValueError(
                f"'{self.lookup_name}' lookup of '{self.lhs.field.name}' field "
                f"must have {len_lhs} elements each"
            )

    def process_rhs(self, compiler, connection):
        rhs = self.rhs
        if not rhs:
            raise EmptyResultSet

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a, b, c) IN ((x1, y1, z1), (x2, y2, z2))
        result = []
        lhs = self.lhs

        for vals in rhs:
            result.append(
                Tuple(
                    *[
                        Value(val, output_field=col.output_field)
                        for col, val in zip(lhs, vals)
                    ]
                )
            )

        return Tuple(*result).as_sql(compiler, connection)

    def as_sqlite(self, compiler, connection):
        rhs = self.rhs
        if not rhs:
            raise EmptyResultSet

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a = x1 AND b = y1 AND c = z1) OR (a = x2 AND b = y2 AND c = z2)
        root = WhereNode([], connector=OR)
        lhs = self.lhs

        for vals in rhs:
            lookups = [Exact(col, val) for col, val in zip(lhs, vals)]
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
