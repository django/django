import datetime

from .base import Database


class InsertVar:
    """
    A late-binding cursor variable that can be passed to Cursor.execute
    as a parameter, in order to receive the id of the row created by an
    insert statement.
    """
    types = {
        'AutoField': int,
        'BigAutoField': int,
        'SmallAutoField': int,
        'IntegerField': int,
        'BigIntegerField': int,
        'SmallIntegerField': int,
        'PositiveSmallIntegerField': int,
        'PositiveIntegerField': int,
        'FloatField': Database.NATIVE_FLOAT,
        'DateTimeField': Database.TIMESTAMP,
        'DateField': Database.Date,
        'DecimalField': Database.NUMBER,
    }

    def __init__(self, field):
        internal_type = getattr(field, 'target_field', field).get_internal_type()
        self.db_type = self.types.get(internal_type, str)
        self.bound_param = None

    def bind_parameter(self, cursor):
        self.bound_param = cursor.cursor.var(self.db_type)
        return self.bound_param

    def get_value(self):
        return self.bound_param.getvalue()


class Oracle_datetime(datetime.datetime):
    """
    A datetime object, with an additional class attribute
    to tell cx_Oracle to save the microseconds too.
    """
    input_size = Database.TIMESTAMP

    @classmethod
    def from_datetime(cls, dt):
        return Oracle_datetime(
            dt.year, dt.month, dt.day,
            dt.hour, dt.minute, dt.second, dt.microsecond,
        )


class BulkInsertMapper:
    BLOB = 'TO_BLOB(%s)'
    CLOB = 'TO_CLOB(%s)'
    DATE = 'TO_DATE(%s)'
    INTERVAL = 'CAST(%s as INTERVAL DAY(9) TO SECOND(6))'
    NUMBER = 'TO_NUMBER(%s)'
    TIMESTAMP = 'TO_TIMESTAMP(%s)'

    types = {
        'BigIntegerField': NUMBER,
        'BinaryField': BLOB,
        'BooleanField': NUMBER,
        'DateField': DATE,
        'DateTimeField': TIMESTAMP,
        'DecimalField': NUMBER,
        'DurationField': INTERVAL,
        'FloatField': NUMBER,
        'IntegerField': NUMBER,
        'NullBooleanField': NUMBER,
        'PositiveIntegerField': NUMBER,
        'PositiveSmallIntegerField': NUMBER,
        'SmallIntegerField': NUMBER,
        'TextField': CLOB,
        'TimeField': TIMESTAMP,
    }
