"""Timezone helper functions.

This module uses pytz when it's available and fallbacks when it isn't.
"""

from datetime import datetime, timedelta, tzinfo
from threading import local
import time as _time

try:
    import pytz
except ImportError:
    pytz = None

from django.conf import settings

__all__ = [
    'utc', 'get_default_timezone', 'get_current_timezone',
    'activate', 'deactivate', 'override',
    'is_naive', 'is_aware', 'make_aware', 'make_naive',
]


# UTC and local time zones

ZERO = timedelta(0)

class UTC(tzinfo):
    """
    UTC implementation taken from Python's docs.

    Used only when pytz isn't available.
    """

    def __repr__(self):
        return "<UTC>"

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

class LocalTimezone(tzinfo):
    """
    Local time implementation taken from Python's docs.

    Used only when pytz isn't available, and most likely inaccurate. If you're
    having trouble with this class, don't waste your time, just install pytz.
    """

    def __init__(self):
        # This code is moved in __init__ to execute it as late as possible
        # See get_default_timezone().
        self.STDOFFSET = timedelta(seconds=-_time.timezone)
        if _time.daylight:
            self.DSTOFFSET = timedelta(seconds=-_time.altzone)
        else:
            self.DSTOFFSET = self.STDOFFSET
        self.DSTDIFF = self.DSTOFFSET - self.STDOFFSET
        tzinfo.__init__(self)

    def __repr__(self):
        return "<LocalTimezone>"

    def utcoffset(self, dt):
        if self._isdst(dt):
            return self.DSTOFFSET
        else:
            return self.STDOFFSET

    def dst(self, dt):
        if self._isdst(dt):
            return self.DSTDIFF
        else:
            return ZERO

    def tzname(self, dt):
        return _time.tzname[self._isdst(dt)]

    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = _time.mktime(tt)
        tt = _time.localtime(stamp)
        return tt.tm_isdst > 0


utc = pytz.utc if pytz else UTC()
"""UTC time zone as a tzinfo instance."""

# In order to avoid accessing the settings at compile time,
# wrap the expression in a function and cache the result.
# If you change settings.TIME_ZONE in tests, reset _localtime to None.
_localtime = None

def get_default_timezone():
    """
    Returns the default time zone as a tzinfo instance.

    This is the time zone defined by settings.TIME_ZONE.

    See also :func:`get_current_timezone`.
    """
    global _localtime
    if _localtime is None:
        if isinstance(settings.TIME_ZONE, basestring) and pytz is not None:
            _localtime = pytz.timezone(settings.TIME_ZONE)
        else:
            _localtime = LocalTimezone()
    return _localtime

# This function exists for consistency with get_current_timezone_name
def get_default_timezone_name():
    """
    Returns the name of the default time zone.
    """
    return _get_timezone_name(get_default_timezone())

_active = local()

def get_current_timezone():
    """
    Returns the currently active time zone as a tzinfo instance.
    """
    return getattr(_active, "value", get_default_timezone())

def get_current_timezone_name():
    """
    Returns the name of the currently active time zone.
    """
    return _get_timezone_name(get_current_timezone())

def _get_timezone_name(timezone):
    """
    Returns the name of ``timezone``.
    """
    try:
        # for pytz timezones
        return timezone.zone
    except AttributeError:
        # for regular tzinfo objects
        local_now = datetime.now(timezone)
        return timezone.tzname(local_now)

# Timezone selection functions.

# These functions don't change os.environ['TZ'] and call time.tzset()
# because it isn't thread safe.

def activate(timezone):
    """
    Sets the time zone for the current thread.

    The ``timezone`` argument must be an instance of a tzinfo subclass or a
    time zone name. If it is a time zone name, pytz is required.
    """
    if isinstance(timezone, tzinfo):
        _active.value = timezone
    elif isinstance(timezone, basestring) and pytz is not None:
        _active.value = pytz.timezone(timezone)
    else:
        raise ValueError("Invalid timezone: %r" % timezone)

def deactivate():
    """
    Unsets the time zone for the current thread.

    Django will then use the time zone defined by settings.TIME_ZONE.
    """
    if hasattr(_active, "value"):
        del _active.value

class override(object):
    """
    Temporarily set the time zone for the current thread.

    This is a context manager that uses ``~django.utils.timezone.activate()``
    to set the timezone on entry, and restores the previously active timezone
    on exit.

    The ``timezone`` argument must be an instance of a ``tzinfo`` subclass, a
    time zone name, or ``None``. If is it a time zone name, pytz is required.
    If it is ``None``, Django enables the default time zone.
    """
    def __init__(self, timezone):
        self.timezone = timezone
        self.old_timezone = getattr(_active, 'value', None)

    def __enter__(self):
        if self.timezone is None:
            deactivate()
        else:
            activate(self.timezone)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_timezone is not None:
            _active.value = self.old_timezone
        else:
            del _active.value


# Templates

def localtime(value, use_tz=None):
    """
    Checks if value is a datetime and converts it to local time if necessary.

    If use_tz is provided and is not None, that will force the value to
    be converted (or not), overriding the value of settings.USE_TZ.

    This function is designed for use by the template engine.
    """
    if (isinstance(value, datetime)
        and (settings.USE_TZ if use_tz is None else use_tz)
        and not is_naive(value)
        and getattr(value, 'convert_to_local_time', True)):
        timezone = get_current_timezone()
        value = value.astimezone(timezone)
        if hasattr(timezone, 'normalize'):
            # available for pytz time zones
            value = timezone.normalize(value)
    return value


# Utilities

def now():
    """
    Returns an aware or naive datetime.datetime, depending on settings.USE_TZ.
    """
    if settings.USE_TZ:
        # timeit shows that datetime.now(tz=utc) is 24% slower
        return datetime.utcnow().replace(tzinfo=utc)
    else:
        return datetime.now()

# By design, these four functions don't perform any checks on their arguments.
# The caller should ensure that they don't receive an invalid value like None.

def is_aware(value):
    """
    Determines if a given datetime.datetime is aware.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None

def is_naive(value):
    """
    Determines if a given datetime.datetime is naive.

    The logic is described in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo
    """
    return value.tzinfo is None or value.tzinfo.utcoffset(value) is None

def make_aware(value, timezone):
    """
    Makes a naive datetime.datetime in a given time zone aware.
    """
    if hasattr(timezone, 'localize'):
        # available for pytz time zones
        return timezone.localize(value, is_dst=None)
    else:
        # may be wrong around DST changes
        return value.replace(tzinfo=timezone)

def make_naive(value, timezone):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # available for pytz time zones
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)
