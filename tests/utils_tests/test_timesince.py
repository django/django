from __future__ import unicode_literals

import datetime
import unittest

from django.test.utils import requires_tz_support
from django.utils import timezone
from django.utils.timesince import timesince, timeuntil


class TimesinceTests(unittest.TestCase):

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
        # NOTE: \xa0 avoids wrapping between value and unit
        self.assertEqual(timesince(self.t, self.t), '0\xa0minutes')

    def test_ignore_microseconds_and_seconds(self):
        """ Microseconds and seconds are ignored. """
        self.assertEqual(timesince(self.t, self.t + self.onemicrosecond), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t + self.onesecond), '0\xa0minutes')

    def test_other_units(self):
        """ Test other units. """
        self.assertEqual(timesince(self.t, self.t + self.oneminute), '1\xa0minute')
        self.assertEqual(timesince(self.t, self.t + self.onehour), '1\xa0hour')
        self.assertEqual(timesince(self.t, self.t + self.oneday), '1\xa0day')
        self.assertEqual(timesince(self.t, self.t + self.oneweek), '1\xa0week')
        self.assertEqual(timesince(self.t, self.t + self.onemonth), '1\xa0month')
        self.assertEqual(timesince(self.t, self.t + self.oneyear), '1\xa0year')

    def test_multiple_units(self):
        """ Test multiple units. """
        self.assertEqual(timesince(self.t, self.t + 2 * self.oneday + 6 * self.onehour), '2\xa0days, 6\xa0hours')
        self.assertEqual(timesince(self.t, self.t + 2 * self.oneweek + 2 * self.oneday), '2\xa0weeks, 2\xa0days')

    def test_display_first_unit(self):
        """
        If the two differing units aren't adjacent, only the first unit is
        displayed.
        """
        self.assertEqual(
            timesince(self.t, self.t + 2 * self.oneweek + 3 * self.onehour + 4 * self.oneminute),
            '2\xa0weeks'
        )
        self.assertEqual(timesince(self.t, self.t + 4 * self.oneday + 5 * self.oneminute), '4\xa0days')

    def test_display_second_before_first(self):
        """
        When the second date occurs before the first, we should always
        get 0 minutes.
        """
        self.assertEqual(timesince(self.t, self.t - self.onemicrosecond), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.onesecond), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.oneminute), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.onehour), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.oneday), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.oneweek), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.onemonth), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - self.oneyear), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - 2 * self.oneday - 6 * self.onehour), '0\xa0minutes')
        self.assertEqual(timesince(self.t, self.t - 2 * self.oneweek - 2 * self.oneday), '0\xa0minutes')
        self.assertEqual(
            timesince(self.t, self.t - 2 * self.oneweek - 3 * self.onehour - 4 * self.oneminute), '0\xa0minutes'
        )
        self.assertEqual(timesince(self.t, self.t - 4 * self.oneday - 5 * self.oneminute), '0\xa0minutes')

    @requires_tz_support
    def test_different_timezones(self):
        """ When using two different timezones. """
        now = datetime.datetime.now()
        now_tz = timezone.make_aware(now, timezone.get_default_timezone())
        now_tz_i = timezone.localtime(now_tz, timezone.get_fixed_timezone(195))

        self.assertEqual(timesince(now), '0\xa0minutes')
        self.assertEqual(timesince(now_tz), '0\xa0minutes')
        self.assertEqual(timesince(now_tz_i), '0\xa0minutes')
        self.assertEqual(timesince(now_tz, now_tz_i), '0\xa0minutes')
        self.assertEqual(timeuntil(now), '0\xa0minutes')
        self.assertEqual(timeuntil(now_tz), '0\xa0minutes')
        self.assertEqual(timeuntil(now_tz_i), '0\xa0minutes')
        self.assertEqual(timeuntil(now_tz, now_tz_i), '0\xa0minutes')

    def test_date_objects(self):
        """ Both timesince and timeuntil should work on date objects (#17937). """
        today = datetime.date.today()
        self.assertEqual(timesince(today + self.oneday), '0\xa0minutes')
        self.assertEqual(timeuntil(today - self.oneday), '0\xa0minutes')

    def test_both_date_objects(self):
        """ Timesince should work with both date objects (#9672) """
        today = datetime.date.today()
        self.assertEqual(timeuntil(today + self.oneday, today), '1\xa0day')
        self.assertEqual(timeuntil(today - self.oneday, today), '0\xa0minutes')
        self.assertEqual(timeuntil(today + self.oneweek, today), '1\xa0week')

    def test_naive_datetime_with_tzinfo_attribute(self):
        class naive(datetime.tzinfo):
            def utcoffset(self, dt):
                return None
        future = datetime.datetime(2080, 1, 1, tzinfo=naive())
        self.assertEqual(timesince(future), '0\xa0minutes')
        past = datetime.datetime(1980, 1, 1, tzinfo=naive())
        self.assertEqual(timeuntil(past), '0\xa0minutes')

    def test_thousand_years_ago(self):
        t = datetime.datetime(1007, 8, 14, 13, 46, 0)
        self.assertEqual(timesince(t, self.t), '1000\xa0years')
