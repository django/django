import datetime
import json

from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange, Range

from django.contrib.postgres import forms, lookups
from django.db import models
from django.db.models.lookups import PostgresOperatorLookup

from .utils import AttributeSetter

__all__ = [
    'RangeField', 'IntegerRangeField', 'BigIntegerRangeField',
    'DecimalRangeField', 'DateTimeRangeField', 'DateRangeField',
    'RangeBoundary', 'RangeOperators',
]


class RangeBoundary(models.Expression):
    """A class that represents range boundaries."""
    def __init__(self, inclusive_lower=True, inclusive_upper=False):
        self.lower = '[' if inclusive_lower else '('
        self.upper = ']' if inclusive_upper else ')'

    def as_sql(self, compiler, connection):
        return "'%s%s'" % (self.lower, self.upper), []


class RangeOperators:
    # https://www.postgresql.org/docs/current/functions-range.html#RANGE-OPERATORS-TABLE
    EQUAL = '='
    NOT_EQUAL = '<>'
    CONTAINS = '@>'
    CONTAINED_BY = '<@'
    OVERLAPS = '&&'
    FULLY_LT = '<<'
    FULLY_GT = '>>'
    NOT_LT = '&>'
    NOT_GT = '&<'
    ADJACENT_TO = '-|-'


