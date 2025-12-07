"""
Constants specific to the SQL storage portion of the ORM.
"""

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Namedtuples for sql.* internal use.

# How many results to expect from a cursor.execute call
MULTI = "multi"
SINGLE = "single"
NO_RESULTS = "no results"
# Rather than returning results, returns:
CURSOR = "cursor"
ROW_COUNT = "row count"

ORDER_DIR = {
    "ASC": ("ASC", "DESC"),
    "DESC": ("DESC", "ASC"),
}

# SQL join types.
INNER = "INNER JOIN"
LOUTER = "LEFT OUTER JOIN"
