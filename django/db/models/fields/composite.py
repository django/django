from django.core import checks
from django.db.models import NOT_PROVIDED, Field
from django.db.models.expressions import Cols
from django.db.models.fields.tuple_lookups import (
    TupleExact,
    TupleGreaterThan,
    TupleGreaterThanOrEqual,
    TupleIn,
    TupleIsNull,
    TupleLessThan,
    TupleLessThanOrEqual,
)
from django.utils.functional import cached_property


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
        return Cols(self.model._meta.db_table, self.fields, self.fields, self)

    def get_col(self, alias, output_field=None):
        if alias == self.model._meta.db_table and (
            output_field is None or output_field == self
        ):
            return self.cached_col

        return Cols(alias, self.fields, self.fields, output_field)

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
