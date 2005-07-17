"""
MySQL database backend for Django.

Requires MySQLdb: http://sourceforge.net/projects/mysql-python
"""

from django.core.db import base, typecasts
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

class DatabaseWrapper:
    def __init__(self):
        self.connection = None
        self.queries = []

    def cursor(self):
        from django.conf.settings import DATABASE_USER, DATABASE_NAME, DATABASE_HOST, DATABASE_PASSWORD, DEBUG
        if self.connection is None:
            self.connection = Database.connect(user=DATABASE_USER, db=DATABASE_NAME,
                passwd=DATABASE_PASSWORD, host=DATABASE_HOST, conv=django_conversions)
        if DEBUG:
            return base.CursorDebugWrapper(self.connection.cursor(), self)
        return self.connection.cursor()

    def commit(self):
        self.connection.commit()

    def rollback(self):
        if self.connection:
            self.connection.rollback()

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None

def dictfetchone(cursor):
    "Returns a row from the cursor as a dict"
    raise NotImplementedError

def dictfetchmany(cursor, number):
    "Returns a certain number of rows from a cursor as a dict"
    raise NotImplementedError

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    raise NotImplementedError

def get_last_insert_id(cursor, table_name, pk_name):
    cursor.execute("SELECT LAST_INSERT_ID()")
    return cursor.fetchone()[0]

OPERATOR_MAPPING = {
    'exact': '=',
    'iexact': 'LIKE',
    'contains': 'LIKE',
    'icontains': 'LIKE',
    'ne': '!=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<=',
    'startswith': 'LIKE',
    'endswith': 'LIKE'
}

# This dictionary maps Field objects to their associated MySQL column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':         'mediumint(9) auto_increment',
    'BooleanField':      'bool',
    'CharField':         'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField': 'varchar(%(maxlength)s)',
    'DateField':         'date',
    'DateTimeField':     'datetime',
    'EmailField':        'varchar(75)',
    'FileField':         'varchar(100)',
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
    'TextField':         'text',
    'TimeField':         'time',
    'URLField':          'varchar(200)',
    'USStateField':      'varchar(2)',
    'XMLField':          'text',
}
