"""
Timezone-related classes and functions.

This module uses pytz when it's available and fallbacks when it isn't.
"""

import sys
import time as _time
from datetime import datetime, timedelta, tzinfo
from threading import local

from django.conf import settings
from django.utils import lru_cache, six
from django.utils.decorators import ContextDecorator

try:
    import pytz
except ImportError:
    pytz = None


__all__ = [
    'utc', 'get_fixed_timezone',
    'get_default_timezone', 'get_default_timezone_name',
    'get_current_timezone', 'get_current_timezone_name',
    'activate', 'deactivate', 'override',
    'localtime', 'now',
    'is_aware', 'is_naive', 'make_aware', 'make_naive',
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


class FixedOffset(tzinfo):
    """
    Fixed offset in minutes east from UTC. Taken from Python's docs.

    Kept as close as possible to the reference version. __init__ was changed
    to make its arguments optional, according to Python's requirement that
    tzinfo subclasses can be instantiated without arguments.
    """

    def __init__(self, offset=None, name=None):
        if offset is not None:
            self.__offset = timedelta(minutes=offset)
        if name is not None:
            self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO


class ReferenceLocalTimezone(tzinfo):
    """
    Local time. Taken from Python's docs.

    Used only when pytz isn't available, and most likely inaccurate. If you're
    having trouble with this class, don't waste your time, just install pytz.

    Kept as close as possible to the reference version. __init__ was added to
    delay the computation of STDOFFSET, DSTOFFSET and DSTDIFF which is
    performed at import time in the example.

    Subclasses contain further improvements.
    """

    def __init__(self):
        self.STDOFFSET = timedelta(seconds=-_time.timezone)
        if _time.daylight:
            self.DSTOFFSET = timedelta(seconds=-_time.altzone)
        else:
            self.DSTOFFSET = self.STDOFFSET
        self.DSTDIFF = self.DSTOFFSET - self.STDOFFSET
        tzinfo.__init__(self)

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


class LocalTimezone(ReferenceLocalTimezone):
    """
    Slightly improved local time implementation focusing on correctness.

    It still crashes on dates before 1970 or after 2038, but at least the
    error message is helpful.
    """

    def tzname(self, dt):
        is_dst = False if dt is None else self._isdst(dt)
        return _time.tzname[is_dst]

    def _isdst(self, dt):
        try:
            return super(LocalTimezone, self)._isdst(dt)
        except (OverflowError, ValueError) as exc:
            exc_type = type(exc)
            exc_value = exc_type(
                "Unsupported value: %r. You should install pytz." % dt)
            exc_value.__cause__ = exc
            if not hasattr(exc, '__traceback__'):
                exc.__traceback__ = sys.exc_info()[2]
            six.reraise(exc_type, exc_value, sys.exc_info()[2])

utc = pytz.utc if pytz else UTC()
"""UTC time zone as a tzinfo instance."""


def get_fixed_timezone(offset):
    """
    Returns a tzinfo instance with a fixed offset from UTC.
    """
    if isinstance(offset, timedelta):
        offset = offset.seconds // 60
    sign = '-' if offset < 0 else '+'
    hhmm = '%02d%02d' % divmod(abs(offset), 60)
    name = sign + hhmm
    return FixedOffset(offset, name)


# In order to avoid accessing settings at compile time,
# wrap the logic in a function and cache the result.
@lru_cache.lru_cache()
def get_default_timezone():
    """
    Returns the default time zone as a tzinfo instance.

    This is the time zone defined by settings.TIME_ZONE.
    """
    if isinstance(settings.TIME_ZONE, six.string_types) and pytz is not None:
        return pytz.timezone(settings.TIME_ZONE)
    else:
        # This relies on os.environ['TZ'] being set to settings.TIME_ZONE.
        return LocalTimezone()


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
        return timezone.tzname(None)

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
    elif isinstance(timezone, six.string_types) and pytz is not None:
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


class override(ContextDecorator):
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

    def __enter__(self):
        self.old_timezone = getattr(_active, 'value', None)
        if self.timezone is None:
            deactivate()
        else:
            activate(self.timezone)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_timezone is None:
            deactivate()
        else:
            _active.value = self.old_timezone


# Templates

def template_localtime(value, use_tz=None):
    """
    Checks if value is a datetime and converts it to local time if necessary.

    If use_tz is provided and is not None, that will force the value to
    be converted (or not), overriding the value of settings.USE_TZ.

    This function is designed for use by the template engine.
    """
    should_convert = (
        isinstance(value, datetime) and
        (settings.USE_TZ if use_tz is None else use_tz) and
        not is_naive(value) and
        getattr(value, 'convert_to_local_time', True)
    )
    return localtime(value) if should_convert else value


# Utilities

def localtime(value, timezone=None):
    """
    Converts an aware datetime.datetime to local time.

    Local time is defined by the current time zone, unless another time zone
    is specified.
    """
    if timezone is None:
        timezone = get_current_timezone()
    # If `value` is naive, astimezone() will raise a ValueError,
    # so we don't need to perform a redundant check.
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # This method is available for pytz time zones.
        value = timezone.normalize(value)
    return value


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

    The concept is defined in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is not None


def is_naive(value):
    """
    Determines if a given datetime.datetime is naive.

    The concept is defined in Python's docs:
    http://docs.python.org/library/datetime.html#datetime.tzinfo

    Assuming value.tzinfo is either None or a proper datetime.tzinfo,
    value.utcoffset() implements the appropriate logic.
    """
    return value.utcoffset() is None


def make_aware(value, timezone=None, is_dst=None):
    """
    Makes a naive datetime.datetime in a given time zone aware.
    """
    if timezone is None:
        timezone = get_current_timezone()
    if hasattr(timezone, 'localize'):
        # This method is available for pytz time zones.
        return timezone.localize(value, is_dst=is_dst)
    else:
        # Check that we won't overwrite the timezone of an aware datetime.
        if is_aware(value):
            raise ValueError(
                "make_aware expects a naive datetime, got %s" % value)
        # This may be wrong around DST changes!
        return value.replace(tzinfo=timezone)


def make_naive(value, timezone=None):
    """
    Makes an aware datetime.datetime naive in a given time zone.
    """
    if timezone is None:
        timezone = get_current_timezone()
    # If `value` is naive, astimezone() will raise a ValueError,
    # so we don't need to perform a redundant check.
    value = value.astimezone(timezone)
    if hasattr(timezone, 'normalize'):
        # This method is available for pytz time zones.
        value = timezone.normalize(value)
    return value.replace(tzinfo=None)
