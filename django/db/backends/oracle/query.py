"""
Custom Query class for Oracle.
Derives from: django.db.models.sql.query.Query
"""

import datetime

from django.db.backends import util

# Cache. Maps default query class to new Oracle query class.
_classes = {}

def query_class(QueryClass, Database):
    """
    Returns a custom django.db.models.sql.query.Query subclass that is
    appropriate for Oracle.

    The 'Database' module (cx_Oracle) is passed in here so that all the setup
    required to import it only needs to be done by the calling module.
    """
    global _classes
    try:
        return _classes[QueryClass]
    except KeyError:
        pass

    class OracleQuery(QueryClass):
        def __reduce__(self):
            """
            Enable pickling for this class (normal pickling handling doesn't
            work as Python can only pickle module-level classes by default).
            """
            if hasattr(QueryClass, '__getstate__'):
                assert hasattr(QueryClass, '__setstate__')
                data = self.__getstate__()
            else:
                data = self.__dict__
            return (unpickle_query_class, (QueryClass,), data)

        def resolve_columns(self, row, fields=()):
            # If this query has limit/offset information, then we expect the
            # first column to be an extra "_RN" column that we need to throw
            # away.
            if self.high_mark is not None or self.low_mark:
                rn_offset = 1
            else:
                rn_offset = 0
            index_start = rn_offset + len(self.extra_select.keys())
            values = [self.convert_values(v, None)
                      for v in row[rn_offset:index_start]]
            for value, field in map(None, row[index_start:], fields):
                values.append(self.convert_values(value, field))
            return values

        def convert_values(self, value, field):
            if isinstance(value, Database.LOB):
                value = value.read()
            # Oracle stores empty strings as null. We need to undo this in
            # order to adhere to the Django convention of using the empty
            # string instead of null, but only if the field accepts the
            # empty string.
            if value is None and field and field.empty_strings_allowed:
                value = u''
            # Convert 1 or 0 to True or False
            elif value in (1, 0) and field and field.get_internal_type() in ('BooleanField', 'NullBooleanField'):
                value = bool(value)
            # Force floats to the correct type
            elif value is not None and field and field.get_internal_type() == 'FloatField':
                value = float(value)
            # Convert floats to decimals
            elif value is not None and field and field.get_internal_type() == 'DecimalField':
                value = util.typecast_decimal(field.format_number(value))
            # cx_Oracle always returns datetime.datetime objects for
            # DATE and TIMESTAMP columns, but Django wants to see a
            # python datetime.date, .time, or .datetime.  We use the type
            # of the Field to determine which to cast to, but it's not
            # always available.
            # As a workaround, we cast to date if all the time-related
            # values are 0, or to time if the date is 1/1/1900.
            # This could be cleaned a bit by adding a method to the Field
            # classes to normalize values from the database (the to_python
            # method is used for validation and isn't what we want here).
            elif isinstance(value, Database.Timestamp):
                # In Python 2.3, the cx_Oracle driver returns its own
                # Timestamp object that we must convert to a datetime class.
                if not isinstance(value, datetime.datetime):
                    value = datetime.datetime(value.year, value.month,
                            value.day, value.hour, value.minute, value.second,
                            value.fsecond)
                if field and field.get_internal_type() == 'DateTimeField':
                    pass
                elif field and field.get_internal_type() == 'DateField':
                    value = value.date()
                elif field and field.get_internal_type() == 'TimeField' or (value.year == 1900 and value.month == value.day == 1):
                    value = value.time()
                elif value.hour == value.minute == value.second == value.microsecond == 0:
                    value = value.date()
            return value

        def as_sql(self, with_limits=True, with_col_aliases=False):
            """
            Creates the SQL for this query. Returns the SQL string and list
            of parameters.  This is overriden from the original Query class
            to handle the additional SQL Oracle requires to emulate LIMIT
            and OFFSET.

            If 'with_limits' is False, any limit/offset information is not
            included in the query.
            """

            # The `do_offset` flag indicates whether we need to construct
            # the SQL needed to use limit/offset with Oracle.
            do_offset = with_limits and (self.high_mark is not None
                                         or self.low_mark)
            if not do_offset:
                sql, params = super(OracleQuery, self).as_sql(with_limits=False,
                        with_col_aliases=with_col_aliases)
            else:
                sql, params = super(OracleQuery, self).as_sql(with_limits=False,
                                                        with_col_aliases=True)

                # Wrap the base query in an outer SELECT * with boundaries on
                # the "_RN" column.  This is the canonical way to emulate LIMIT
                # and OFFSET on Oracle.
                high_where = ''
                if self.high_mark is not None:
                    high_where = 'WHERE ROWNUM <= %d' % (self.high_mark,)
                sql = 'SELECT * FROM (SELECT ROWNUM AS "_RN", "_SUB".* FROM (%s) "_SUB" %s) WHERE "_RN" > %d' % (sql, high_where, self.low_mark)

            return sql, params

    _classes[QueryClass] = OracleQuery
    return OracleQuery

def unpickle_query_class(QueryClass):
    """
    Utility function, called by Python's unpickling machinery, that handles
    unpickling of Oracle Query subclasses.
    """
    # XXX: Would be nice to not have any dependency on cx_Oracle here. Since
    # modules can't be pickled, we need a way to know to load the right module.
    import cx_Oracle

    klass = query_class(QueryClass, cx_Oracle)
    return klass.__new__(klass)
unpickle_query_class.__safe_for_unpickling__ = True

