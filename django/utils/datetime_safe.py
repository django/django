# These classes override date and datetime to ensure that strftime('%Y')
# returns four digits (with leading zeros) on years < 1000.
# https://bugs.python.org/issue13305
#
# Based on code submitted to comp.lang.python by Andrew Dalke
#
# >>> datetime_safe.date(10, 8, 2).strftime("%Y/%m/%d was a %A")
# '0010/08/02 was a Monday'

import time
import warnings
from datetime import date as real_date, datetime as real_datetime

from django.utils.deprecation import RemovedInDjango50Warning
from django.utils.regex_helper import _lazy_re_compile

warnings.warn(
    "The django.utils.datetime_safe module is deprecated.",
    category=RemovedInDjango50Warning,
    stacklevel=2,
)


class date(real_date):
    def strftime(self, fmt):
        return strftime(self, fmt)


class datetime(real_datetime):
    def strftime(self, fmt):
        return strftime(self, fmt)

    @classmethod
    def combine(cls, date, time):
        return cls(
            date.year,
            date.month,
            date.day,
            time.hour,
            time.minute,
            time.second,
            time.microsecond,
            time.tzinfo,
        )

    def date(self):
        return date(self.year, self.month, self.day)


def new_date(d):
    "Generate a safe date from a datetime.date object."
    return date(d.year, d.month, d.day)


def new_datetime(d):
    """
    Generate a safe datetime from a datetime.date or datetime.datetime object.
    """
    kw = [d.year, d.month, d.day]
    if isinstance(d, real_datetime):
        kw.extend([d.hour, d.minute, d.second, d.microsecond, d.tzinfo])
    return datetime(*kw)


# This library does not support strftime's "%s" or "%y" format strings.
# Allowed if there's an even number of "%"s because they are escaped.
_illegal_formatting = _lazy_re_compile(r"((^|[^%])(%%)*%[sy])")


def _findall(text, substr):
    # Also finds overlaps
    sites = []
    i = 0
    while True:
        i = text.find(substr, i)
        if i == -1:
            break
        sites.append(i)
        i += 1
    return sites


def strftime(dt, fmt):
    if dt.year >= 1000:
        return super(type(dt), dt).strftime(fmt)
    illegal_formatting = _illegal_formatting.search(fmt)
    if illegal_formatting:
        raise TypeError(
            "strftime of dates before 1000 does not handle " + illegal_formatting[0]
        )

    year = dt.year
    # For every non-leap year century, advance by
    # 6 years to get into the 28-year repeat cycle
    delta = 2000 - year
    off = 6 * (delta // 100 + delta // 400)
    year = year + off

    # Move to around the year 2000
    year = year + ((2000 - year) // 28) * 28
    timetuple = dt.timetuple()
    s1 = time.strftime(fmt, (year,) + timetuple[1:])
    sites1 = _findall(s1, str(year))

    s2 = time.strftime(fmt, (year + 28,) + timetuple[1:])
    sites2 = _findall(s2, str(year + 28))

    sites = []
    for site in sites1:
        if site in sites2:
            sites.append(site)

    s = s1
    syear = "%04d" % dt.year
    for site in sites:
        s = s[:site] + syear + s[site + 4 :]
    return s
