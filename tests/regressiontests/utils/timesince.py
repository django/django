"""
>>> from datetime import datetime, timedelta
>>> from django.utils.timesince import timesince, timeuntil
>>> from django.utils.tzinfo import LocalTimezone, FixedOffset

>>> t = datetime(2007, 8, 14, 13, 46, 0)

>>> onemicrosecond = timedelta(microseconds=1)
>>> onesecond = timedelta(seconds=1)
>>> oneminute = timedelta(minutes=1)
>>> onehour = timedelta(hours=1)
>>> oneday = timedelta(days=1)
>>> oneweek = timedelta(days=7)
>>> onemonth = timedelta(days=30)
>>> oneyear = timedelta(days=365)

# equal datetimes.
>>> timesince(t, t)
u'0 minutes'

# Microseconds and seconds are ignored.
>>> timesince(t, t+onemicrosecond)
u'0 minutes'
>>> timesince(t, t+onesecond)
u'0 minutes'

# Test other units.
>>> timesince(t, t+oneminute)
u'1 minute'
>>> timesince(t, t+onehour)
u'1 hour'
>>> timesince(t, t+oneday)
u'1 day'
>>> timesince(t, t+oneweek)
u'1 week'
>>> timesince(t, t+onemonth)
u'1 month'
>>> timesince(t, t+oneyear)
u'1 year'

# Test multiple units.
>>> timesince(t, t+2*oneday+6*onehour)
u'2 days, 6 hours'
>>> timesince(t, t+2*oneweek+2*oneday)
u'2 weeks, 2 days'

# If the two differing units aren't adjacent, only the first unit is displayed.
>>> timesince(t, t+2*oneweek+3*onehour+4*oneminute)
u'2 weeks'
>>> timesince(t, t+4*oneday+5*oneminute)
u'4 days'

# When the second date occurs before the first, we should always get 0 minutes.
>>> timesince(t, t-onemicrosecond)
u'0 minutes'
>>> timesince(t, t-onesecond)
u'0 minutes'
>>> timesince(t, t-oneminute)
u'0 minutes'
>>> timesince(t, t-onehour)
u'0 minutes'
>>> timesince(t, t-oneday)
u'0 minutes'
>>> timesince(t, t-oneweek)
u'0 minutes'
>>> timesince(t, t-onemonth)
u'0 minutes'
>>> timesince(t, t-oneyear)
u'0 minutes'
>>> timesince(t, t-2*oneday-6*onehour)
u'0 minutes'
>>> timesince(t, t-2*oneweek-2*oneday)
u'0 minutes'
>>> timesince(t, t-2*oneweek-3*onehour-4*oneminute)
u'0 minutes'
>>> timesince(t, t-4*oneday-5*oneminute)
u'0 minutes'

# When using two different timezones.
>>> now = datetime.now()
>>> now_tz = datetime.now(LocalTimezone(now))
>>> now_tz_i = datetime.now(FixedOffset((3 * 60) + 15))
>>> timesince(now)
u'0 minutes'
>>> timesince(now_tz)
u'0 minutes'
>>> timeuntil(now_tz, now_tz_i)
u'0 minutes'
"""
