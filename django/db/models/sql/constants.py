"""
Constants specific to the SQL storage portion of the ORM.
"""

from collections import namedtuple
import re

# Valid query types (a set is used for speedy lookups). These are (currently)
# considered SQL-specific; other storage systems may choose to use different
# lookup types.
QUERY_TERMS = set([
    'exact', 'iexact', 'contains', 'icontains', 'gt', 'gte', 'lt', 'lte', 'in',
    'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'year',
    'month', 'day', 'week_day', 'isnull', 'search', 'regex', 'iregex',
])

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Constants to make looking up tuple values clearer.
# Join lists (indexes into the tuples that are values in the alias_map
# dictionary in the Query class).
JoinInfo = namedtuple('JoinInfo',
                      'table_name rhs_alias join_type lhs_alias '
                      'lhs_join_col rhs_join_col nullable')

# How many results to expect from a cursor.execute call
MULTI = 'multi'
SINGLE = 'single'

ORDER_PATTERN = re.compile(r'\?|[-+]?[.\w]+$')
ORDER_DIR = {
    'ASC': ('ASC', 'DESC'),
    'DESC': ('DESC', 'ASC'),
}
