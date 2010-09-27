from django.test import TestCase

import datetime

from django.utils.timesince import timesince, timeuntil
from django.utils.tzinfo import LocalTimezone, FixedOffset

class TimesinceTests(TestCase):

    def setUp(self):
        self.t = datetime.datetime(2007, 8, 14, 13, 46, 0)
        self.onemicrosecond = datetime.timedelta(microseconds=1)
        self.onesecond = datetime.timedelta(seconds=1)
        self.oneminute = datetime.timedelta(minutes=1)
        self.onehour = datetime.timedelta(hours=1)
        self.oneday = datetime.timedelta(days=1)
        self.oneweek = datetime.timedelta(days=7)
        self.onemonth = datetime.timedelta(days=30)
        self.oneyear = datetime.timedelta(days=365)

    def test_equal_datetimes(self):
        """ equal datetimes. """
        self.assertEquals(timesince(self.t, self.t), u'0 minutes')

    def test_ignore_microseconds_and_seconds(self):
        """ Microseconds and seconds are ignored. """
        self.assertEquals(timesince(self.t, self.t+self.onemicrosecond),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t+self.onesecond),
            u'0 minutes')

    def test_other_units(self):
        """ Test other units. """
        self.assertEquals(timesince(self.t, self.t+self.oneminute),
            u'1 minute')
        self.assertEquals(timesince(self.t, self.t+self.onehour), u'1 hour')
        self.assertEquals(timesince(self.t, self.t+self.oneday), u'1 day')
        self.assertEquals(timesince(self.t, self.t+self.oneweek), u'1 week')
        self.assertEquals(timesince(self.t, self.t+self.onemonth),
            u'1 month')
        self.assertEquals(timesince(self.t, self.t+self.oneyear), u'1 year')

    def test_multiple_units(self):
        """ Test multiple units. """
        self.assertEquals(timesince(self.t,
            self.t+2*self.oneday+6*self.onehour), u'2 days, 6 hours')
        self.assertEquals(timesince(self.t,
            self.t+2*self.oneweek+2*self.oneday), u'2 weeks, 2 days')

    def test_display_first_unit(self):
        """
        If the two differing units aren't adjacent, only the first unit is
        displayed.
        """
        self.assertEquals(timesince(self.t,
            self.t+2*self.oneweek+3*self.onehour+4*self.oneminute),
            u'2 weeks')

        self.assertEquals(timesince(self.t,
            self.t+4*self.oneday+5*self.oneminute), u'4 days')

    def test_display_second_before_first(self):
        """
        When the second date occurs before the first, we should always
        get 0 minutes.
        """
        self.assertEquals(timesince(self.t, self.t-self.onemicrosecond),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.onesecond),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.oneminute),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.onehour),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.oneday),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.oneweek),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.onemonth),
            u'0 minutes')
        self.assertEquals(timesince(self.t, self.t-self.oneyear),
            u'0 minutes')
        self.assertEquals(timesince(self.t,
            self.t-2*self.oneday-6*self.onehour), u'0 minutes')
        self.assertEquals(timesince(self.t,
            self.t-2*self.oneweek-2*self.oneday), u'0 minutes')
        self.assertEquals(timesince(self.t,
            self.t-2*self.oneweek-3*self.onehour-4*self.oneminute),
            u'0 minutes')
        self.assertEquals(timesince(self.t,
            self.t-4*self.oneday-5*self.oneminute), u'0 minutes')

    def test_different_timezones(self):
        """ When using two different timezones. """
        now = datetime.datetime.now()
        now_tz = datetime.datetime.now(LocalTimezone(now))
        now_tz_i = datetime.datetime.now(FixedOffset((3 * 60) + 15))

        self.assertEquals(timesince(now), u'0 minutes')
        self.assertEquals(timesince(now_tz), u'0 minutes')
        self.assertEquals(timeuntil(now_tz, now_tz_i), u'0 minutes')

    def test_both_date_objects(self):
        """ Timesince should work with both date objects (#9672) """
        today = datetime.date.today()
        self.assertEquals(timeuntil(today+self.oneday, today), u'1 day')
        self.assertEquals(timeuntil(today-self.oneday, today), u'0 minutes')
        self.assertEquals(timeuntil(today+self.oneweek, today), u'1 week')
