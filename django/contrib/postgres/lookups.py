from django.db.models import Transform
from django.db.models.lookups import PostgresOperatorLookup

from .search import SearchVector, SearchVectorExact, SearchVectorField


class DataContains(PostgresOperatorLookup):
    lookup_name = 'contains'
    postgres_operator = '@>'


class ContainedBy(PostgresOperatorLookup):
    lookup_name = 'contained_by'
    postgres_operator = '<@'


class Overlap(PostgresOperatorLookup):
    lookup_name = 'overlap'
    postgres_operator = '&&'


class HasKey(PostgresOperatorLookup):
    lookup_name = 'has_key'
    postgres_operator = '?'
    prepare_rhs = False


class HasKeys(PostgresOperatorLookup):
    lookup_name = 'has_keys'
    postgres_operator = '?&'

    def get_prep_lookup(self):
        return [str(item) for item in self.rhs]


class HasAnyKeys(HasKeys):
    lookup_name = 'has_any_keys'
    postgres_operator = '?|'


class Unaccent(Transform):
    bilateral = True
    lookup_name = 'unaccent'
    function = 'UNACCENT'


class SearchLookup(SearchVectorExact):
    lookup_name = 'search'

    def process_lhs(self, qn, connection):
        if not isinstance(self.lhs.output_field, SearchVectorField):
            config = getattr(self.rhs, 'config', None)
            self.lhs = SearchVector(self.lhs, config=config)
        lhs, lhs_params = super().process_lhs(qn, connection)
        return lhs, lhs_params


class TrigramSimilar(PostgresOperatorLookup):
    lookup_name = 'trigram_similar'
    postgres_operator = '%%'
