from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.test.utils import requires_tz_support

from .timezone_utils import TimezoneTestCase
from ..utils import render, setup


class TimeuntilTests(TimezoneTestCase):

    # Default compare with datetime.now()
    @setup({'timeuntil01': '{{ a|timeuntil }}'})
    def test_timeuntil01(self):
        output = render('timeuntil01', {'a': datetime.now() + timedelta(minutes=2, seconds=10)})
        self.assertEqual(output, '2\xa0minutes')

    @setup({'timeuntil02': '{{ a|timeuntil }}'})
    def test_timeuntil02(self):
        output = render('timeuntil02', {'a': (datetime.now() + timedelta(days=1, seconds=10))})
        self.assertEqual(output, '1\xa0day')

    @setup({'timeuntil03': '{{ a|timeuntil }}'})
    def test_timeuntil03(self):
        output = render('timeuntil03', {'a': (datetime.now() + timedelta(hours=8, minutes=10, seconds=10))})
        self.assertEqual(output, '8\xa0hours, 10\xa0minutes')

    # Compare to a given parameter
    @setup({'timeuntil04': '{{ a|timeuntil:b }}'})
    def test_timeuntil04(self):
        output = render(
            'timeuntil04',
            {'a': self.now - timedelta(days=1), 'b': self.now - timedelta(days=2)},
        )
        self.assertEqual(output, '1\xa0day')

    @setup({'timeuntil05': '{{ a|timeuntil:b }}'})
    def test_timeuntil05(self):
        output = render(
            'timeuntil05',
            {'a': self.now - timedelta(days=2), 'b': self.now - timedelta(days=2, minutes=1)},
        )
        self.assertEqual(output, '1\xa0minute')

    # Regression for #7443
    @setup({'timeuntil06': '{{ earlier|timeuntil }}'})
    def test_timeuntil06(self):
        output = render('timeuntil06', {'earlier': self.now - timedelta(days=7)})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timeuntil07': '{{ earlier|timeuntil:now }}'})
    def test_timeuntil07(self):
        output = render('timeuntil07', {'now': self.now, 'earlier': self.now - timedelta(days=7)})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timeuntil08': '{{ later|timeuntil }}'})
    def test_timeuntil08(self):
        output = render('timeuntil08', {'later': self.now + timedelta(days=7, hours=1)})
        self.assertEqual(output, '1\xa0week')

    @setup({'timeuntil09': '{{ later|timeuntil:now }}'})
    def test_timeuntil09(self):
        output = render('timeuntil09', {'now': self.now, 'later': self.now + timedelta(days=7)})
        self.assertEqual(output, '1\xa0week')

    # Ensures that differing timezones are calculated correctly.
    @requires_tz_support
    @setup({'timeuntil10': '{{ a|timeuntil }}'})
    def test_timeuntil10(self):
        output = render('timeuntil10', {'a': self.now_tz})
        self.assertEqual(output, '0\xa0minutes')

    @requires_tz_support
    @setup({'timeuntil11': '{{ a|timeuntil }}'})
    def test_timeuntil11(self):
        output = render('timeuntil11', {'a': self.now_tz_i})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timeuntil12': '{{ a|timeuntil:b }}'})
    def test_timeuntil12(self):
        output = render('timeuntil12', {'a': self.now_tz_i, 'b': self.now_tz})
        self.assertEqual(output, '0\xa0minutes')

    # Regression for #9065 (two date objects).
    @setup({'timeuntil13': '{{ a|timeuntil:b }}'})
    def test_timeuntil13(self):
        output = render('timeuntil13', {'a': self.today, 'b': self.today})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timeuntil14': '{{ a|timeuntil:b }}'})
    def test_timeuntil14(self):
        output = render('timeuntil14', {'a': self.today, 'b': self.today - timedelta(hours=24)})
        self.assertEqual(output, '1\xa0day')
