from django.db.models.expressions import Expression
from django.db.models.query_utils import Q


class FilterAgg(Expression):
    '''
    Allow generation of PostgreSQL "AGG(expre) FILTER (WHERE ...)"
    '''
    template = '%(agg)s FILTER(WHERE %(condition)s)'
    contains_aggregate = True

    def __init__(self, agg, condition, **extra):
        if not agg.contains_aggregate:
            raise TypeError('First argument to FilterAgg must be an Aggregate')
        if not isinstance(condition, Q):
            raise TypeError('Second argument to FilterAgg must be a Q')

        output_field = extra.pop('output_field', agg.output_field)
        super(FilterAgg, self).__init__(output_field=output_field)

        self.agg = agg
        self.condition = condition

    def __str__(self):
        return '%s FILTER(WHERE %s)' % (self.agg, self.condition)

    def get_source_expressions(self):
        return self.agg, self.condition

    def set_source_expressions(self, exprs):
        self.agg, self.condition = exprs[:2]

    def as_sql(self, compiler, connection, template=None, extra=None):
        agg_sql, agg_params = compiler.compile(self.agg)
        condition_sql, condition_params = compiler.compile(self.condition)

        template = template or self.template
        sql = template % {'agg': agg_sql, 'condition': condition_sql}
        return sql, agg_params + condition_params

    def get_group_by_cols(self):
        return []
