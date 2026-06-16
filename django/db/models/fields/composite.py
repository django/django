import json
from functools import partial

from django.core import checks
from django.core.exceptions import FieldError
from django.db.models import NOT_PROVIDED, Field
from django.db.models.expressions import ColPairs
from django.db.models.fields.tuple_lookups import (
    TupleExact,
    TupleGreaterThan,
    TupleGreaterThanOrEqual,
    TupleIn,
    TupleIsNull,
    TupleLessThan,
    TupleLessThanOrEqual,
)
from django.db.models.lookups import Transform
from django.utils.functional import cached_property


class AttributeSetter:
    def __init__(self, name, value):
        setattr(self, name, value)


class CompositeAttribute:
    def __init__(self, field):
        self.field = field

    @property
    def attnames(self):
        return [field.attname for field in self.field.fields]

    def __get__(self, instance, cls=None):
        return tuple(getattr(instance, attname) for attname in self.attnames)

    def __set__(self, instance, values):
        attnames = self.attnames
        length = len(attnames)

        if values is None:
            values = (None,) * length

        if not isinstance(values, (list, tuple)):
            raise ValueError(f"{self.field.name!r} must be a list or a tuple.")
        if length != len(values):
            raise ValueError(f"{self.field.name!r} must have {length} elements.")

        for attname, value in zip(attnames, values):
            setattr(instance, attname, value)


class CompositePrimaryKey(Field):
    descriptor_class = CompositeAttribute

    def __init__(self, *args, **kwargs):
        if (
            not args
            or not all(isinstance(field, str) for field in args)
            or len(set(args)) != len(args)
        ):
            raise ValueError("CompositePrimaryKey args must be unique strings.")
        if len(args) == 1:
            raise ValueError("CompositePrimaryKey must include at least two fields.")
        if kwargs.get("default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("CompositePrimaryKey cannot have a default.")
        if kwargs.get("db_default", NOT_PROVIDED) is not NOT_PROVIDED:
            raise ValueError("CompositePrimaryKey cannot have a database default.")
        if kwargs.get("db_column", None) is not None:
            raise ValueError("CompositePrimaryKey cannot have a db_column.")
        if kwargs.setdefault("editable", False):
            raise ValueError("CompositePrimaryKey cannot be editable.")
        if not kwargs.setdefault("primary_key", True):
            raise ValueError("CompositePrimaryKey must be a primary key.")
        if not kwargs.setdefault("blank", True):
            raise ValueError("CompositePrimaryKey must be blank.")

        self.field_names = args
        super().__init__(**kwargs)

    def deconstruct(self):
        # args is always [] so it can be ignored.
        name, path, _, kwargs = super().deconstruct()
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
        return ColPairs(self.model._meta.db_table, self.fields, self.fields, self)

    def get_col(self, alias, output_field=None):
        if alias == self.model._meta.db_table and (
            output_field is None or output_field == self
        ):
            return self.cached_col

        return ColPairs(alias, self.fields, self.fields, output_field)

    def get_pk_value_on_save(self, instance):
        values = []

        for field in self.fields:
            value = field.value_from_object(instance)
            if value is None:
                value = field.get_pk_value_on_save(instance)
            values.append(value)

        return tuple(values)

    def _check_field_name(self):
        if self.name == "pk":
            return []
        return [
            checks.Error(
                "'CompositePrimaryKey' must be named 'pk'.",
                obj=self,
                id="fields.E013",
            )
        ]

    def value_to_string(self, obj):
        values = []
        vals = self.value_from_object(obj)
        for field, value in zip(self.fields, vals):
            obj = AttributeSetter(field.attname, value)
            values.append(field.value_to_string(obj))
        return json.dumps(values, ensure_ascii=False)

    def to_python(self, value):
        if isinstance(value, str):
            # Assume we're deserializing.
            vals = json.loads(value)
            value = [
                field.to_python(val)
                for field, val in zip(self.fields, vals, strict=True)
            ]
        return value


CompositePrimaryKey.register_lookup(TupleExact)
CompositePrimaryKey.register_lookup(TupleGreaterThan)
CompositePrimaryKey.register_lookup(TupleGreaterThanOrEqual)
CompositePrimaryKey.register_lookup(TupleLessThan)
CompositePrimaryKey.register_lookup(TupleLessThanOrEqual)
CompositePrimaryKey.register_lookup(TupleIn)
CompositePrimaryKey.register_lookup(TupleIsNull)


def unnest(fields):
    result = []

    for field in fields:
        if isinstance(field, CompositePrimaryKey):
            result.extend(field.fields)
        else:
            result.append(field)

    return result


class CompositeSubfieldTransform(Transform):
    def __init__(self, expression, lookup_name, output_field, **kwargs):
        super().__init__(expression, **kwargs)
        self.lookup_name = lookup_name
        self._output_field = output_field

    @property
    def output_field(self):
        return self._output_field

    def as_sql(self, compiler, connection):
        """
        Render a reference to a sub-column of a composite table expression.
        """
        current_lhs = self.lhs
        parts = [self.lookup_name]

        while isinstance(current_lhs, CompositeSubfieldTransform):
            parts.insert(0, current_lhs.lookup_name)
            current_lhs = current_lhs.lhs
        full_lookup_name = "__".join(parts)

        if (
            hasattr(current_lhs, "alias")
            and current_lhs.alias
            and current_lhs.alias in compiler.query.alias_map
        ):
            table_alias = current_lhs.alias
            quoted_table = compiler.quote_name(table_alias)
            quoted_column = compiler.quote_name(full_lookup_name)
            return f"{quoted_table}.{quoted_column}", []
        elif hasattr(current_lhs, "refs"):
            table_alias = current_lhs.refs
            quoted_table = compiler.quote_name(table_alias)
            quoted_column = compiler.quote_name(full_lookup_name)
            return f"{quoted_table}.{quoted_column}", []
        elif getattr(current_lhs, "subquery", False) and hasattr(current_lhs, "query"):
            query = current_lhs.query.clone()
            query.set_values([full_lookup_name])
            return query.as_sql(compiler, connection)
        elif isinstance(current_lhs, type(compiler.query)):
            query = current_lhs.clone()
            query.set_values([full_lookup_name])
            return query.as_sql(compiler, connection)
        else:
            raise FieldError("Cannot resolve table alias for composite field. ")


class CompositeField(Field):
    is_composite = True

    def __init__(self, **kwargs):
        self.sub_fields = {}
        if len(kwargs) == 0:
            raise ValueError("At least one fields should be there")
        for name, field in kwargs.items():
            if not isinstance(field, Field):
                raise TypeError(
                    f"{name!r} should field instance"
                )  # this message could enhance later

            self.sub_fields[name] = field
        super().__init__()

    def deconstruct(self):
        """This method taken from base Field class"""
        name, path, _, kwargs = super().deconstruct()
        return name, path, self.sub_fields, kwargs

    def get_field(self, name):
        if name not in self.sub_fields:
            raise FieldError(f"{name!r} not found")
        return self.sub_fields[name]

    def get_transform(self, name):
        """This for to work lookups"""
        try:
            subfield = self.get_field(name)
        except FieldError:
            return super().get_transform(name)
        return partial(
            CompositeSubfieldTransform, lookup_name=name, output_field=subfield
        )
