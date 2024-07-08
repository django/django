import itertools

from django.core import checks
from django.core.exceptions import EmptyResultSet
from django.db.models import NOT_PROVIDED, Expression, Field
from django.db.models.expressions import Col
from django.db.models.fields.related_lookups import (
    RelatedExact,
    RelatedGreaterThan,
    RelatedGreaterThanOrEqual,
    RelatedIn,
    RelatedIsNull,
    RelatedLessThan,
    RelatedLessThanOrEqual,
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
from django.utils.functional import cached_property


class TupleLookupMixin:
    def get_prep_lookup(self):
        self.check_tuple_lookup()
        return super().get_prep_lookup()

    def check_tuple_lookup(self):
        assert isinstance(self.lhs, Cols)
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


class TupleExactMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, WhereNode

        # e.g.: (a, b, c) == (x, y, z) as SQL:
        # WHERE a = x AND b = y AND c = z
        cols = self.lhs.get_source_expressions()
        lookups = [Exact(col, val) for col, val in zip(cols, self.rhs)]

        return compiler.compile(WhereNode(lookups, connector=AND))


class TupleGreaterThanMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, OR, WhereNode

        # e.g.: (a, b, c) > (x, y, z) as SQL:
        # WHERE a > x OR (a = x AND (b > y OR (b = y AND c > z)))
        cols = self.lhs.get_source_expressions()
        lookups = itertools.cycle([GreaterThan, Exact])  # >, =, >, =, ...
        connectors = itertools.cycle([OR, AND])  # OR, AND, OR, AND, ...
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list[:-1])  # a, a, b, b, c
        vals_iter = iter(vals_list[:-1])  # x, x, y, y, z
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return compiler.compile(root)


class TupleGreaterThanOrEqualMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, OR, WhereNode

        # e.g.: (a, b, c) >= (x, y, z) as SQL:
        # WHERE a > x OR (a = x AND (b > y OR (b = y AND (c > z OR c = z))))
        cols = self.lhs.get_source_expressions()
        lookups = itertools.cycle([GreaterThan, Exact])  # >, =, >, =, ...
        connectors = itertools.cycle([OR, AND])  # OR, AND, OR, AND, ...
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list)  # a, a, b, b, c, c
        vals_iter = iter(vals_list)  # x, x, y, y, z, z
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return compiler.compile(root)


class TupleLessThanMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, OR, WhereNode

        # e.g.: (a, b, c) < (x, y, z) as SQL:
        # WHERE a < x OR (a = x AND (b < y OR (b = y AND c < z)))
        cols = self.lhs.get_source_expressions()
        lookups = itertools.cycle([LessThan, Exact])  # <, =, <, =, ...
        connectors = itertools.cycle([OR, AND])  # OR, AND, OR, AND, ...
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list[:-1])  # a, a, b, b, c
        vals_iter = iter(vals_list[:-1])  # x, x, y, y, z
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return compiler.compile(root)


class TupleLessThanOrEqualMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, OR, WhereNode

        # e.g.: (a, b, c) <= (x, y, z) as SQL:
        # WHERE a < x OR (a = x AND (b < y OR (b = y AND (c < z OR c = z))))
        cols = self.lhs.get_source_expressions()
        lookups = itertools.cycle([LessThan, Exact])  # <, =, <, =, ...
        connectors = itertools.cycle([OR, AND])  # OR, AND, OR, AND, ...
        cols_list = [col for col in cols for _ in range(2)]
        vals_list = [val for val in self.rhs for _ in range(2)]
        cols_iter = iter(cols_list)  # a, a, b, b, c, c
        vals_iter = iter(vals_list)  # x, x, y, y, z, z
        col, val = next(cols_iter), next(vals_iter)
        lookup, connector = next(lookups), next(connectors)
        root = node = WhereNode([lookup(col, val)], connector=connector)

        for col, val in zip(cols_iter, vals_iter):
            lookup, connector = next(lookups), next(connectors)
            child = WhereNode([lookup(col, val)], connector=connector)
            node.children.append(child)
            node = child

        return compiler.compile(root)


class TupleInMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, OR, WhereNode

        if not self.rhs:
            raise EmptyResultSet

        # e.g.: (a, b, c) in [(x1, y1, z1), (x2, y2, z2)] as SQL:
        # WHERE (a = x1 AND b = y1 AND c = z1) OR (a = x2 AND b = y2 AND c = z2)
        nodes = []
        cols = self.lhs.get_source_expressions()

        for vals in self.rhs:
            lookups = [Exact(col, val) for col, val in zip(cols, vals)]
            nodes.append(WhereNode(lookups, connector=AND))

        return compiler.compile(WhereNode(nodes, connector=OR))


class TupleIsNullMixin:
    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, WhereNode

        # e.g.: (a, b, c) is None as SQL:
        # WHERE a IS NULL AND b IS NULL AND c IS NULL
        cols = self.lhs.get_source_expressions()
        lookups = [IsNull(col, self.rhs) for col in cols]

        return compiler.compile(WhereNode(lookups, connector=AND))


class TupleExact(TupleLookupMixin, TupleExactMixin, Exact):
    pass


class TupleGreaterThan(TupleLookupMixin, TupleGreaterThanMixin, GreaterThan):
    pass


class TupleGreaterThanOrEqual(
    TupleLookupMixin, TupleGreaterThanOrEqualMixin, GreaterThanOrEqual
):
    pass


class TupleLessThan(TupleLookupMixin, TupleLessThanMixin, LessThan):
    pass


class TupleLessThanOrEqual(
    TupleLookupMixin, TupleLessThanOrEqualMixin, LessThanOrEqual
):
    pass


class TupleIn(TupleLookupMixin, TupleInMixin, In):
    def check_tuple_lookup(self):
        assert isinstance(self.lhs, Cols)
        self.check_rhs_is_tuple_or_list()
        self.check_rhs_is_collection_of_tuples_or_lists()
        self.check_rhs_elements_length_equals_lhs_length()


class TupleIsNull(TupleIsNullMixin, IsNull):
    pass


class TupleRelatedIn(TupleInMixin, RelatedIn):
    pass


class TupleRelatedExact(TupleExactMixin, RelatedExact):
    pass


class TupleRelatedGreaterThan(TupleGreaterThanMixin, RelatedGreaterThan):
    pass


class TupleRelatedGreaterThanOrEqual(
    TupleGreaterThanOrEqualMixin, RelatedGreaterThanOrEqual
):
    pass


class TupleRelatedLessThan(TupleLessThanMixin, RelatedLessThan):
    pass


class TupleRelatedLessThanOrEqual(TupleLessThanOrEqualMixin, RelatedLessThanOrEqual):
    pass


class TupleRelatedIsNull(TupleIsNullMixin, RelatedIsNull):
    pass


class CompositeAttribute:
    def __init__(self, field):
        self.field = field

    @property
    def attnames(self):
        return [field.attname for field in self.field.fields]

    def __get__(self, instance, cls=None):
        return tuple(getattr(instance, attname) for attname in self.attnames)

    def __set__(self, instance, values):
        if values is None:
            values = (None,) * len(self.attnames)

        for field_name, value in zip(self.attnames, values):
            setattr(instance, field_name, value)


