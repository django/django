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
    # This query retrieves each index on the given table, including the
    # first associated field name
    cursor.execute("""
        SELECT attr.attname, idx.indkey, idx.indisunique, idx.indisprimary
        FROM pg_catalog.pg_class c, pg_catalog.pg_class c2,
            pg_catalog.pg_index idx, pg_catalog.pg_attribute attr
        WHERE c.oid = idx.indrelid
            AND idx.indexrelid = c2.oid
            AND attr.attrelid = c.oid
            AND attr.attnum = idx.indkey[0]
            AND c.relname = %s""", [table_name])
    indexes = {}
    for row in cursor.fetchall():
        # row[1] (idx.indkey) is stored in the DB as an array. It comes out as
        # a string of space-separated integers. This designates the field
        # indexes (1-based) of the fields that have indexes on the table.
        # Here, we skip any indexes across multiple fields.
        if ' ' in row[1]:
            continue
        indexes[row[0]] = {'primary_key': row[3], 'unique': row[2]}
    return indexes

def get_columns(cursor, table_name):
    try:
        cursor.execute("SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod), (SELECT substring(d.adsrc for 128) FROM pg_catalog.pg_attrdef d WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef), a.attnotnull, a.attnum, pg_catalog.col_description(a.attrelid, a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid = (SELECT c.oid from pg_catalog.pg_class c where c.relname ~ '^%s$') AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum" % table_name)
        return [row[0] for row in cursor.fetchall()]
    except:
        return []
    
def get_known_column_flags( cursor, table_name, column_name ):
#    print "SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod), (SELECT substring(d.adsrc for 128) FROM pg_catalog.pg_attrdef d WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef), a.attnotnull, a.attnum, pg_catalog.col_description(a.attrelid, a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid = (SELECT c.oid from pg_catalog.pg_class c where c.relname ~ '^%s$') AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum" % table_name
    cursor.execute("SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod), (SELECT substring(d.adsrc for 128) FROM pg_catalog.pg_attrdef d WHERE d.adrelid = a.attrelid AND d.adnum = a.attnum AND a.atthasdef), a.attnotnull, a.attnum, pg_catalog.col_description(a.attrelid, a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid = (SELECT c.oid from pg_catalog.pg_class c where c.relname ~ '^%s$') AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum" % table_name)
    dict = {}
    dict['primary_key'] = False
    dict['foreign_key'] = False
    dict['unique'] = False
    dict['default'] = ''
            
#    dict['allow_null'] = False
    for row in cursor.fetchall():
        if row[0] == column_name:

            # maxlength check goes here
            if row[1][0:17]=='character varying':
                dict['maxlength'] = row[1][18:len(row[1])-1]
            
            # null flag check goes here
            dict['allow_null'] = not row[3]

    # pk, fk and unique checks go here
#    print "select pg_constraint.conname, pg_constraint.contype, pg_attribute.attname from pg_constraint, pg_attribute where pg_constraint.conrelid=pg_attribute.attrelid and pg_attribute.attnum=any(pg_constraint.conkey) and pg_constraint.conname~'^%s'" % table_name 
    unique_conname = None
    shared_unique_connames = set()
    cursor.execute("select pg_constraint.conname, pg_constraint.contype, pg_attribute.attname from pg_constraint, pg_attribute where pg_constraint.conrelid=pg_attribute.attrelid and pg_attribute.attnum=any(pg_constraint.conkey) and pg_constraint.conname~'^%s'" % table_name )
    for row in cursor.fetchall():
        if row[2] == column_name:
            if row[1]=='p': dict['primary_key'] = True
            if row[1]=='f': dict['foreign_key'] = True
            if row[1]=='u': unique_conname = row[0]
        else:
            if row[1]=='u': shared_unique_connames.add( row[0] )
    if unique_conname and unique_conname not in shared_unique_connames:
        dict['unique'] = True
        
            # default value check goes here
    cursor.execute("select pg_attribute.attname, adsrc from pg_attrdef, pg_attribute WHERE pg_attrdef.adrelid=pg_attribute.attrelid and pg_attribute.attnum=pg_attrdef.adnum and pg_attrdef.adrelid = (SELECT c.oid from pg_catalog.pg_class c where c.relname ~ '^%s$')" % table_name )
    for row in cursor.fetchall():
        if row[0] == column_name:
            if row[1][0:7] == 'nextval': continue
            dict['default'] = row[1][1:row[1].index("'",1)]
            
#    print table_name, column_name, dict
    return dict

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
