from django.db.models.sql.constants import QUERY_TERMS

GIS_LOOKUPS = {
    'bbcontains', 'bboverlaps', 'contained', 'contains',
    'contains_properly', 'coveredby', 'covers', 'crosses', 'disjoint',
    'distance_gt', 'distance_gte', 'distance_lt', 'distance_lte',
    'dwithin', 'equals', 'exact',
    'intersects', 'overlaps', 'relate', 'same_as', 'touches', 'within',
    'left', 'right', 'overlaps_left', 'overlaps_right',
    'overlaps_above', 'overlaps_below',
    'strictly_above', 'strictly_below'
}
ALL_TERMS = GIS_LOOKUPS | QUERY_TERMS

__all__ = ['ALL_TERMS', 'GIS_LOOKUPS']
