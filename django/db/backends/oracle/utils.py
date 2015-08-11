import datetime

from django.utils.encoding import force_bytes, force_text

from .base import Database

# Check whether cx_Oracle was compiled with the WITH_UNICODE option if cx_Oracle is pre-5.1. This will
# also be True for cx_Oracle 5.1 and in Python 3.0. See #19606
if int(Database.version.split('.', 1)[0]) >= 5 and \
        (int(Database.version.split('.', 2)[1]) >= 1 or
         not hasattr(Database, 'UNICODE')):
    convert_unicode = force_text
else:
    convert_unicode = force_bytes


class InsertIdVar(object):
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
