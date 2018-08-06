from datetime import (
    date as original_date, datetime as original_datetime,
    time as original_time,
)

from django.test import SimpleTestCase
from django.utils.datetime_safe import date, datetime, time


class DatetimeTests(SimpleTestCase):

    def setUp(self):
        self.percent_y_safe = (1900, 1, 1)  # >= 1900 required on Windows.
        self.just_safe = (1000, 1, 1)
        self.just_unsafe = (999, 12, 31, 23, 59, 59)
        self.just_time = (11, 30, 59)
        self.really_old = (20, 1, 1)
        self.more_recent = (2006, 1, 1)

    def test_compare_datetimes(self):
        self.assertEqual(original_datetime(*self.more_recent), datetime(*self.more_recent))
        self.assertEqual(original_datetime(*self.really_old), datetime(*self.really_old))
        self.assertEqual(original_date(*self.more_recent), date(*self.more_recent))
        self.assertEqual(original_date(*self.really_old), date(*self.really_old))

        self.assertEqual(
            original_date(*self.just_safe).strftime('%Y-%m-%d'), date(*self.just_safe).strftime('%Y-%m-%d')
        )
        self.assertEqual(
            original_datetime(*self.just_safe).strftime('%Y-%m-%d'), datetime(*self.just_safe).strftime('%Y-%m-%d')
        )

        self.assertEqual(
            original_time(*self.just_time).strftime('%H:%M:%S'), time(*self.just_time).strftime('%H:%M:%S')
        )

    def test_safe_strftime(self):
        self.assertEqual(date(*self.just_unsafe[:3]).strftime('%Y-%m-%d (weekday %w)'), '0999-12-31 (weekday 2)')
        self.assertEqual(date(*self.just_safe).strftime('%Y-%m-%d (weekday %w)'), '1000-01-01 (weekday 3)')

        self.assertEqual(
            datetime(*self.just_unsafe).strftime('%Y-%m-%d %H:%M:%S (weekday %w)'), '0999-12-31 23:59:59 (weekday 2)'
        )
        self.assertEqual(
            datetime(*self.just_safe).strftime('%Y-%m-%d %H:%M:%S (weekday %w)'), '1000-01-01 00:00:00 (weekday 3)'
        )

        self.assertEqual(time(*self.just_time).strftime('%H:%M:%S AM'), '11:30:59 AM')

        # %y will error before this date
        self.assertEqual(date(*self.percent_y_safe).strftime('%y'), '00')
        self.assertEqual(datetime(*self.percent_y_safe).strftime('%y'), '00')
        with self.assertRaisesMessage(TypeError, 'strftime of dates before 1000 does not handle %y'):
            datetime(*self.just_unsafe).strftime('%y')

        self.assertEqual(date(1850, 8, 2).strftime("%Y/%m/%d was a %A"), '1850/08/02 was a Friday')

    def test_zero_padding(self):
        """
        Regression for #12524

        Pre-1000AD dates are padded with zeros if necessary
        """
        self.assertEqual(date(1, 1, 1).strftime("%Y/%m/%d was a %A"), '0001/01/01 was a Monday')
