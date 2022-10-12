"""
PHP date() style date formatting
See https://www.php.net/date for format strings

Usage:
>>> from datetime import datetime
>>> d = datetime.now()
>>> df = DateFormat(d)
>>> print(df.format('jS F Y H:i'))
7th October 2003 11:39
>>>
"""
import calendar
from datetime import date, datetime, time
from email.utils import format_datetime as format_datetime_rfc5322

from django.utils.dates import (
    MONTHS,
    MONTHS_3,
    MONTHS_ALT,
    MONTHS_AP,
    WEEKDAYS,
    WEEKDAYS_ABBR,
)
from django.utils.regex_helper import _lazy_re_compile
from django.utils.timezone import (
    _datetime_ambiguous_or_imaginary,
    get_default_timezone,
    is_naive,
    make_aware,
)
from django.utils.translation import gettext as _

re_formatchars = _lazy_re_compile(r"(?<!\\)([aAbcdDeEfFgGhHiIjlLmMnNoOPrsStTUuwWyYzZ])")
re_escaped = _lazy_re_compile(r"\\(.)")


class Formatter:
    def format(self, formatstr):
        pieces = []
        for i, piece in enumerate(re_formatchars.split(str(formatstr))):
            if i % 2:
                if type(self.data) is date and hasattr(TimeFormat, piece):
                    raise TypeError(
                        "The format for date objects may not contain "
                        "time-related format specifiers (found '%s')." % piece
                    )
                pieces.append(str(getattr(self, piece)()))
            elif piece:
                pieces.append(re_escaped.sub(r"\1", piece))
        return "".join(pieces)


