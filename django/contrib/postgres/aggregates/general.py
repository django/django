from django.db.models.aggregates import Aggregate

__all__ = [
    'ArrayAgg', 'BitAnd', 'BitOr', 'BoolAnd', 'BoolOr', 'StringAgg',
]


class OrderableAgg(Aggregate):
    template = "%(function)s(%(expressions)s %(ordering)s)"

    def __init__(self, expression, ordering=None, **extra):
        super(OrderableAgg, self).__init__(
            expression,
            ordering=ordering,
            **extra
        )

    def resolve_expression(self, query=None, allow_joins=True, reuse=None, summarize=False,
                           for_save=False):
        # resolve the ordering if it's there
        ordering = self.extra.pop('ordering', None)
        if ordering is not None:
            parsed_ordering = self._parse_expressions(ordering)[0]
            resolved_ordering = parsed_ordering.resolve_expression(query, allow_joins, reuse,
                                                                   summarize)

            self.extra['ordering'] = resolved_ordering

        return super(OrderableAgg, self).resolve_expression(query, allow_joins, reuse, summarize,
                                                            for_save)

    def as_sql(self, compiler, connection):
        # turn ordering parameter to ORDER BY sql clause
        if 'ordering' in self.extra:
            sqled_ordering, _ = self.extra['ordering'].as_sql(compiler, connection)
            self.extra['ordering'] = 'ORDER BY ' + sqled_ordering
        else:
            self.extra['ordering'] = ''

        (formatted, params) = super(OrderableAgg, self).as_sql(compiler, connection)
        return (formatted, params)


class ArrayAgg(OrderableAgg):
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


class StringAgg(OrderableAgg):
    function = 'STRING_AGG'
    template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s'%(ordering)s)"

    def __init__(self, expression, delimiter, distinct=False, **extra):
        distinct = 'DISTINCT ' if distinct else ''
        super(StringAgg, self).__init__(expression, delimiter=delimiter, distinct=distinct, **extra)

    def convert_value(self, value, expression, connection, context):
        if not value:
            return ''
        return value
