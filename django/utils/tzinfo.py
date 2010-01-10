"Implementation of tzinfo classes for use with datetime.datetime."

import time
from datetime import timedelta, tzinfo
from django.utils.encoding import smart_unicode, smart_str, DEFAULT_LOCALE_ENCODING

class FixedOffset(tzinfo):
    "Fixed offset in minutes east from UTC."
    def __init__(self, offset):
        if isinstance(offset, timedelta):
            self.__offset = offset
            offset = self.__offset.seconds // 60
        else:
            self.__offset = timedelta(minutes=offset)

        sign = offset < 0 and '-' or '+'
        self.__name = u"%s%02d%02d" % (sign, abs(offset) / 60., abs(offset) % 60)

    def __repr__(self):
        return self.__name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)

class LocalTimezone(tzinfo):
    "Proxy timezone information from time module."
    def __init__(self, dt):
        tzinfo.__init__(self)
        self._tzname = self.tzname(dt)

    def __repr__(self):
        return smart_str(self._tzname)

    def utcoffset(self, dt):
        if self._isdst(dt):
            return timedelta(seconds=-time.altzone)
        else:
            return timedelta(seconds=-time.timezone)

    def dst(self, dt):
        if self._isdst(dt):
            return timedelta(seconds=-time.altzone) - timedelta(seconds=-time.timezone)
        else:
            return timedelta(0)

    def tzname(self, dt):
        try:
            return smart_unicode(time.tzname[self._isdst(dt)],
                                 DEFAULT_LOCALE_ENCODING)
        except UnicodeDecodeError:
            return None

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
        try:
            stamp = time.mktime(tt)
        except (OverflowError, ValueError):
            # 32 bit systems can't handle dates after Jan 2038, and certain
            # systems can't handle dates before ~1901-12-01:
            #
            # >>> time.mktime((1900, 1, 13, 0, 0, 0, 0, 0, 0))
            # OverflowError: mktime argument out of range
            # >>> time.mktime((1850, 1, 13, 0, 0, 0, 0, 0, 0))
            # ValueError: year out of range
            #
            # In this case, we fake the date, because we only care about the
            # DST flag.
            tt = (2037,) + tt[1:]
            stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0