class TimeFormat(Formatter):
    def __init__(self, obj):
        self.data = obj
        self.timezone = None

        if isinstance(obj, datetime):
            # Timezone is only supported when formatting datetime objects, not
            # date objects (timezone information not appropriate), or time
            # objects (against established django policy).
            if is_naive(obj):
                timezone = get_default_timezone()
            else:
                timezone = obj.tzinfo
            if not _datetime_ambiguous_or_imaginary(obj, timezone):
                self.timezone = timezone

    def a(self):
        "'a.m.' or 'p.m.'"
        if self.data.hour > 11:
            return _("p.m.")
        return _("a.m.")

    def A(self):
        "'AM' or 'PM'"
        if self.data.hour > 11:
            return _("PM")
        return _("AM")

    def e(self):
        """
        Timezone name.

        If timezone information is not available, return an empty string.
        """
        if not self.timezone:
            return ""

        try:
            if getattr(self.data, "tzinfo", None):
                return self.data.tzname() or ""
        except NotImplementedError:
            pass
        return ""

    def f(self):
        """
        Time, in 12-hour hours and minutes, with minutes left off if they're
        zero.
        Examples: '1', '1:30', '2:05', '2'
        Proprietary extension.
        """
        hour = self.data.hour % 12 or 12
        minute = self.data.minute
        return "%d:%02d" % (hour, minute) if minute else hour

    def g(self):
        "Hour, 12-hour format without leading zeros; i.e. '1' to '12'"
        return self.data.hour % 12 or 12

    def G(self):
        "Hour, 24-hour format without leading zeros; i.e. '0' to '23'"
        return self.data.hour

    def h(self):
        "Hour, 12-hour format; i.e. '01' to '12'"
        return "%02d" % (self.data.hour % 12 or 12)

    def H(self):
        "Hour, 24-hour format; i.e. '00' to '23'"
        return "%02d" % self.data.hour

    def i(self):
        "Minutes; i.e. '00' to '59'"
        return "%02d" % self.data.minute

    def O(self):  # NOQA: E743, E741
        """
        Difference to Greenwich time in hours; e.g. '+0200', '-0430'.

        If timezone information is not available, return an empty string.
        """
        if self.timezone is None:
            return ""

        offset = self.timezone.utcoffset(self.data)
        seconds = offset.days * 86400 + offset.seconds
        sign = "-" if seconds < 0 else "+"
        seconds = abs(seconds)
        return "%s%02d%02d" % (sign, seconds // 3600, (seconds // 60) % 60)

    def P(self):
        """
        Time, in 12-hour hours, minutes and 'a.m.'/'p.m.', with minutes left off
        if they're zero and the strings 'midnight' and 'noon' if appropriate.
        Examples: '1 a.m.', '1:30 p.m.', 'midnight', 'noon', '12:30 p.m.'
        Proprietary extension.
        """
        if self.data.minute == 0 and self.data.hour == 0:
            return _("midnight")
        if self.data.minute == 0 and self.data.hour == 12:
            return _("noon")
        return "%s %s" % (self.f(), self.a())

    def s(self):
        "Seconds; i.e. '00' to '59'"
        return "%02d" % self.data.second

    def T(self):
        """
        Time zone of this machine; e.g. 'EST' or 'MDT'.

        If timezone information is not available, return an empty string.
        """
        if self.timezone is None:
            return ""

        return str(self.timezone.tzname(self.data))

    def u(self):
        "Microseconds; i.e. '000000' to '999999'"
        return "%06d" % self.data.microsecond

    def Z(self):
        """
        Time zone offset in seconds (i.e. '-43200' to '43200'). The offset for
        timezones west of UTC is always negative, and for those east of UTC is
        always positive.

        If timezone information is not available, return an empty string.
        """
        if self.timezone is None:
            return ""

        offset = self.timezone.utcoffset(self.data)

        # `offset` is a datetime.timedelta. For negative values (to the west of
        # UTC) only days can be negative (days=-1) and seconds are always
        # positive. e.g. UTC-1 -> timedelta(days=-1, seconds=82800, microseconds=0)
        # Positive offsets have days=0
        return offset.days * 86400 + offset.seconds


class DateFormat(TimeFormat):
    def b(self):
        "Month, textual, 3 letters, lowercase; e.g. 'jan'"
        return MONTHS_3[self.data.month]

    def c(self):
        """
        ISO 8601 Format
        Example : '2008-01-02T10:30:00.000123'
        """
        return self.data.isoformat()

    def d(self):
        "Day of the month, 2 digits with leading zeros; i.e. '01' to '31'"
        return "%02d" % self.data.day

    def D(self):
        "Day of the week, textual, 3 letters; e.g. 'Fri'"
        return WEEKDAYS_ABBR[self.data.weekday()]

    def E(self):
        "Alternative month names as required by some locales. Proprietary extension."
        return MONTHS_ALT[self.data.month]

    def F(self):
        "Month, textual, long; e.g. 'January'"
        return MONTHS[self.data.month]

    def I(self):  # NOQA: E743, E741
        "'1' if daylight saving time, '0' otherwise."
        if self.timezone is None:
            return ""
        return "1" if self.timezone.dst(self.data) else "0"

    def j(self):
        "Day of the month without leading zeros; i.e. '1' to '31'"
        return self.data.day

    def l(self):  # NOQA: E743, E741
        "Day of the week, textual, long; e.g. 'Friday'"
        return WEEKDAYS[self.data.weekday()]

    def L(self):
        "Boolean for whether it is a leap year; i.e. True or False"
        return calendar.isleap(self.data.year)

    def m(self):
        "Month; i.e. '01' to '12'"
        return "%02d" % self.data.month

    def M(self):
        "Month, textual, 3 letters; e.g. 'Jan'"
        return MONTHS_3[self.data.month].title()

    def n(self):
        "Month without leading zeros; i.e. '1' to '12'"
        return self.data.month

    def N(self):
        "Month abbreviation in Associated Press style. Proprietary extension."
        return MONTHS_AP[self.data.month]

    def o(self):
        "ISO 8601 year number matching the ISO week number (W)"
        return self.data.isocalendar()[0]

    def r(self):
        "RFC 5322 formatted date; e.g. 'Thu, 21 Dec 2000 16:01:07 +0200'"
        value = self.data
        if not isinstance(value, datetime):
            # Assume midnight in default timezone if datetime.date provided.
            default_timezone = get_default_timezone()
            value = datetime.combine(value, time.min).replace(tzinfo=default_timezone)
        elif is_naive(value):
            value = make_aware(value, timezone=self.timezone)
        return format_datetime_rfc5322(value)

    def S(self):
        """
        English ordinal suffix for the day of the month, 2 characters; i.e.
        'st', 'nd', 'rd' or 'th'.
        """
        if self.data.day in (11, 12, 13):  # Special case
            return "th"
        last = self.data.day % 10
        if last == 1:
            return "st"
        if last == 2:
            return "nd"
        if last == 3:
            return "rd"
        return "th"

    def t(self):
        "Number of days in the given month; i.e. '28' to '31'"
        return calendar.monthrange(self.data.year, self.data.month)[1]

    def U(self):
        "Seconds since the Unix epoch (January 1 1970 00:00:00 GMT)"
        value = self.data
        if not isinstance(value, datetime):
            value = datetime.combine(value, time.min)
        return int(value.timestamp())

    def w(self):
        "Day of the week, numeric, i.e. '0' (Sunday) to '6' (Saturday)"
        return (self.data.weekday() + 1) % 7

    def W(self):
        "ISO-8601 week number of year, weeks starting on Monday"
        return self.data.isocalendar()[1]

    def y(self):
        """Year, 2 digits with leading zeros; e.g. '99'."""
        return "%02d" % (self.data.year % 100)

    def Y(self):
        """Year, 4 digits with leading zeros; e.g. '1999'."""
        return "%04d" % self.data.year

    def z(self):
        """Day of the year, i.e. 1 to 366."""
        return self.data.timetuple().tm_yday


def format(value, format_string):
    "Convenience function"
    df = DateFormat(value)
    return df.format(format_string)


def time_format(value, format_string):
    "Convenience function"
    tf = TimeFormat(value)
    return tf.format(format_string)
