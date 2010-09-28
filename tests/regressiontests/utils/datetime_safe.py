import unittest

from datetime import date as original_date, datetime as original_datetime
from django.utils.datetime_safe import date, datetime

class DatetimeTests(unittest.TestCase):

    def setUp(self):
        self.just_safe = (1900, 1, 1)
        self.just_unsafe = (1899, 12, 31, 23, 59, 59)
        self.really_old = (20, 1, 1)
        self.more_recent = (2006, 1, 1)

    def test_compare_datetimes(self):
        self.assertEqual(original_datetime(*self.more_recent), datetime(*self.more_recent))
        self.assertEqual(original_datetime(*self.really_old), datetime(*self.really_old))
        self.assertEqual(original_date(*self.more_recent), date(*self.more_recent))
        self.assertEqual(original_date(*self.really_old), date(*self.really_old))

        self.assertEqual(original_date(*self.just_safe).strftime('%Y-%m-%d'), date(*self.just_safe).strftime('%Y-%m-%d'))
        self.assertEqual(original_datetime(*self.just_safe).strftime('%Y-%m-%d'), datetime(*self.just_safe).strftime('%Y-%m-%d'))

    def test_safe_strftime(self):
        self.assertEquals(date(*self.just_unsafe[:3]).strftime('%Y-%m-%d (weekday %w)'), '1899-12-31 (weekday 0)')
        self.assertEquals(date(*self.just_safe).strftime('%Y-%m-%d (weekday %w)'), '1900-01-01 (weekday 1)')

        self.assertEquals(datetime(*self.just_unsafe).strftime('%Y-%m-%d %H:%M:%S (weekday %w)'), '1899-12-31 23:59:59 (weekday 0)')
        self.assertEquals(datetime(*self.just_safe).strftime('%Y-%m-%d %H:%M:%S (weekday %w)'), '1900-01-01 00:00:00 (weekday 1)')

        # %y will error before this date
        self.assertEquals(date(*self.just_safe).strftime('%y'), '00')
        self.assertEquals(datetime(*self.just_safe).strftime('%y'), '00')

        self.assertEquals(date(1850, 8, 2).strftime("%Y/%m/%d was a %A"), '1850/08/02 was a Friday')

    def test_zero_padding(self):
        """
        Regression for #12524

        Check that pre-1000AD dates are padded with zeros if necessary
        """
        self.assertEquals(date(1, 1, 1).strftime("%Y/%m/%d was a %A"), '0001/01/01 was a Monday')
