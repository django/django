"""
MySQL database backend for Django.

Requires MySQLdb: http://sourceforge.net/projects/mysql-python
"""

from django.core.db import base, typecasts
from django.core.db.dicthelpers import *
import MySQLdb as Database
from MySQLdb.converters import conversions
from MySQLdb.constants import FIELD_TYPE
import types

DatabaseError = Database.DatabaseError

django_conversions = conversions.copy()
django_conversions.update({
    types.BooleanType: typecasts.rev_typecast_boolean,
    FIELD_TYPE.DATETIME: typecasts.typecast_timestamp,
    FIELD_TYPE.DATE: typecasts.typecast_date,
    FIELD_TYPE.TIME: typecasts.typecast_time,
})

# This is an extra debug layer over MySQL queries, to display warnings.
# It's only used when DEBUG=True.
class MysqlDebugWrapper:
    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, sql, params=()):
        try:
            return self.cursor.execute(sql, params)
        except Database.Warning, w:
            self.cursor.execute("SHOW WARNINGS")
            raise Database.Warning, "%s: %s" % (w, self.cursor.fetchall())

    def executemany(self, sql, param_list):
        try:
            return self.cursor.executemany(sql, param_list)
        except Database.Warning:
            self.cursor.execute("SHOW WARNINGS")
            raise Database.Warning, "%s: %s" % (w, self.cursor.fetchall())

    def __getattr__(self, attr):
        if self.__dict__.has_key(attr):
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_USER, DATABASE_NAME, DATABASE_HOST, DATABASE_PORT, DATABASE_PASSWORD, DEBUG
        if self.connection is None:
            kwargs = {
                'user': DATABASE_USER,
                'db': DATABASE_NAME,
                'passwd': DATABASE_PASSWORD,
                'host': DATABASE_HOST,
                'conv': django_conversions,
            }
            if DATABASE_PORT:
                kwargs['port'] = DATABASE_PORT
            self.connection = Database.connect(**kwargs)
        if DEBUG:
            return base.CursorDebugWrapper(MysqlDebugWrapper(self.connection.cursor()), self)
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        if self.connection:
            try:
                self.connection.rollback()
            except Database.NotSupportedError:
                pass

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute("SELECT LAST_INSERT_ID()")
    return cursor.fetchone()[0]

def get_date_extract_sql(lookup_type, table_name):
    # lookup_type is 'year', 'month', 'day'
    # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
    return "EXTRACT(%s FROM %s)" % (lookup_type.upper(), table_name)

def get_date_trunc_sql(lookup_type, field_name):
    # lookup_type is 'year', 'month', 'day'
    # http://dev.mysql.com/doc/mysql/en/date-and-time-functions.html
    # MySQL doesn't support DATE_TRUNC, so we fake it by subtracting intervals.
    # If you know of a better way to do this, please file a Django ticket.
    subtractions = ["interval (DATE_FORMAT(%s, '%%%%s')) second - interval (DATE_FORMAT(%s, '%%%%i')) minute - interval (DATE_FORMAT(%s, '%%%%H')) hour" % (field_name, field_name, field_name)]
    if lookup_type in ('year', 'month'):
        subtractions.append(" - interval (DATE_FORMAT(%s, '%%%%e')-1) day" % field_name)
    if lookup_type == 'year':
        subtractions.append(" - interval (DATE_FORMAT(%s, '%%%%m')-1) month" % field_name)
    return "(%s - %s)" % (field_name, ''.join(subtractions))

def get_limit_offset_sql(limit, offset=None):
    sql = "LIMIT "
    if offset and offset != 0:
        sql += "%s," % offset
    return sql + str(limit)

def get_random_function_sql():
    return "RAND()"

def get_table_list(cursor):
    "Returns a list of table names in the current database."
    cursor.execute("SHOW TABLES")
    return [row[0] for row in cursor.fetchall()]

def get_relations(cursor, table_name):
    raise NotImplementedError

OPERATOR_MAPPING = {
    'exact': '=',
    'iexact': 'LIKE',
    'contains': 'LIKE BINARY',
    'icontains': 'LIKE',
    'ne': '!=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'startswith': 'LIKE BINARY',
    'endswith': 'LIKE BINARY',
    'istartswith': 'LIKE',
    'iendswith': 'LIKE',
}

# This dictionary maps Field objects to their associated MySQL column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':         'mediumint(9) unsigned auto_increment',
    'BooleanField':      'bool',
    'CharField':         'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField': 'varchar(%(maxlength)s)',
    'DateField':         'date',
    'DateTimeField':     'datetime',
    'EmailField':        'varchar(75)',
    'FileField':         'varchar(100)',
    'FilePathField':     'varchar(100)',
    'FloatField':        'numeric(%(max_digits)s, %(decimal_places)s)',
    'ImageField':        'varchar(100)',
    'IntegerField':      'integer',
    'IPAddressField':    'char(15)',
    'ManyToManyField':   None,
    'NullBooleanField':  'bool',
    'OneToOneField':     'integer',
    'PhoneNumberField':  'varchar(20)',
    'PositiveIntegerField': 'integer UNSIGNED',
    'PositiveSmallIntegerField': 'smallint UNSIGNED',
    'SlugField':         'varchar(50)',
    'SmallIntegerField': 'smallint',
    'TextField':         'longtext',
    'TimeField':         'time',
    'URLField':          'varchar(200)',
    'USStateField':      'varchar(2)',
}

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
