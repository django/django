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

    def get_db_prep_lookup(self, lookup_type, value, connection, prepared=False):
        if lookup_type == 'contains':
            return [self.get_prep_value(value)]
        return super(RangeField, self).get_db_prep_lookup(lookup_type, value,
                connection, prepared=False)

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


@RangeField.register_lookup
class RangeContainsLookup(models.Lookup):
    lookup_name = 'contains'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s @> %s' % (lhs, rhs), params


@RangeField.register_lookup
class RangeContainedByLookup(models.Lookup):
    lookup_name = 'contained_by'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s <@ %s' % (lhs, rhs), params


@RangeField.register_lookup
class RangeOverlapLookup(models.Lookup):
    lookup_name = 'overlap'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s && %s' % (lhs, rhs), params


@RangeField.register_lookup
class FullyLessThanLookup(models.Lookup):
    lookup_name = 'fully_lt'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s << %s' % (lhs, rhs), params


@RangeField.register_lookup
class FullGreaterThanLookup(models.Lookup):
    lookup_name = 'fully_gt'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s >> %s' % (lhs, rhs), params


@RangeField.register_lookup
class NotLessThanLookup(models.Lookup):
    lookup_name = 'not_lt'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s &> %s' % (lhs, rhs), params


@RangeField.register_lookup
class NotGreaterThanLookup(models.Lookup):
    lookup_name = 'not_gt'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s &< %s' % (lhs, rhs), params


@RangeField.register_lookup
class AdjacentToLookup(models.Lookup):
    lookup_name = 'adjacent_to'

    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s -|- %s' % (lhs, rhs), params


@RangeField.register_lookup
class RangeStartsWithTransform(models.Transform):
    lookup_name = 'startswith'

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return "lower(%s)" % lhs, params


@RangeField.register_lookup
class RangeEndsWithTransform(models.Transform):
    lookup_name = 'endswith'

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return "upper(%s)" % lhs, params


@RangeField.register_lookup
class RangeIsEmptyTransform(models.Transform):
    lookup_name = 'isempty'
    output_type = models.BooleanField()

    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return "isempty(%s)" % lhs, params
