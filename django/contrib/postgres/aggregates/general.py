from django.contrib.postgres.fields import JSONField
from django.db.models.aggregates import Aggregate

__all__ = [
    'ArrayAgg', 'BitAnd', 'BitOr', 'BoolAnd', 'BoolOr', 'JSONBAgg', 'StringAgg',
]


class ArrayAgg(Aggregate):
    function = 'ARRAY_AGG'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super().__init__(expression, distinct='DISTINCT ' if distinct else '', **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return []
        return value
    
    
class ArrayAggFilter(ArrayAgg):
    template = '%(function)s(%(expressions)s) FILTER (WHERE %(conditions)s)'

    def __init__(self, *args, where=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.where = where

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False):
        expr = super().resolve_expression(query, allow_joins, reuse, summarize, for_save)
        expr.where = expr.where.resolve_expression(query, allow_joins, reuse, summarize, False)
        return expr

    # http://cathyreisenwitz.com/wp-content/uploads/2016/01/no.jpg
    # So I kind of have to copy + paste the as_sql implementation here, as you can't access `params` or `data`
    # easily. This works, lets leave it be for now.

    def as_sql(self, compiler, connection, function=None, template=None, arg_joiner=None, **extra_context):
        connection.ops.check_expression_support(self)
        sql_parts = []
        params = []
        for arg in self.source_expressions:
            arg_sql, arg_params = compiler.compile(arg)
            sql_parts.append(arg_sql)
            params.extend(arg_params)
        data = self.extra.copy()
        data.update(**extra_context)
        # Use the first supplied value in this order: the parameter to this
        # method, a value supplied in __init__()'s **extra (the value in
        # `data`), or the value defined on the class.
        if function is not None:
            data['function'] = function
        else:
            data.setdefault('function', self.function)
        template = template or data.get('template', self.template)
        arg_joiner = arg_joiner or data.get('arg_joiner', self.arg_joiner)
        data['expressions'] = data['field'] = arg_joiner.join(sql_parts)

        filter_sql, filter_params = compiler.compile(self.where)

        data['conditions'] = filter_sql
        params.extend(filter_params)
        return template % data, params
    

class BitAnd(Aggregate):
    function = 'BIT_AND'


class BitOr(Aggregate):
    function = 'BIT_OR'


class BoolAnd(Aggregate):
    function = 'BOOL_AND'


class BoolOr(Aggregate):
    function = 'BOOL_OR'


class JSONBAgg(Aggregate):
    function = 'JSONB_AGG'
    _output_field = JSONField()

    def convert_value(self, value, expression, connection, context):
        if not value:
            return []
        return value


class StringAgg(Aggregate):
    function = 'STRING_AGG'
    template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s')"

    def __init__(self, expression, delimiter, distinct=False, **extra):
        distinct = 'DISTINCT ' if distinct else ''
        super().__init__(expression, delimiter=delimiter, distinct=distinct, **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return ''
        return value
