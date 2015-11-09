from django.db.models import Lookup, Transform
from django.db.models.lookups import Exact, IsNull


class PostgresSimpleLookup(Lookup):
    def as_sql(self, qn, connection):
        lhs, lhs_params = self.process_lhs(qn, connection)
        rhs, rhs_params = self.process_rhs(qn, connection)
        params = lhs_params + rhs_params
        return '%s %s %s' % (lhs, self.operator, rhs), params


class DataContains(PostgresSimpleLookup):
    lookup_name = 'contains'
    operator = '@>'


class ContainedBy(PostgresSimpleLookup):
    lookup_name = 'contained_by'
    operator = '<@'


class Overlap(PostgresSimpleLookup):
    lookup_name = 'overlap'
    operator = '&&'


class HasKey(PostgresSimpleLookup):
    lookup_name = 'has_key'
    operator = '?'


class HasKeys(PostgresSimpleLookup):
    lookup_name = 'has_keys'
    operator = '?&'


class HasAnyKeys(PostgresSimpleLookup):
    lookup_name = 'has_any_keys'
    operator = '?|'


class Unaccent(Transform):
    bilateral = True
    lookup_name = 'unaccent'
    function = 'UNACCENT'


class JSONIsNull(IsNull):

    def as_sql(self, compiler, connection):
        if isinstance(self.lhs, Transform):
            sql, params = compiler.compile(self.lhs)
            if self.rhs:
                return "%s = 'null'" % sql, params
            else:
                return "%s != 'null'" % sql, params
        else:
            return super(JSONIsNull, self).as_sql(compiler, connection)


class JSONExact(Exact):

    def process_rhs(self, compiler, connection):
        result = super(JSONExact, self).process_rhs(compiler, connection)
        if result == ('%s', [None]):
            return "'null'", []
        return result
