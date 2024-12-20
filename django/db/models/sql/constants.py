"""
Constants specific to the SQL storage portion of the ORM.
"""

# Size of each "chunk" for get_iterator calls.
# Larger values are slightly faster at the expense of more storage space.
GET_ITERATOR_CHUNK_SIZE = 100

# Namedtuples for sql.* internal use.

# How many results to expect from a cursor.execute call
# multiple rows are expected
MULTI = "multi"
# a single row is expected
SINGLE = "single"
# do not return the rows, instead return the cursor
# used for the query
CURSOR = "cursor"
# instead of returning the rows, return the row count
ROW_COUNT = "row count"
NO_RESULTS = "no results"

ORDER_DIR = {
    "ASC": ("ASC", "DESC"),
    "DESC": ("DESC", "ASC"),
}

# SQL join types.
INNER = "INNER JOIN"
LOUTER = "LEFT OUTER JOIN"
