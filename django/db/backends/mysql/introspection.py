from django.db.backends.mysql.base import quote_name
from MySQLdb import ProgrammingError, OperationalError
from MySQLdb.constants import FIELD_TYPE
import re

foreign_key_re = re.compile(r"\sCONSTRAINT `[^`]*` FOREIGN KEY \(`([^`]*)`\) REFERENCES `([^`]*)` \(`([^`]*)`\)")

def get_table_list(cursor):
    "Returns a list of table names in the current database."
    cursor.execute("SHOW TABLES")
    return [row[0] for row in cursor.fetchall()]

def get_table_description(cursor, table_name):
    "Returns a description of the table, with the DB-API cursor.description interface."
    cursor.execute("SELECT * FROM %s LIMIT 1" % quote_name(table_name))
    return cursor.description

def _name_to_index(cursor, table_name):
    """
    Returns a dictionary of {field_name: field_index} for the given table.
    Indexes are 0-based.
    """
    return dict([(d[0], i) for i, d in enumerate(get_table_description(cursor, table_name))])

def get_relations(cursor, table_name):
    """
    Returns a dictionary of {field_index: (field_index_other_table, other_table)}
    representing all relationships to the given table. Indexes are 0-based.
    """
    my_field_dict = _name_to_index(cursor, table_name)
    constraints = []
    relations = {}
    try:
        # This should work for MySQL 5.0.
        cursor.execute("""
            SELECT column_name, referenced_table_name, referenced_column_name
            FROM information_schema.key_column_usage
            WHERE table_name = %s
                AND table_schema = DATABASE()
                AND referenced_table_name IS NOT NULL
                AND referenced_column_name IS NOT NULL""", [table_name])
        constraints.extend(cursor.fetchall())
    except (ProgrammingError, OperationalError):
        # Fall back to "SHOW CREATE TABLE", for previous MySQL versions.
        # Go through all constraints and save the equal matches.
        cursor.execute("SHOW CREATE TABLE %s" % quote_name(table_name))
        for row in cursor.fetchall():
            pos = 0
            while True:
                match = foreign_key_re.search(row[1], pos)
                if match == None:
                    break
                pos = match.end()
                constraints.append(match.groups())

    for my_fieldname, other_table, other_field in constraints:
        other_field_index = _name_to_index(cursor, other_table)[other_field]
        my_field_index = my_field_dict[my_fieldname]
        relations[my_field_index] = (other_field_index, other_table)

    return relations

def get_indexes(cursor, table_name):
    """
    Returns a dictionary of fieldname -> infodict for the given table,
    where each infodict is in the format:
        {'primary_key': boolean representing whether it's the primary key,
         'unique': boolean representing whether it's a unique index}
    """
    cursor.execute("SHOW INDEX FROM %s" % quote_name(table_name))
    indexes = {}
    for row in cursor.fetchall():
        indexes[row[4]] = {'primary_key': (row[2] == 'PRIMARY'), 'unique': not bool(row[1])}
    return indexes

def get_columns(cursor, table_name):
    try:
        cursor.execute("describe %s" % quote_name(table_name))
        return [row[0] for row in cursor.fetchall()]
    except:
        return []
    
def get_known_column_flags( cursor, table_name, column_name ):
    cursor.execute("describe %s" % quote_name(table_name))
    dict = {}
    for row in cursor.fetchall():
        if row[0] == column_name:

            # maxlength check goes here
            if row[1][0:7]=='varchar':
                dict['maxlength'] = row[1][8:len(row[1])-1]
            
            # default flag check goes here
            if row[2]=='YES': dict['allow_null'] = True
            else: dict['allow_null'] = False
            
            # primary/foreign/unique key flag check goes here
            if row[3]=='PRI': dict['primary_key'] = True
            else: dict['primary_key'] = False
            if row[3]=='FOR': dict['foreign_key'] = True
            else: dict['foreign_key'] = False
            if row[3]=='UNI': dict['unique'] = True
            else: dict['unique'] = False
            
            # default value check goes here
            # if row[4]=='NULL': dict['default'] = None
            # else: dict['default'] = row[4]
            dict['default'] = row[4]
            
    # print table_name, column_name, dict
    return dict
    
DATA_TYPES_REVERSE = {
    FIELD_TYPE.BLOB: 'TextField',
    FIELD_TYPE.CHAR: 'CharField',
    FIELD_TYPE.DECIMAL: 'FloatField',
    FIELD_TYPE.DATE: 'DateField',
    FIELD_TYPE.DATETIME: 'DateTimeField',
    FIELD_TYPE.DOUBLE: 'FloatField',
    FIELD_TYPE.FLOAT: 'FloatField',
    FIELD_TYPE.INT24: 'IntegerField',
    FIELD_TYPE.LONG: 'IntegerField',
    FIELD_TYPE.LONGLONG: 'IntegerField',
    FIELD_TYPE.SHORT: 'IntegerField',
    FIELD_TYPE.STRING: 'TextField',
    FIELD_TYPE.TIMESTAMP: 'DateTimeField',
    FIELD_TYPE.TINY: 'IntegerField',
    FIELD_TYPE.TINY_BLOB: 'TextField',
    FIELD_TYPE.MEDIUM_BLOB: 'TextField',
    FIELD_TYPE.LONG_BLOB: 'TextField',
    FIELD_TYPE.VAR_STRING: 'CharField',
}
