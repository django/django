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

def _dict_helper(desc, row):
    "Returns a dictionary for the given cursor.description and result row."
    return dict([(desc[col[0]][0], col[1]) for col in enumerate(row)])

def dictfetchone(cursor):
    "Returns a row from the cursor as a dict"
    row = cursor.fetchone()
    if not row:
        return None
    return _dict_helper(cursor.description, row)

def dictfetchmany(cursor, number):
    "Returns a certain number of rows from a cursor as a dict"
    desc = cursor.description
    return [_dict_helper(desc, row) for row in cursor.fetchmany(number)]

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    return [_dict_helper(desc, row) for row in cursor.fetchall()]

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
    'AutoField':         'mediumint(9) unsigned auto_increment',
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
