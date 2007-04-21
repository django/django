"Implementation of tzinfo classes for use with datetime.datetime."

import time
from datetime import timedelta, tzinfo

class FixedOffset(tzinfo):
    "Fixed offset in minutes east from UTC."
    def __init__(self, offset):
        self.__offset = timedelta(minutes=offset)
        self.__name = u"%+03d%02d" % (offset // 60, offset % 60)

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
        tzinfo.__init__(self, dt)
        self._tzname = unicode(time.tzname[self._isdst(dt)])

    def __repr__(self):
        return self._tzname

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
        return unicode(time.tzname[self._isdst(dt)])

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0
