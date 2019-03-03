from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.template.defaultfilters import timesince_filter
from django.test import SimpleTestCase
from django.test.utils import requires_tz_support

from ..utils import setup
from .timezone_utils import TimezoneTestCase


class TimesinceTests(TimezoneTestCase):
    """
    #20246 - \xa0 in output avoids line-breaks between value and unit
    """

    # Default compare with datetime.now()
    @setup({'timesince01': '{{ a|timesince }}'})
    def test_timesince01(self):
        output = self.engine.render_to_string(
            'timesince01', {'a': datetime.now() + timedelta(minutes=-1, seconds=-10)}
        )
        self.assertEqual(output, '1\xa0minute')

    @setup({'timesince02': '{{ a|timesince }}'})
    def test_timesince02(self):
        output = self.engine.render_to_string(
            'timesince02', {'a': datetime.now() - timedelta(days=1, minutes=1)}
        )
        self.assertEqual(output, '1\xa0day')

    @setup({'timesince03': '{{ a|timesince }}'})
    def test_timesince03(self):
        output = self.engine.render_to_string(
            'timesince03', {'a': datetime.now() - timedelta(hours=1, minutes=25, seconds=10)}
        )
        self.assertEqual(output, '1\xa0hour, 25\xa0minutes')

    # Compare to a given parameter
    @setup({'timesince04': '{{ a|timesince:b }}'})
    def test_timesince04(self):
        output = self.engine.render_to_string(
            'timesince04',
            {'a': self.now - timedelta(days=2), 'b': self.now - timedelta(days=1)},
        )
        self.assertEqual(output, '1\xa0day')

    @setup({'timesince05': '{{ a|timesince:b }}'})
    def test_timesince05(self):
        output = self.engine.render_to_string(
            'timesince05',
            {'a': self.now - timedelta(days=2, minutes=1), 'b': self.now - timedelta(days=2)},
        )
        self.assertEqual(output, '1\xa0minute')

    # Timezone is respected
    @setup({'timesince06': '{{ a|timesince:b }}'})
    def test_timesince06(self):
        output = self.engine.render_to_string('timesince06', {'a': self.now_tz - timedelta(hours=8), 'b': self.now_tz})
        self.assertEqual(output, '8\xa0hours')

    # Tests for #7443
    @setup({'timesince07': '{{ earlier|timesince }}'})
    def test_timesince07(self):
        output = self.engine.render_to_string('timesince07', {'earlier': self.now - timedelta(days=7)})
        self.assertEqual(output, '1\xa0week')

    @setup({'timesince08': '{{ earlier|timesince:now }}'})
    def test_timesince08(self):
        output = self.engine.render_to_string(
            'timesince08', {'now': self.now, 'earlier': self.now - timedelta(days=7)}
        )
        self.assertEqual(output, '1\xa0week')

    @setup({'timesince09': '{{ later|timesince }}'})
    def test_timesince09(self):
        output = self.engine.render_to_string('timesince09', {'later': self.now + timedelta(days=7)})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince10': '{{ later|timesince:now }}'})
    def test_timesince10(self):
        output = self.engine.render_to_string('timesince10', {'now': self.now, 'later': self.now + timedelta(days=7)})
        self.assertEqual(output, '0\xa0minutes')

    # Differing timezones are calculated correctly.
    @setup({'timesince11': '{{ a|timesince }}'})
    def test_timesince11(self):
        output = self.engine.render_to_string('timesince11', {'a': self.now})
        self.assertEqual(output, '0\xa0minutes')

    @requires_tz_support
    @setup({'timesince12': '{{ a|timesince }}'})
    def test_timesince12(self):
        output = self.engine.render_to_string('timesince12', {'a': self.now_tz})
        self.assertEqual(output, '0\xa0minutes')

    @requires_tz_support
    @setup({'timesince13': '{{ a|timesince }}'})
    def test_timesince13(self):
        output = self.engine.render_to_string('timesince13', {'a': self.now_tz_i})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince14': '{{ a|timesince:b }}'})
    def test_timesince14(self):
        output = self.engine.render_to_string('timesince14', {'a': self.now_tz, 'b': self.now_tz_i})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince15': '{{ a|timesince:b }}'})
    def test_timesince15(self):
        output = self.engine.render_to_string('timesince15', {'a': self.now, 'b': self.now_tz_i})
        self.assertEqual(output, '')

    @setup({'timesince16': '{{ a|timesince:b }}'})
    def test_timesince16(self):
        output = self.engine.render_to_string('timesince16', {'a': self.now_tz_i, 'b': self.now})
        self.assertEqual(output, '')

    # Tests for #9065 (two date objects).
    @setup({'timesince17': '{{ a|timesince:b }}'})
    def test_timesince17(self):
        output = self.engine.render_to_string('timesince17', {'a': self.today, 'b': self.today})
        self.assertEqual(output, '0\xa0minutes')

    @setup({'timesince18': '{{ a|timesince:b }}'})
    def test_timesince18(self):
        output = self.engine.render_to_string('timesince18', {'a': self.today, 'b': self.today + timedelta(hours=24)})
        self.assertEqual(output, '1\xa0day')


class FunctionTests(SimpleTestCase):

    def test_since_now(self):
        self.assertEqual(timesince_filter(datetime.now() - timedelta(1)), '1\xa0day')

    def test_explicit_date(self):
        self.assertEqual(timesince_filter(datetime(2005, 12, 29), datetime(2005, 12, 30)), '1\xa0day')
