from django.db.models import Lookup, Transform


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
