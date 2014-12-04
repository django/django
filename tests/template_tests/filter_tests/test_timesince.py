from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.test.utils import requires_tz_support

from .timezone_utils import TimezoneTestCase
from ..utils import render, setup


class TimesinceTests(TimezoneTestCase):
    """
    #20246 - \xa0 in output avoids line-breaks between value and unit
    """

    # Default compare with datetime.now()
    @setup({'timesince01': '{{ a|timesince }}'})
    def test_timesince01(self):
        output = render('timesince01', {'a': datetime.now() + timedelta(minutes=-1, seconds=-10)})
        self.assertEqual(output, '1\xa0minute')

    @setup({'timesince02': '{{ a|timesince }}'})
    def test_timesince02(self):
        output = render('timesince02', {'a': datetime.now() - timedelta(days=1, minutes=1)})
        self.assertEqual(output, '1\xa0day')

    @setup({'timesince03': '{{ a|timesince }}'})
    def test_timesince03(self):
        output = render('timesince03', {'a': datetime.now() - timedelta(hours=1, minutes=25, seconds=10)})
        self.assertEqual(output, '1\xa0hour, 25\xa0minutes')

    # Compare to a given parameter
    @setup({'timesince04': '{{ a|timesince:b }}'})
    def test_timesince04(self):
        output = render(
            'timesince04',
            {'a': self.now - timedelta(days=2), 'b': self.now - timedelta(days=1)},
        )
        self.assertEqual(output, '1\xa0day')

    @setup({'timesince05': '{{ a|timesince:b }}'})
    def test_timesince05(self):
        output = render(
            'timesince05',
            {'a': self.now - timedelta(days=2, minutes=1), 'b': self.now - timedelta(days=2)},
        )
        self.assertEqual(output, '1\xa0minute')

    # Check that timezone is respected
    @setup({'timesince06': '{{ a|timesince:b }}'})
    def test_timesince06(self):
        output = render('timesince06', {'a': self.now_tz - timedelta(hours=8), 'b': self.now_tz})
        self.assertEqual(output, '8\xa0hours')

    # Tests for #7443
    @setup({'timesince07': '{{ earlier|timesince }}'})
    def test_timesince07(self):
        output = render('timesince07', {'earlier': self.now - timedelta(days=7)})
        self.assertEqual(output, '1\xa0week')

    @setup({'timesince08': '{{ earlier|timesince:now }}'})
    def test_timesince08(self):
        output = render('timesince08', {'now': self.now, 'earlier': self.now - timedelta(days=7)})
        self.assertEqual(output, '1\xa0week')

    @setup({'timesince09': '{{ later|timesince }}'})
    def test_timesince09(self):
        output = render('timesince09', {'later': self.now + timedelta(days=7)})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince10': '{{ later|timesince:now }}'})
    def test_timesince10(self):
        output = render('timesince10', {'now': self.now, 'later': self.now + timedelta(days=7)})
        self.assertEqual(output, '0\xa0minutes')

    # Ensures that differing timezones are calculated correctly.
    @setup({'timesince11': '{{ a|timesince }}'})
    def test_timesince11(self):
        output = render('timesince11', {'a': self.now})
        self.assertEqual(output, '0\xa0minutes')

    @requires_tz_support
    @setup({'timesince12': '{{ a|timesince }}'})
    def test_timesince12(self):
        output = render('timesince12', {'a': self.now_tz})
        self.assertEqual(output, '0\xa0minutes')

    @requires_tz_support
    @setup({'timesince13': '{{ a|timesince }}'})
    def test_timesince13(self):
        output = render('timesince13', {'a': self.now_tz_i})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince14': '{{ a|timesince:b }}'})
    def test_timesince14(self):
        output = render('timesince14', {'a': self.now_tz, 'b': self.now_tz_i})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince15': '{{ a|timesince:b }}'})
    def test_timesince15(self):
        output = render('timesince15', {'a': self.now, 'b': self.now_tz_i})
        self.assertEqual(output, '')

    @setup({'timesince16': '{{ a|timesince:b }}'})
    def test_timesince16(self):
        output = render('timesince16', {'a': self.now_tz_i, 'b': self.now})
        self.assertEqual(output, '')

    # Tests for #9065 (two date objects).
    @setup({'timesince17': '{{ a|timesince:b }}'})
    def test_timesince17(self):
        output = render('timesince17', {'a': self.today, 'b': self.today})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince18': '{{ a|timesince:b }}'})
    def test_timesince18(self):
        output = render('timesince18', {'a': self.today, 'b': self.today + timedelta(hours=24)})
        self.assertEqual(output, '1\xa0day')
