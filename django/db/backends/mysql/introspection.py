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
