import datetime

from .base import Database


class InsertIdVar:
    """
    A late-binding cursor variable that can be passed to Cursor.execute
    as a parameter, in order to receive the id of the row created by an
    insert statement.
    """

    def bind_parameter(self, cursor):
        param = cursor.cursor.var(Database.NUMBER)
        cursor._insert_id_var = param
        return param


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
        'TimeField': TIMESTAMP,
    }
