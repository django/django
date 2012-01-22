import datetime
import decimal
import hashlib
from time import time

from django.conf import settings
from django.utils.log import getLogger
from django.utils.timezone import utc


logger = getLogger('django.db.backends')


class CursorWrapper(object):
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db

    def set_dirty(self):
        if self.db.is_managed():
            self.db.set_dirty()

    def __getattr__(self, attr):
        self.set_dirty()
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)


class CursorDebugWrapper(CursorWrapper):

    def execute(self, sql, params=()):
        self.set_dirty()
        start = time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time()
            duration = stop - start
            sql = self.db.ops.last_executed_query(self.cursor, sql, params)
            self.db.queries.append({
                'sql': sql,
                'time': "%.3f" % duration,
            })
            logger.debug('(%.3f) %s; args=%s' % (duration, sql, params),
                extra={'duration': duration, 'sql': sql, 'params': params}
            )

    def executemany(self, sql, param_list):
        self.set_dirty()
        start = time()
        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            stop = time()
            duration = stop - start
            try:
                times = len(param_list)
            except TypeError:           # param_list could be an iterator
                times = '?'
            self.db.queries.append({
                'sql': '%s times: %s' % (times, sql),
                'time': "%.3f" % duration,
            })
            logger.debug('(%.3f) %s; args=%s' % (duration, sql, param_list),
                extra={'duration': duration, 'sql': sql, 'params': param_list}
            )


###############################################
# Converters from database (string) to Python #
###############################################

def typecast_date(s):
    return s and datetime.date(*map(int, s.split('-'))) or None # returns None if s is null

def typecast_time(s): # does NOT store time zone information
    if not s: return None
    hour, minutes, seconds = s.split(':')
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.time(int(hour), int(minutes), int(seconds), int(float('.'+microseconds) * 1000000))

def typecast_timestamp(s): # does NOT store time zone information
    # "2005-07-29 15:48:00.590358-05"
    # "2005-07-29 09:56:00-05"
    if not s: return None
    if not ' ' in s: return typecast_date(s)
    d, t = s.split()
    # Extract timezone information, if it exists. Currently we just throw
    # it away, but in the future we may make use of it.
    if '-' in t:
        t, tz = t.split('-', 1)
        tz = '-' + tz
    elif '+' in t:
        t, tz = t.split('+', 1)
        tz = '+' + tz
    else:
        tz = ''
    dates = d.split('-')
    times = t.split(':')
    seconds = times[2]
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    tzinfo = utc if settings.USE_TZ else None
    return datetime.datetime(int(dates[0]), int(dates[1]), int(dates[2]),
        int(times[0]), int(times[1]), int(seconds),
        int((microseconds + '000000')[:6]), tzinfo)

def typecast_decimal(s):
    if s is None or s == '':
        return None
    return decimal.Decimal(s)

###############################################
# Converters from Python to database (string) #
###############################################

def rev_typecast_decimal(d):
    if d is None:
        return None
    return str(d)

def truncate_name(name, length=None, hash_len=4):
    """Shortens a string to a repeatable mangled version with the given length.
    """
    if length is None or len(name) <= length:
        return name

    hsh = hashlib.md5(name).hexdigest()[:hash_len]
    return '%s%s' % (name[:length-hash_len], hsh)

def format_number(value, max_digits, decimal_places):
    """
    Formats a number into a string with the requisite number of digits and
    decimal places.
    """
    if isinstance(value, decimal.Decimal):
        context = decimal.getcontext().copy()
        context.prec = max_digits
        return u'%s' % str(value.quantize(decimal.Decimal(".1") ** decimal_places, context=context))
    else:
        return u"%.*f" % (decimal_places, value)
