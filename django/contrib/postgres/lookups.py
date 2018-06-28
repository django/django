from django.db.models import Lookup, Transform
from django.db.models.lookups import Exact

from .search import SearchVector, SearchVectorExact, SearchVectorField


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
    prepare_rhs = False


class HasKeys(PostgresSimpleLookup):
    lookup_name = 'has_keys'
    operator = '?&'

    def get_prep_lookup(self):
        return [str(item) for item in self.rhs]


class HasAnyKeys(HasKeys):
    lookup_name = 'has_any_keys'
    operator = '?|'


class Unaccent(Transform):
    bilateral = True
    lookup_name = 'unaccent'
    function = 'UNACCENT'


class SearchLookup(SearchVectorExact):
    lookup_name = 'search'

    def process_lhs(self, qn, connection):
        if not isinstance(self.lhs.output_field, SearchVectorField):
            self.lhs = SearchVector(self.lhs)
        lhs, lhs_params = super().process_lhs(qn, connection)
        return lhs, lhs_params


class TrigramSimilar(PostgresSimpleLookup):
    lookup_name = 'trigram_similar'
    operator = '%%'


class JSONExact(Exact):
    can_use_none_as_rhs = True

    def process_rhs(self, compiler, connection):
        result = super().process_rhs(compiler, connection)
        # Treat None lookup values as null.
        return ("'null'", []) if result == ('%s', [None]) else result
