from django.db.models import Lookup, Transform


class PostgresSimpleLookup(Lookup):
    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s %s %s' % (lhs, self.operator, rhs), params


class FunctionTransform(Transform):
    def as_sql(self, qn, connection):
        lhs, params = qn.compile(self.lhs)
        return "%s(%s)" % (self.function, lhs), params


class DataContains(PostgresSimpleLookup):
    lookup_name = 'contains'
    operator = '@>'


class ContainedBy(PostgresSimpleLookup):
    lookup_name = 'contained_by'
    operator = '<@'


class Overlap(PostgresSimpleLookup):
    lookup_name = 'overlap'
    operator = '&&'


class Unaccent(FunctionTransform):
    bilateral = True
    lookup_name = 'unaccent'
    function = 'UNACCENT'
