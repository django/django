from django.contrib.postgres.aggregates import PostgresAggregate
from django.contrib.postgres.fields import JSONField

__all__ = [
    'ArrayAgg', 'BitAnd', 'BitOr', 'BoolAnd', 'BoolOr', 'JSONBAgg', 'StringAgg',
]


class ArrayAgg(PostgresAggregate):
    function = 'ARRAY_AGG'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super().__init__(expression, distinct='DISTINCT ' if distinct else '', **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return []
        return value


class BitAnd(PostgresAggregate):
    function = 'BIT_AND'


class BitOr(PostgresAggregate):
    function = 'BIT_OR'


class BoolAnd(PostgresAggregate):
    function = 'BOOL_AND'


class BoolOr(PostgresAggregate):
    function = 'BOOL_OR'


class JSONBAgg(PostgresAggregate):
    function = 'JSONB_AGG'
    _output_field = JSONField()

    def convert_value(self, value, expression, connection, context):
        if not value:
            return []
        return value


class StringAgg(PostgresAggregate):
    function = 'STRING_AGG'
    template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s')"

    def __init__(self, expression, delimiter, distinct=False, **extra):
        distinct = 'DISTINCT ' if distinct else ''
        super().__init__(expression, delimiter=delimiter, distinct=distinct, **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return ''
        return value
