import datetime, math, time
from django.utils.tzinfo import LocalTimezone

def timesince(d, now=None):
    """
    Takes a datetime object, returns the time between then and now
    as a nicely formatted string, e.g "10 minutes"
    Adapted from http://blog.natbat.co.uk/archive/2003/Jun/14/time_since
    """
    chunks = (
      (60 * 60 * 24 * 365, 'year'),
      (60 * 60 * 24 * 30, 'month'),
      (60 * 60 * 24, 'day'),
      (60 * 60, 'hour'),
      (60, 'minute')
    )
    if now:
        t = time.mktime(now)
    else:
        t = time.localtime()
    if d.tzinfo:
        tz = LocalTimezone()
    else:
        tz = None
    now = datetime.datetime(t[0], t[1], t[2], t[3], t[4], t[5], tzinfo=tz)
    delta = now - d
    since = delta.days * 24 * 60 * 60 + delta.seconds
    # Crazy iteration syntax because we need i to be current index
    for i, (seconds, name) in zip(range(len(chunks)), chunks):
        count = math.floor(since / seconds)
        if count != 0:
            break
    if count == 1:
        s = '1 %s' % name
    else:
        s = '%d %ss' % (count, name)
    if i + 1 < len(chunks):
        # Now get the second item
        seconds2, name2 = chunks[i + 1]
        count2 = math.floor((since - (seconds * count)) / seconds2)
        if count2 != 0:
            if count2 == 1:
                s += ', 1 %s' % name2
            else:
                s += ', %d %ss' % (count2, name2)
    return s

def timeuntil(d):
    """
    Like timesince, but returns a string measuring the time until
    the given time.
    """
    now = datetime.datetime.now()
    return timesince(now, time.mktime(d.timetuple()))
