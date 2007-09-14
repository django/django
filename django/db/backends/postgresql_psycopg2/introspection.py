from django.db.backends.postgresql_psycopg2.base import DatabaseOperations
from django.db.backends.postgresql.introspection import get_table_list, get_table_description, get_indexes, DATA_TYPES_REVERSE

quote_name = DatabaseOperations().quote_name

def get_relations(cursor, table_name):
    """
    Returns a dictionary of {field_index: (field_index_other_table, other_table)}
    representing all relationships to the given table. Indexes are 0-based.
    """
    cursor.execute("""
        SELECT con.conkey, con.confkey, c2.relname
        FROM pg_constraint con, pg_class c1, pg_class c2
        WHERE c1.oid = con.conrelid
            AND c2.oid = con.confrelid
            AND c1.relname = %s
            AND con.contype = 'f'""", [table_name])
    relations = {}
    for row in cursor.fetchall():
        # row[0] and row[1] are single-item lists, so grab the single item.
        relations[row[0][0] - 1] = (row[1][0] - 1, row[2])
    return relations
