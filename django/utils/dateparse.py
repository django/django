"""Functions to parse datetime objects."""

# We're using regular expressions rather than time.strptime because:
# - They provide both validation and parsing.
# - They're more flexible for datetimes.
# - The date/datetime/time constructors produce friendlier error messages.

import datetime
import re
from django.utils.timezone import utc
from django.utils.tzinfo import FixedOffset

date_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})$'
)

datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{1,2}:\d{1,2})?$'
)

time_re = re.compile(
    r'(?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
)

def parse_date(value):
    """Parses a string and return a datetime.date.

    Raises ValueError if the input is well formatted but not a valid date.
    Returns None if the input isn't well formatted.
    """
    match = date_re.match(value)
    if match:
        kw = dict((k, int(v)) for k, v in match.groupdict().iteritems())
        return datetime.date(**kw)

def parse_time(value):
    """Parses a string and return a datetime.time.

    This function doesn't support time zone offsets.

    Sub-microsecond precision is accepted, but ignored.

    Raises ValueError if the input is well formatted but not a valid time.
    Returns None if the input isn't well formatted, in particular if it
    contains an offset.
    """
    match = time_re.match(value)
    if match:
        kw = match.groupdict()
        if kw['microsecond']:
            kw['microsecond'] = kw['microsecond'].ljust(6, '0')
        kw = dict((k, int(v)) for k, v in kw.iteritems() if v is not None)
        return datetime.time(**kw)

def parse_datetime(value):
    """Parses a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses an instance of FixedOffset as tzinfo.

    Sub-microsecond precision is accepted, but ignored.

    Raises ValueError if the input is well formatted but not a valid datetime.
    Returns None if the input isn't well formatted.
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
            offset = 60 * int(tzinfo[1:3]) + int(tzinfo[4:6])
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = FixedOffset(offset)
        kw = dict((k, int(v)) for k, v in kw.iteritems() if v is not None)
        kw['tzinfo'] = tzinfo
        return datetime.datetime(**kw)