class CompositePrimaryKey(Field):
    descriptor_class = CompositeAttribute

    def __init__(self, *args, **kwargs):
        if (
            not args
            or not all(isinstance(field, str) for field in args)
            or len(set(args)) != len(args)
        ):
            raise ValueError("CompositePrimaryKey args must be unique strings.")
        if kwargs.get("db_default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("CompositePrimaryKey cannot have a database default.")
        if kwargs.setdefault("editable", False):
            raise ValueError("CompositePrimaryKey cannot be editable.")
        if not kwargs.setdefault("primary_key", True):
            raise ValueError("CompositePrimaryKey must be a primary key.")
        if not kwargs.setdefault("blank", True):
            raise ValueError("CompositePrimaryKey must be blank.")

        self.field_names = args
        super().__init__(**kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, path, self.field_names, kwargs

    @cached_property
    def fields(self):
        meta = self.model._meta
        return tuple(meta.get_field(field_name) for field_name in self.field_names)

    @cached_property
    def columns(self):
        return tuple(field.column for field in self.fields)

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only=private_only)
        cls._meta.pk = self
        setattr(cls, self.attname, self.descriptor_class(self))

    def get_attname_column(self):
        return self.get_attname(), None

    def __iter__(self):
        return iter(self.fields)

    def __len__(self):
        return len(self.field_names)

    @cached_property
    def cached_col(self):
        return Cols(self.model._meta.db_table, self.fields, self)

    def get_col(self, alias, output_field=None):
        if alias == self.model._meta.db_table and (
            output_field is None or output_field == self
        ):
            return self.cached_col

        return Cols(alias, self.fields, output_field)

    @classmethod
    def is_set(cls, values):
        return all(value is not None for value in values)

    def _check_field_name(self):
        if self.name != "pk":
            return [
                checks.Error(
                    "'CompositePrimaryKey' must be named 'pk'.",
                    obj=self,
                    id="fields.E013",
                )
            ]
        else:
            return []


CompositePrimaryKey.register_lookup(TupleExact)
CompositePrimaryKey.register_lookup(TupleGreaterThan)
CompositePrimaryKey.register_lookup(TupleGreaterThanOrEqual)
CompositePrimaryKey.register_lookup(TupleLessThan)
CompositePrimaryKey.register_lookup(TupleLessThanOrEqual)
CompositePrimaryKey.register_lookup(TupleIn)
CompositePrimaryKey.register_lookup(TupleIsNull)


def unnest_composite_fields(fields):
    result = []

    for field in fields:
        if isinstance(field, CompositePrimaryKey):
            result.extend(field.fields)
        else:
            result.append(field)

    return result


class Cols(Expression):
    def __init__(self, alias, targets, output_field):
        super().__init__(output_field=output_field)
        self.targets, self.alias = targets, alias

    def __len__(self):
        return len(self.targets)

    def get_source_expressions(self):
        return [Col(self.alias, target) for target in self.targets]

    def set_source_expressions(self, exprs):
        assert all(isinstance(expr, Col) for expr in exprs)
        self.targets = [col.target for col in exprs]

    def as_sql(self, compiler, connection):
        cols_sql = []
        cols_params = []
        cols = self.get_source_expressions()

        for col in cols:
            sql, params = col.as_sql(compiler, connection)
            cols_sql.append(sql)
            cols_params.extend(params)

        return ", ".join(cols_sql), cols_params

    def get_lookup(self, lookup_name):
        lookup = super().get_lookup(lookup_name)

        if lookup_name == "in" and lookup is RelatedIn:
            return TupleRelatedIn
        elif lookup_name == "exact" and lookup is RelatedExact:
            return TupleRelatedExact
        elif lookup_name == "lt" and lookup is RelatedLessThan:
            return TupleRelatedLessThan
        elif lookup_name == "lte" and lookup is RelatedLessThanOrEqual:
            return TupleRelatedLessThanOrEqual
        elif lookup_name == "gt" and lookup is RelatedGreaterThan:
            return TupleRelatedGreaterThan
        elif lookup_name == "gte" and lookup is RelatedGreaterThanOrEqual:
            return TupleRelatedGreaterThanOrEqual
        elif lookup_name == "isnull" and lookup is RelatedIsNull:
            return TupleRelatedIsNull

        return lookup

    @staticmethod
    def db_converter(value, *_):
        return (tuple(value),)
