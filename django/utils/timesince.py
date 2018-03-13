import calendar
import datetime

from django.utils.html import avoid_wrapping
from django.utils.timezone import is_aware, utc
from django.utils.translation import gettext, ngettext_lazy

TIME_STRINGS = {
    'year': ngettext_lazy('%d year', '%d years'),
    'month': ngettext_lazy('%d month', '%d months'),
    'week': ngettext_lazy('%d week', '%d weeks'),
    'day': ngettext_lazy('%d day', '%d days'),
    'hour': ngettext_lazy('%d hour', '%d hours'),
    'minute': ngettext_lazy('%d minute', '%d minutes'),
}

TIMESINCE_CHUNKS = (
    (60 * 60 * 24 * 365, 'year'),
    (60 * 60 * 24 * 30, 'month'),
    (60 * 60 * 24 * 7, 'week'),
    (60 * 60 * 24, 'day'),
    (60 * 60, 'hour'),
    (60, 'minute'),
)


def timesince(d, now=None, reversed=False, time_strings=None):
    """
    Take two datetime objects and return the time between d and now as a nicely
    formatted string, e.g. "10 minutes". If d occurs after now, return
    "0 minutes".

    Units used are years, months, weeks, days, hours, and minutes.
    Seconds and microseconds are ignored.  Up to two adjacent units will be
    displayed.  For example, "2 weeks, 3 days" and "1 year, 3 months" are
    possible outputs, but "2 weeks, 3 hours" and "1 year, 5 days" are not.

    `time_strings` is an optional dict of strings to replace the default
    TIME_STRINGS dict.

    Adapted from
    http://web.archive.org/web/20060617175230/http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    if time_strings is None:
        time_strings = TIME_STRINGS

    # Convert datetime.date to datetime.datetime for comparison.
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    now = now or datetime.datetime.now(utc if is_aware(d) else None)

    if reversed:
        d, now = now, d
    delta = now - d

    # Deal with leapyears by subtracing the number of leapdays
    leapdays = calendar.leapdays(d.year, now.year)
    if leapdays != 0:
        if calendar.isleap(d.year):
            leapdays -= 1
        elif calendar.isleap(now.year):
            leapdays += 1
    delta -= datetime.timedelta(leapdays)

    # ignore microseconds
    since = delta.days * 24 * 60 * 60 + delta.seconds
    if since <= 0:
        # d is in the future compared to now, stop processing.
        return avoid_wrapping(gettext('0 minutes'))
    for i, (seconds, name) in enumerate(TIMESINCE_CHUNKS):
        count = since // seconds
        if count != 0:
            break
    result = avoid_wrapping(time_strings[name] % count)
    if i + 1 < len(TIMESINCE_CHUNKS):
        # Now get the second item
        seconds2, name2 = TIMESINCE_CHUNKS[i + 1]
        count2 = (since - (seconds * count)) // seconds2
        if count2 != 0:
            result += gettext(', ') + avoid_wrapping(time_strings[name2] % count2)
    return result


def timeuntil(d, now=None, time_strings=None):
    """
    Like timesince, but return a string measuring the time until the given time.
    """
    return timesince(d, now, reversed=True, time_strings=time_strings)