class RangeField(models.Field):
    empty_strings_allowed = False

    def __init__(self, *args, **kwargs):
        # Initializing base_field here ensures that its model matches the model for self.
        if hasattr(self, 'base_field'):
            self.base_field = self.base_field()
        super().__init__(*args, **kwargs)

    @property
    def model(self):
        try:
            return self.__dict__['model']
        except KeyError:
            raise AttributeError("'%s' object has no attribute 'model'" % self.__class__.__name__)

    @model.setter
    def model(self, model):
        self.__dict__['model'] = model
        self.base_field.model = model

    @classmethod
    def _choices_is_value(cls, value):
        return isinstance(value, (list, tuple)) or super()._choices_is_value(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        elif isinstance(value, Range):
            return value
        elif isinstance(value, (list, tuple)):
            return self.range_type(value[0], value[1])
        return value

    def to_python(self, value):
        if isinstance(value, str):
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
        super().set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
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
        return super().formfield(**kwargs)


class IntegerRangeField(RangeField):
    base_field = models.IntegerField
    range_type = NumericRange
    form_field = forms.IntegerRangeField

    def db_type(self, connection):
        return 'int4range'


class BigIntegerRangeField(RangeField):
    base_field = models.BigIntegerField
    range_type = NumericRange
    form_field = forms.IntegerRangeField

    def db_type(self, connection):
        return 'int8range'


class DecimalRangeField(RangeField):
    base_field = models.DecimalField
    range_type = NumericRange
    form_field = forms.DecimalRangeField

    def db_type(self, connection):
        return 'numrange'


class DateTimeRangeField(RangeField):
    base_field = models.DateTimeField
    range_type = DateTimeTZRange
    form_field = forms.DateTimeRangeField

    def db_type(self, connection):
        return 'tstzrange'


class DateRangeField(RangeField):
    base_field = models.DateField
    range_type = DateRange
    form_field = forms.DateRangeField

    def db_type(self, connection):
        return 'daterange'


RangeField.register_lookup(lookups.DataContains)
RangeField.register_lookup(lookups.ContainedBy)
RangeField.register_lookup(lookups.Overlap)


class DateTimeRangeContains(PostgresOperatorLookup):
    """
    Lookup for Date/DateTimeRange containment to cast the rhs to the correct
    type.
    """
    lookup_name = 'contains'
    postgres_operator = RangeOperators.CONTAINS

    def process_rhs(self, compiler, connection):
        # Transform rhs value for db lookup.
        if isinstance(self.rhs, datetime.date):
            value = models.Value(self.rhs)
            self.rhs = value.resolve_expression(compiler.query)
        return super().process_rhs(compiler, connection)

    def as_postgresql(self, compiler, connection):
        sql, params = super().as_postgresql(compiler, connection)
        # Cast the rhs if needed.
        cast_sql = ''
        if (
            isinstance(self.rhs, models.Expression) and
            self.rhs._output_field_or_none and
            # Skip cast if rhs has a matching range type.
            not isinstance(self.rhs._output_field_or_none, self.lhs.output_field.__class__)
        ):
            cast_internal_type = self.lhs.output_field.base_field.get_internal_type()
            cast_sql = '::{}'.format(connection.data_types.get(cast_internal_type))
        return '%s%s' % (sql, cast_sql), params


DateRangeField.register_lookup(DateTimeRangeContains)
DateTimeRangeField.register_lookup(DateTimeRangeContains)


class RangeContainedBy(PostgresOperatorLookup):
    lookup_name = 'contained_by'
    type_mapping = {
        'smallint': 'int4range',
        'integer': 'int4range',
        'bigint': 'int8range',
        'double precision': 'numrange',
        'numeric': 'numrange',
        'date': 'daterange',
        'timestamp with time zone': 'tstzrange',
    }
    postgres_operator = RangeOperators.CONTAINED_BY

    def process_rhs(self, compiler, connection):
        rhs, rhs_params = super().process_rhs(compiler, connection)
        # Ignore precision for DecimalFields.
        db_type = self.lhs.output_field.cast_db_type(connection).split('(')[0]
        cast_type = self.type_mapping[db_type]
        return '%s::%s' % (rhs, cast_type), rhs_params

    def process_lhs(self, compiler, connection):
        lhs, lhs_params = super().process_lhs(compiler, connection)
        if isinstance(self.lhs.output_field, models.FloatField):
            lhs = '%s::numeric' % lhs
        elif isinstance(self.lhs.output_field, models.SmallIntegerField):
            lhs = '%s::integer' % lhs
        return lhs, lhs_params

    def get_prep_lookup(self):
        return RangeField().get_prep_value(self.rhs)


models.DateField.register_lookup(RangeContainedBy)
models.DateTimeField.register_lookup(RangeContainedBy)
models.IntegerField.register_lookup(RangeContainedBy)
models.FloatField.register_lookup(RangeContainedBy)
models.DecimalField.register_lookup(RangeContainedBy)


@RangeField.register_lookup
class FullyLessThan(PostgresOperatorLookup):
    lookup_name = 'fully_lt'
    postgres_operator = RangeOperators.FULLY_LT


@RangeField.register_lookup
class FullGreaterThan(PostgresOperatorLookup):
    lookup_name = 'fully_gt'
    postgres_operator = RangeOperators.FULLY_GT


@RangeField.register_lookup
class NotLessThan(PostgresOperatorLookup):
    lookup_name = 'not_lt'
    postgres_operator = RangeOperators.NOT_LT


@RangeField.register_lookup
class NotGreaterThan(PostgresOperatorLookup):
    lookup_name = 'not_gt'
    postgres_operator = RangeOperators.NOT_GT


@RangeField.register_lookup
class AdjacentToLookup(PostgresOperatorLookup):
    lookup_name = 'adjacent_to'
    postgres_operator = RangeOperators.ADJACENT_TO


@RangeField.register_lookup
class RangeStartsWith(models.Transform):
    lookup_name = 'startswith'
    function = 'lower'

    @property
    def output_field(self):
        return self.lhs.output_field.base_field


@RangeField.register_lookup
class RangeEndsWith(models.Transform):
    lookup_name = 'endswith'
    function = 'upper'

    @property
    def output_field(self):
        return self.lhs.output_field.base_field


@RangeField.register_lookup
class IsEmpty(models.Transform):
    lookup_name = 'isempty'
    function = 'isempty'
    output_field = models.BooleanField()


@RangeField.register_lookup
class LowerInclusive(models.Transform):
    lookup_name = 'lower_inc'
    function = 'LOWER_INC'
    output_field = models.BooleanField()


@RangeField.register_lookup
class LowerInfinite(models.Transform):
    lookup_name = 'lower_inf'
    function = 'LOWER_INF'
    output_field = models.BooleanField()


@RangeField.register_lookup
class UpperInclusive(models.Transform):
    lookup_name = 'upper_inc'
    function = 'UPPER_INC'
    output_field = models.BooleanField()


@RangeField.register_lookup
class UpperInfinite(models.Transform):
    lookup_name = 'upper_inf'
    function = 'UPPER_INF'
    output_field = models.BooleanField()
