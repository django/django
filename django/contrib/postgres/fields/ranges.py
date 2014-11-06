import json

from django.db import models
from django.utils import six

from psycopg2.extras import Range, NumericRange, DateRange, DateTimeTZRange


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
        else:
            return self.range_type(value[0], value[1])

    def to_python(self, value):
        if isinstance(value, six.string_types):
            value = self.range_type(**json.loads(value))
        return value

    def value_to_string(self, obj):
        value = self._get_val_from_obj(obj)
        if value is None:
            return None
        if value.isempty:
            return json.dumps({"empty": True})
        return json.dumps({
            "lower": value.lower,
            "upper": value.upper,
            "bounds": value._bounds,
        })


class IntegerRangeField(RangeField):
    base_field = models.IntegerField()
    range_type = NumericRange

    def db_type(self, connection):
        return 'int4range'


class BigIntegerRangeField(RangeField):
    base_field = models.BigIntegerField()
    range_type = NumericRange

    def db_type(self, connection):
        return 'int8range'


class FloatRangeField(RangeField):
    base_field = models.FloatField()
    range_type = NumericRange

    def db_type(self, connection):
        return 'numrange'


class DateTimeRangeField(RangeField):
    base_field = models.FloatField()
    range_type = DateTimeTZRange

    def db_type(self, connection):
        return 'tstzrange'


class DateRangeField(RangeField):
    base_field = models.FloatField()
    range_type = DateRange

    def db_type(self, connection):
        return 'daterange'
