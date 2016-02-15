import json

from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange, Range

from django.contrib.postgres import forms, lookups
from django.db import models
from django.utils import six

from .utils import AttributeSetter

__all__ = [
    'RangeField', 'IntegerRangeField', 'BigIntegerRangeField',
    'FloatRangeField', 'DateTimeRangeField', 'DateRangeField',
]


class RangeField(models.Field):
    empty_strings_allowed = False

    def get_prep_value(self, value):
        if value is None:
            return None
        elif isinstance(value, Range):
            return value
        elif isinstance(value, (list, tuple)):
            return self.range_type(value[0], value[1])
        return value

    def to_python(self, value):
        if isinstance(value, six.string_types):
            # Assume we're deserializing
            vals = json.loads(value)
            for end in ('lower', 'upper'):
                if end in vals:
                    vals[end] = self.base_field.to_python(vals[end])
            value = self.range_type(**vals)
        elif isinstance(value, (list, tuple)):
            value = self.range_type(value[0], value[1])
        return value

    def set_attributes_from_name(self, name):
        super(RangeField, self).set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        if value is None:
            return None
        if value.isempty:
            return json.dumps({"empty": True})
        base_field = self.base_field
        result = {"bounds": value._bounds}
        for end in ('lower', 'upper'):
            val = getattr(value, end)
            if val is None:
                result[end] = None
            else:
                obj = AttributeSetter(base_field.attname, val)
                result[end] = base_field.value_to_string(obj)
        return json.dumps(result)

    def formfield(self, **kwargs):
        kwargs.setdefault('form_class', self.form_field)
        return super(RangeField, self).formfield(**kwargs)


class IntegerRangeField(RangeField):
    base_field = models.IntegerField()
    range_type = NumericRange
    form_field = forms.IntegerRangeField

    def db_type(self, connection):
        return 'int4range'


class BigIntegerRangeField(RangeField):
    base_field = models.BigIntegerField()
    range_type = NumericRange
    form_field = forms.IntegerRangeField

    def db_type(self, connection):
        return 'int8range'


class FloatRangeField(RangeField):
    base_field = models.FloatField()
    range_type = NumericRange
    form_field = forms.FloatRangeField

    def db_type(self, connection):
        return 'numrange'


class DateTimeRangeField(RangeField):
    base_field = models.DateTimeField()
    range_type = DateTimeTZRange
    form_field = forms.DateTimeRangeField

    def db_type(self, connection):
        return 'tstzrange'


class DateRangeField(RangeField):
    base_field = models.DateField()
    range_type = DateRange
    form_field = forms.DateRangeField

    def db_type(self, connection):
        return 'daterange'


RangeField.register_lookup(lookups.DataContains)
RangeField.register_lookup(lookups.ContainedBy)
RangeField.register_lookup(lookups.Overlap)


@RangeField.register_lookup
class FullyLessThan(lookups.PostgresSimpleLookup):
    lookup_name = 'fully_lt'
    operator = '<<'


@RangeField.register_lookup
class FullGreaterThan(lookups.PostgresSimpleLookup):
    lookup_name = 'fully_gt'
    operator = '>>'


@RangeField.register_lookup
class NotLessThan(lookups.PostgresSimpleLookup):
    lookup_name = 'not_lt'
    operator = '&>'


@RangeField.register_lookup
class NotGreaterThan(lookups.PostgresSimpleLookup):
    lookup_name = 'not_gt'
    operator = '&<'


@RangeField.register_lookup
class AdjacentToLookup(lookups.PostgresSimpleLookup):
    lookup_name = 'adjacent_to'
    operator = '-|-'


@RangeField.register_lookup
class RangeStartsWith(lookups.FunctionTransform):
    lookup_name = 'startswith'
    function = 'lower'

    @property
    def output_field(self):
        return self.lhs.output_field.base_field


@RangeField.register_lookup
class RangeEndsWith(lookups.FunctionTransform):
    lookup_name = 'endswith'
    function = 'upper'

    @property
    def output_field(self):
        return self.lhs.output_field.base_field


@RangeField.register_lookup
class IsEmpty(lookups.FunctionTransform):
    lookup_name = 'isempty'
    function = 'isempty'
    output_field = models.BooleanField()
