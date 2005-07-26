"""
PHP date() style date formatting
See http://www.php.net/date for format strings

Usage:
>>> import datetime
>>> d = datetime.datetime.now()
>>> df = DateFormat(d)
>>> print df.format('jS F Y H:i')
7th October 2003 11:39
>>>
"""

from calendar import isleap
from dates import MONTHS, MONTHS_AP, WEEKDAYS

class DateFormat:
    year_days = [None, 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]

    def __init__(self, d):
        self.date = d

    def a(self):
        "'a.m.' or 'p.m.'"
        if self.date.hour > 11:
            return 'p.m.'
        return 'a.m.'

    def A(self):
        "'AM' or 'PM'"
        if self.date.hour > 11:
            return 'PM'
        return 'AM'

    def B(self):
        "Swatch Internet time"
        raise NotImplementedError

    def d(self):
        "Day of the month, 2 digits with leading zeros; i.e. '01' to '31'"
        return '%02d' % self.date.day

    def D(self):
        "Day of the week, textual, 3 letters; e.g. 'Fri'"
        return WEEKDAYS[self.date.weekday()][0:3]

    def f(self):
        """
        Time, in 12-hour hours and minutes, with minutes left off if they're zero.
        Examples: '1', '1:30', '2:05', '2'
        Proprietary extension.
        """
        if self.date.minute == 0:
            return self.g()
        return '%s:%s' % (self.g(), self.i())

    def F(self):
        "Month, textual, long; e.g. 'January'"
        return MONTHS[self.date.month]

    def g(self):
        "Hour, 12-hour format without leading zeros; i.e. '1' to '12'"
        if self.date.hour == 0:
            return 12
        if self.date.hour > 12:
            return self.date.hour - 12
        return self.date.hour

    def G(self):
        "Hour, 24-hour format without leading zeros; i.e. '0' to '23'"
        return self.date.hour

    def h(self):
        "Hour, 12-hour format; i.e. '01' to '12'"
        return '%02d' % self.g()

    def H(self):
        "Hour, 24-hour format; i.e. '00' to '23'"
        return '%02d' % self.G()

    def i(self):
        "Minutes; i.e. '00' to '59'"
        return '%02d' % self.date.minute

    def I(self):
        "'1' if Daylight Savings Time, '0' otherwise."
        raise NotImplementedError

    def j(self):
        "Day of the month without leading zeros; i.e. '1' to '31'"
        return self.date.day

    def l(self):
        "Day of the week, textual, long; e.g. 'Friday'"
        return WEEKDAYS[self.date.weekday()]

    def L(self):
        "Boolean for whether it is a leap year; i.e. True or False"
        return isleap(self.date.year)

    def m(self):
        "Month; i.e. '01' to '12'"
        return '%02d' % self.date.month

    def M(self):
        "Month, textual, 3 letters; e.g. 'Jan'"
        return MONTHS[self.date.month][0:3]

    def n(self):
        "Month without leading zeros; i.e. '1' to '12'"
        return self.date.month

    def N(self):
        "Month abbreviation in Associated Press style. Proprietary extension."
        return MONTHS_AP[self.date.month]

    def O(self):
        "Difference to Greenwich time in hours; e.g. '+0200'"
        raise NotImplementedError

    def P(self):
        """
        Time, in 12-hour hours, minutes and 'a.m.'/'p.m.', with minutes left off
        if they're zero and the strings 'midnight' and 'noon' if appropriate.
        Examples: '1 a.m.', '1:30 p.m.', 'midnight', 'noon', '12:30 p.m.'
        Proprietary extension.
        """
        if self.date.minute == 0 and self.date.hour == 0:
            return 'midnight'
        if self.date.minute == 0 and self.date.hour == 12:
            return 'noon'
        return '%s %s' % (self.f(), self.a())

    def r(self):
        "RFC 822 formatted date; e.g. 'Thu, 21 Dec 2000 16:01:07 +0200'"
        raise NotImplementedError

    def s(self):
        "Seconds; i.e. '00' to '59'"
        return '%02d' % self.date.second

    def S(self):
        "English ordinal suffix for the day of the month, 2 characters; i.e. 'st', 'nd', 'rd' or 'th'"
        if self.date.day in (11, 12, 13): # Special case
            return 'th'
        last = self.date.day % 10
        if last == 1:
            return 'st'
        if last == 2:
            return 'nd'
        if last == 3:
            return 'rd'
        return 'th'

    def t(self):
        "Number of days in the given month; i.e. '28' to '31'"
        raise NotImplementedError

    def T(self):
        "Time zone of this machine; e.g. 'EST' or 'MDT'"
        raise NotImplementedError

    def U(self):
        "Seconds since the Unix epoch (January 1 1970 00:00:00 GMT)"
        raise NotImplementedError

    def w(self):
        "Day of the week, numeric, i.e. '0' (Sunday) to '6' (Saturday)"
        weekday = self.date.weekday()
        if weekday == 0:
            return 6
        return weekday - 1

    def W(self):
        "ISO-8601 week number of year, weeks starting on Monday"
        # Algorithm from http://www.personal.ecu.edu/mccartyr/ISOwdALG.txt
        week_number = None
        jan1_weekday = self.date.replace(month=1, day=1).weekday() + 1
        weekday = self.date.weekday() + 1
        day_of_year = self.z()
        if day_of_year <= (8 - jan1_weekday) and jan1_weekday > 4:
            if jan1_weekday == 5 or (jan1_weekday == 6 and isleap(self.date.year-1)):
                week_number = 53
            else:
                week_number = 52
        else:
            if isleap(self.date.year):
                i = 366
            else:
                i = 365
            if (i - day_of_year) < (4 - weekday):
                week_number = 1
            else:
                j = day_of_year + (7 - weekday) + (jan1_weekday - 1)
                week_number = j / 7
                if jan1_weekday > 4:
                    week_number -= 1
        return week_number

    def Y(self):
        "Year, 4 digits; e.g. '1999'"
        return self.date.year

    def y(self):
        "Year, 2 digits; e.g. '99'"
        return str(self.date.year)[2:]

    def z(self):
        "Day of the year; i.e. '0' to '365'"
        doy = self.year_days[self.date.month] + self.date.day
        if self.L() and self.date.month > 2:
            doy += 1
        return doy

    def Z(self):
        """Time zone offset in seconds (i.e. '-43200' to '43200'). The offset
        for timezones west of UTC is always negative, and for those east of UTC
        is always positive."""
        raise NotImplementedError

    def format(self, formatstr):
        result = ''
        for char in formatstr:
            try:
                result += str(getattr(self, char)())
            except AttributeError:
                result += char
        return result

