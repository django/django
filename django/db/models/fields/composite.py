import json
from functools import partial

from django.core import checks
from django.core.exceptions import FieldError
from django.db.models import NOT_PROVIDED, Field
from django.db.models.constants import LOOKUP_SEP
from django.db.models.expressions import ColPairs, CompositeCol
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

    @classmethod
    def from_select(
        cls, select, values_select=None, annotation_select=None, selected=None
    ):
        """
        Builds a CompositeField (possibly nested) from query select exprs.
        """

        def extract_field(value):
            return (
                getattr(value, "target", None)
                or getattr(value, "field", None)
                or getattr(value, "output_field", None)
            )

        select_map = {}
        if selected:
            for path, val in selected.items():
                if isinstance(val, int):
                    field = extract_field(select[val])
                else:
                    field = extract_field(val)
                if field:
                    select_map[path] = field
        else:
            if values_select:
                select_idx = 0
                for path in values_select:
                    if annotation_select and path in annotation_select:
                        field = extract_field(annotation_select[path])
                    elif select_idx < len(select):
                        field = extract_field(select[select_idx])
                        select_idx += 1
                    else:
                        field = None
                    if field:
                        select_map[path] = field
            else:
                for sel in select:
                    field = extract_field(sel)
                    if field:
                        select_map[field.name] = field
            
        if annotation_select:
            select_map.update(
                {
                    key: extract_field(value)
                    for key, value in annotation_select.items()
                    if key not in select_map
                }
            )

        if len(select_map) == 1:
            return next(iter(select_map.values()))

        nested = {}
        for path, field in select_map.items():
            parts = path.split(LOOKUP_SEP)
            current = nested
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = field
        return cls._make_composite(nested)

    @classmethod
    def _make_composite(cls, value):
        if isinstance(value, dict):
            sub_fields = {k: cls._make_composite(v) for k, v in value.items()}
            return cls(**sub_fields)
        return value

    def deconstruct(self):
        """This method taken from base Field class"""
        name, path, _, kwargs = super().deconstruct()
        return name, path, self.sub_fields, kwargs

    def get_field(self, name):
        try:
            return self.sub_fields[name]
        except KeyError:
            raise FieldError(f"{name!r} not found")

    def get_lookup(self, lookup_name):
        return super().get_lookup(lookup_name)

    def get_transform(self, name):
        """This for to work lookups"""
        try:
            subfield = self.get_field(name)
        except FieldError:
            return super().get_transform(name)
        return partial(CompositeCol, lookup_name=name, output_field=subfield)

    def __len__(self):
        return len(self.sub_fields)


CompositeField.register_lookup(TupleExact)
CompositeField.register_lookup(TupleGreaterThan)
CompositeField.register_lookup(TupleGreaterThanOrEqual)
CompositeField.register_lookup(TupleLessThan)
CompositeField.register_lookup(TupleLessThanOrEqual)
CompositeField.register_lookup(TupleIn)
CompositeField.register_lookup(TupleIsNull)
