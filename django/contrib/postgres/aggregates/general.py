from django.contrib.postgres.fields import JSONField
from django.db.models.aggregates import Aggregate, DistinctAggregate

__all__ = [
    'ArrayAgg', 'BitAnd', 'BitOr', 'BoolAnd', 'BoolOr', 'JSONBAgg', 'StringAgg',
]


class ArrayAgg(DistinctAggregate):
    function = 'ARRAY_AGG'

    def convert_value(self, value, expression, connection, context):
        if not value:
            return []
        return value


class BitAnd(Aggregate):
    function = 'BIT_AND'


class BitOr(Aggregate):
    function = 'BIT_OR'


class BoolAnd(Aggregate):
    function = 'BOOL_AND'


class BoolOr(Aggregate):
    function = 'BOOL_OR'


class JSONBAgg(DistinctAggregate):
    function = 'JSONB_AGG'
    _output_field = JSONField()

    def convert_value(self, value, expression, connection, context):
        if not value:
            return []
        return value


class StringAgg(DistinctAggregate):
    function = 'STRING_AGG'
    template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s')"

    def __init__(self, expression, delimiter, **extra):
        super().__init__(expression, delimiter=delimiter, **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return ''
        return value
