"Implementation of tzinfo classes for use with datetime.datetime."

import locale
import time
from datetime import timedelta, tzinfo
from django.utils.encoding import smart_unicode

try:
    DEFAULT_ENCODING = locale.getdefaultlocale()[1] or 'ascii'
except:
    # Any problems at all determining the locale and we fallback. See #5846.
    DEFAULT_ENCODING = 'ascii'

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
        self._tzname = self.tzname(dt)

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
        try:
            return smart_unicode(time.tzname[self._isdst(dt)], DEFAULT_ENCODING)
        except UnicodeDecodeError:
            return None

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.weekday(), 0, -1)
        try:
            stamp = time.mktime(tt)
        except OverflowError:
            # 32 bit systems can't handle dates after Jan 2038, so we fake it
            # in that case (since we only care about the DST flag here).
            tt = (2037,) + tt[1:]
            stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0