class TimeFormat:
    def __init__(self, t):
        self.time = t

    def a(self):
        "'a.m.' or 'p.m.'"
        if self.time.hour > 11:
            return 'p.m.'
        else:
            return 'a.m.'

    def A(self):
        "'AM' or 'PM'"
        return self.a().upper()

    def B(self):
        "Swatch Internet time"
        raise NotImplementedError

    def f(self):
        """
        Time, in 12-hour hours and minutes, with minutes left off if they're zero.
        Examples: '1', '1:30', '2:05', '2'
        Proprietary extension.
        """
        if self.time.minute == 0:
            return self.g()
        return '%s:%s' % (self.g(), self.i())

    def g(self):
        "Hour, 12-hour format without leading zeros; i.e. '1' to '12'"
        if self.time.hour == 0:
            return 12
        if self.time.hour > 12:
            return self.time.hour - 12
        return self.time.hour

    def G(self):
        "Hour, 24-hour format without leading zeros; i.e. '0' to '23'"
        return self.time.hour

    def h(self):
        "Hour, 12-hour format; i.e. '01' to '12'"
        return '%02d' % self.g()

    def H(self):
        "Hour, 24-hour format; i.e. '00' to '23'"
        return '%02d' % self.G()

    def i(self):
        "Minutes; i.e. '00' to '59'"
        return '%02d' % self.time.minute

    def P(self):
        """
        Time, in 12-hour hours, minutes and 'a.m.'/'p.m.', with minutes left off
        if they're zero and the strings 'midnight' and 'noon' if appropriate.
        Examples: '1 a.m.', '1:30 p.m.', 'midnight', 'noon', '12:30 p.m.'
        Proprietary extension.
        """
        if self.time.minute == 0 and self.time.hour == 0:
            return 'midnight'
        if self.time.minute == 0 and self.time.hour == 12:
            return 'noon'
        return '%s %s' % (self.f(), self.a())

    def s(self):
        "Seconds; i.e. '00' to '59'"
        return '%02d' % self.time.second

    def format(self, formatstr):
        result = ''
        for char in formatstr:
            try:
                result += str(getattr(self, char)())
            except AttributeError:
                result += char
        return result

def format(value, format_string):
    "Convenience function"
    df = DateFormat(value)
    return df.format(format_string)

def time_format(value, format_string):
    "Convenience function"
    tf = TimeFormat(value)
    return tf.format(format_string)
