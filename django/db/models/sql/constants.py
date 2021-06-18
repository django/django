"""
Constants specific to the SQL storage portion of the ORM.
"""
from django.utils.regex_helper import _lazy_re_compile

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Namedtuples for sql.* internal use.

# How many results to expect from a cursor.execute call
MULTI = 'multi'
SINGLE = 'single'
CURSOR = 'cursor'
NO_RESULTS = 'no results'

ORDER_DIR = {
    'ASC': ('ASC', 'DESC'),
    'DESC': ('DESC', 'ASC'),
}
ORDER_PATTERN = _lazy_re_compile(r'[-+]?[.\w]+$')

# SQL join types.
INNER = 'INNER JOIN'
LOUTER = 'LEFT OUTER JOIN'
