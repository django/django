from datetime import datetime, time

from django.utils import timezone

from .timezone_utils import TimezoneTestCase
from ..utils import render, setup


class DateTests(TimezoneTestCase):

    @setup({'date01': '{{ d|date:"m" }}'})
    def test_date01(self):
        output = render('date01', {'d': datetime(2008, 1, 1)})
        self.assertEqual(output, '01')

    @setup({'date02': '{{ d|date }}'})
    def test_date02(self):
        output = render('date02', {'d': datetime(2008, 1, 1)})
        self.assertEqual(output, 'Jan. 1, 2008')

    @setup({'date03': '{{ d|date:"m" }}'})
    def test_date03(self):
        """
        #9520: Make sure |date doesn't blow up on non-dates
        """
        output = render('date03', {'d': 'fail_string'})
        self.assertEqual(output, '')

    # ISO date formats
    @setup({'date04': '{{ d|date:"o" }}'})
    def test_date04(self):
        output = render('date04', {'d': datetime(2008, 12, 29)})
        self.assertEqual(output, '2009')

    @setup({'date05': '{{ d|date:"o" }}'})
    def test_date05(self):
        output = render('date05', {'d': datetime(2010, 1, 3)})
        self.assertEqual(output, '2009')

    # Timezone name
    @setup({'date06': '{{ d|date:"e" }}'})
    def test_date06(self):
        output = render('date06', {'d': datetime(2009, 3, 12, tzinfo=timezone.get_fixed_timezone(30))})
        self.assertEqual(output, '+0030')

    @setup({'date07': '{{ d|date:"e" }}'})
    def test_date07(self):
        output = render('date07', {'d': datetime(2009, 3, 12)})
        self.assertEqual(output, '')

    # #19370: Make sure |date doesn't blow up on a midnight time object
    @setup({'date08': '{{ t|date:"H:i" }}'})
    def test_date08(self):
        output = render('date08', {'t': time(0, 1)})
        self.assertEqual(output, '00:01')

    @setup({'date09': '{{ t|date:"H:i" }}'})
    def test_date09(self):
        output = render('date09', {'t': time(0, 0)})
        self.assertEqual(output, '00:00')
