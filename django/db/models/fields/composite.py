from collections.abc import Iterable

from django.db.models import Field
from django.db.models.expressions import Col, Expression
from django.db.models.lookups import Exact, In
from django.db.models.signals import class_prepared
from django.utils.functional import cached_property


class TupleExact(Exact):
    def get_prep_lookup(self):
        if not isinstance(self.lhs, Cols):
            raise ValueError(
                "The left-hand side of TupleExact lookups must be an instance of Cols"
            )
        if not isinstance(self.rhs, Iterable):
            raise ValueError(
                "The right-hand side of TupleExact lookups must be an iterable"
            )
        if len(list(self.lhs)) != len(list(self.rhs)):
            raise ValueError(
                "The left-hand side and right-hand side of TupleExact lookups must "
                "have the same number of elements"
            )

        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, WhereNode

        cols = self.lhs.get_source_expressions()
        exprs = [Exact(col, val) for col, val in zip(cols, self.rhs)]

        return compiler.compile(WhereNode(exprs, connector=AND))


class TupleIn(In):
    def get_prep_lookup(self):
        if not isinstance(self.lhs, Cols):
            raise ValueError(
                "The left-hand side of TupleIn lookups must be an instance of Cols"
            )
        if not isinstance(self.rhs, Iterable):
            raise ValueError(
                "The right-hand side of TupleIn lookups must be an iterable"
            )
        if not all(isinstance(vals, Iterable) for vals in self.rhs):
            raise ValueError(
                "The right-hand side of TupleIn lookups must be an iterable of "
                "iterables"
            )
        lhs_len = len(list(self.lhs))
        if not all(lhs_len == len(list(vals)) for vals in self.rhs):
            raise ValueError(
                "The left-hand side and right-hand side of TupleIn lookups must "
                "have the same number of elements"
            )

        return super().get_prep_lookup()

    def as_sql(self, compiler, connection):
        from django.db.models.sql.where import AND, OR, WhereNode

        exprs = []
        cols = self.lhs.get_source_expressions()

        for vals in self.rhs:
            exprs.append(
                WhereNode(
                    [Exact(col, val) for col, val in zip(cols, vals)], connector=AND
                )
            )

        return compiler.compile(WhereNode(exprs, connector=OR))


class Cols(Expression):
    def __init__(self, alias, targets, output_field):
        super().__init__(output_field=output_field)
        self.alias, self.targets = alias, targets

    def get_source_expressions(self):
        return [Col(self.alias, target) for target in self.targets]

    def set_source_expressions(self, exprs):
        assert all(isinstance(expr, Col) for expr in exprs)
        assert len(exprs) == len(self.targets)

    def as_sql(self, compiler, connection):
        sqls = []
        cols = self.get_source_expressions()

        for col in cols:
            sql, _ = col.as_sql(compiler, connection)
            sqls.append(sql)

        return ", ".join(sqls), []

    def __iter__(self):
        return iter(self.get_source_expressions())


class CompositeAttribute:
    def __init__(self, field):
        self.field = field

    def __get__(self, instance, cls=None):
        return tuple(
            getattr(instance, field_name) for field_name in self.field.field_names
        )

    def __set__(self, instance, values):
        for field_name, value in zip(self.field.field_names, values):
            setattr(instance, field_name, value)


class CompositeField(Field):
    descriptor_class = CompositeAttribute

    def __init__(self, *args, **kwargs):
        kwargs["db_column"] = None
        kwargs["editable"] = False
        super().__init__(**kwargs)
        self.field_names = args
        self.fields = None

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only)
        cls._meta.pk = self
        setattr(cls, self.attname, self.descriptor_class(self))

    def get_attname_column(self):
        return self.get_attname(), self.db_column

    def __iter__(self):
        return iter(self.fields)

    @cached_property
    def cached_col(self):
        return Cols(self.model._meta.db_table, self.fields, self)

    def get_lookup(self, lookup_name):
        if lookup_name == "exact":
            return TupleExact
        elif lookup_name == "in":
            return TupleIn

        return super().get_lookup(lookup_name)


def resolve_columns(*args, **kwargs):
    cls = kwargs.pop("sender")
    for field in cls._meta.local_fields:
        if isinstance(field, CompositeField) and field.fields is None:
            field.fields = tuple(
                cls._meta.get_field(name) for name in field.field_names
            )


class_prepared.connect(resolve_columns)
