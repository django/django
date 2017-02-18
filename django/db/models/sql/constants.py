"""
Constants specific to the SQL storage portion of the ORM.
"""

import re

# Valid query types (a set is used for speedy lookups). These are (currently)
# considered SQL-specific; other storage systems may choose to use different
# lookup types.
QUERY_TERMS = {
    'exact', 'iexact', 'contains', 'icontains', 'gt', 'gte', 'lt', 'lte', 'in',
    'startswith', 'istartswith', 'endswith', 'iendswith', 'range', 'year',
    'month', 'day', 'week_day', 'hour', 'minute', 'second', 'isnull', 'search',
    'regex', 'iregex',
}

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Namedtuples for sql.* internal use.

# How many results to expect from a cursor.execute call
MULTI = 'multi'
SINGLE = 'single'
CURSOR = 'cursor'
NO_RESULTS = 'no results'

ORDER_PATTERN = re.compile(r'\?|[-+]?[.\w]+$')
ORDER_DIR = {
    'ASC': ('ASC', 'DESC'),
    'DESC': ('DESC', 'ASC'),
}

# SQL join types.
INNER = 'INNER JOIN'
LOUTER = 'LEFT OUTER JOIN'
