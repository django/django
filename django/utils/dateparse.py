"""Functions to parse datetime objects."""

# We're using regular expressions rather than time.strptime because:
# - They provide both validation and parsing.
# - They're more flexible for datetimes.
# - The date/datetime/time constructors produce friendlier error messages.

import datetime
import re

from django.utils.timezone import get_fixed_timezone, utc

date_re = re.compile(
    r'(?P<year>[0-9]{4})-(?P<month>[0-9]{1,2})-(?P<day>[0-9]{1,2})$'
)

time_re = re.compile(
    r'(?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{1,2})'
    r'(?::(?P<second>[0-9]{1,2})(?:\.(?P<microsecond>[0-9]{1,6})[0-9]{0,6})?)?'
)

datetime_re = re.compile(
    r'(?P<year>[0-9]{4})-(?P<month>[0-9]{1,2})-(?P<day>[0-9]{1,2})'
    r'[T ](?P<hour>[0-9]{1,2}):(?P<minute>[0-9]{1,2})'
    r'(?::(?P<second>[0-9]{1,2})(?:\.(?P<microsecond>[0-9]{1,6})[0-9]{0,6})?)?'
    r'(?P<tzinfo>Z|[+-][0-9]{2}(?::?[0-9]{2})?)?$'
)

standard_duration_re = re.compile(
    r'^'
    r'(?:(?P<days>-?[0-9]+) (days?, )?)?'
    r'((?:(?P<hours>-?[0-9]+):)(?=[0-9]+:[0-9]+))?'
    r'(?:(?P<minutes>-?[0-9]+):)?'
    r'(?P<seconds>-?[0-9]+)'
    r'(?:\.(?P<microseconds>[0-9]{1,6})[0-9]{0,6})?'
    r'$'
)

# Support the sections of ISO 8601 date representation that are accepted by
# timedelta
iso8601_duration_re = re.compile(
    r'^(?P<sign>[-+]?)'
    r'P'
    r'(?:(?P<days>[0-9]+(.[0-9]+)?)D)?'
    r'(?:T'
    r'(?:(?P<hours>[0-9]+(.[0-9]+)?)H)?'
    r'(?:(?P<minutes>[0-9]+(.[0-9]+)?)M)?'
    r'(?:(?P<seconds>[0-9]+(.[0-9]+)?)S)?'
    r')?'
    r'$'
)

# Support PostgreSQL's day-time interval format, e.g. "3 days 04:05:06". The
# year-month and mixed intervals cannot be converted to a timedelta and thus
# aren't accepted.
postgres_interval_re = re.compile(
    r'^'
    r'(?:(?P<days>-?[0-9]+) (days? ?))?'
    r'(?:(?P<sign>[-+])?'
    r'(?P<hours>[0-9]+):'
    r'(?P<minutes>[0-9][0-9]):'
    r'(?P<seconds>[0-9][0-9])'
    r'(?:\.(?P<microseconds>[0-9]{1,6}))?'
    r')?$'
)


def parse_date(value):
    """Parse a string and return a datetime.date.

    Raise ValueError if the input is well formatted but not a valid date.
    Return None if the input isn't well formatted.
    """
    match = date_re.match(value)
    if match:
        kw = {k: int(v) for k, v in match.groupdict().items()}
        return datetime.date(**kw)


def parse_time(value):
    """Parse a string and return a datetime.time.

    This function doesn't support time zone offsets.

    Raise ValueError if the input is well formatted but not a valid time.
    Return None if the input isn't well formatted, in particular if it
    contains an offset.
    """
    match = time_re.match(value)
    if match:
        kw = match.groupdict()
        if kw['microsecond']:
            kw['microsecond'] = kw['microsecond'].ljust(6, '0')
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        return datetime.time(**kw)


def parse_datetime(value):
    """Parse a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raise ValueError if the input is well formatted but not a valid datetime.
    Return None if the input isn't well formatted.
    """
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        if kw['microsecond']:
            kw['microsecond'] = kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime.datetime(**kw)


def parse_duration(value):
    """Parse a duration string and return a datetime.timedelta.

    The preferred format for durations in Django is '%d %H:%M:%S.%f'.

    Also supports ISO 8601 representation and PostgreSQL's day-time interval
    format.
    """
    match = standard_duration_re.match(value)
    if not match:
        match = iso8601_duration_re.match(value) or postgres_interval_re.match(value)
    if match:
        kw = match.groupdict()
        days = datetime.timedelta(float(kw.pop('days', 0) or 0))
        sign = -1 if kw.pop('sign', '+') == '-' else 1
        if kw.get('microseconds'):
            kw['microseconds'] = kw['microseconds'].ljust(6, '0')
        if kw.get('seconds') and kw.get('microseconds') and kw['seconds'].startswith('-'):
            kw['microseconds'] = '-' + kw['microseconds']
        kw = {k: float(v) for k, v in kw.items() if v is not None}
        return days + sign * datetime.timedelta(**kw)
