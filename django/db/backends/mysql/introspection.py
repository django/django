from django.db.backends.mysql.base import quote_name
from MySQLdb.constants import FIELD_TYPE

def get_table_list(cursor):
    "Returns a list of table names in the current database."
    cursor.execute("SHOW TABLES")
    return [row[0] for row in cursor.fetchall()]

def get_table_description(cursor, table_name):
    "Returns a description of the table, with the DB-API cursor.description interface."
    cursor.execute("SELECT * FROM %s LIMIT 1" % quote_name(table_name))
    return cursor.description

def get_relations(cursor, table_name):
    raise NotImplementedError

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
    FIELD_TYPE.TINY_BLOB: 'TextField',
    FIELD_TYPE.MEDIUM_BLOB: 'TextField',
    FIELD_TYPE.LONG_BLOB: 'TextField',
    FIELD_TYPE.VAR_STRING: 'CharField',
}
