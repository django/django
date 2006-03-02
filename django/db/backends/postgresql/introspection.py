from django.db import transaction
from django.db.backends.postgresql.base import quote_name

def get_table_list(cursor):
    "Returns a list of table names in the current database."
    cursor.execute("""
        SELECT c.relname
        FROM pg_catalog.pg_class c
        LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r', 'v', '')
            AND n.nspname NOT IN ('pg_catalog', 'pg_toast')
            AND pg_catalog.pg_table_is_visible(c.oid)""")
    return [row[0] for row in cursor.fetchall()]

def get_table_description(cursor, table_name):
    "Returns a description of the table, with the DB-API cursor.description interface."
    cursor.execute("SELECT * FROM %s LIMIT 1" % quote_name(table_name))
    return cursor.description

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
        try:
            # row[0] and row[1] are like "{2}", so strip the curly braces.
            relations[int(row[0][1:-1]) - 1] = (int(row[1][1:-1]) - 1, row[2])
        except ValueError:
            continue
    return relations

def get_indexes(cursor, table_name):
    """
    Returns a dictionary of fieldname -> infodict for the given table,
    where each infodict is in the format:
        {'primary_key': boolean representing whether it's the primary key,
         'unique': boolean representing whether it's a unique index}
    """
    # Get the table description because we only have the column indexes, and we
    # need the column names.
    desc = get_table_description(cursor, table_name)
    # This query retrieves each index on the given table.
    cursor.execute("""
        SELECT idx.indkey, idx.indisunique, idx.indisprimary
        FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
            pg_catalog.pg_index idx
        WHERE c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND c.relname = %s""", [table_name])
    indexes = {}
    for row in cursor.fetchall():
        # row[0] (idx.indkey) is stored in the DB as an array. It comes out as
        # a string of space-separated integers. This designates the field
        # indexes (1-based) of the fields that have indexes on the table.
        # Here, we skip any indexes across multiple fields.
        if ' ' in row[0]:
            continue
        col_name = desc[int(row[0])-1][0]
        indexes[col_name] = {'primary_key': row[2], 'unique': row[1]}
    return indexes

# Maps type codes to Django Field types.
DATA_TYPES_REVERSE = {
    16: 'BooleanField',
    21: 'SmallIntegerField',
    23: 'IntegerField',
    25: 'TextField',
    869: 'IPAddressField',
    1043: 'CharField',
    1082: 'DateField',
    1083: 'TimeField',
    1114: 'DateTimeField',
    1184: 'DateTimeField',
    1266: 'TimeField',
    1700: 'FloatField',
}
