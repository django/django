from datetime import time

from django.template.defaultfilters import time as time_filter
from django.test import SimpleTestCase
from django.utils import timezone

from ..utils import setup
from .timezone_utils import TimezoneTestCase


class TimeTests(TimezoneTestCase):
    """
    #20693: Timezone support for the time template filter
    """

    @setup({'time01': '{{ dt|time:"e:O:T:Z" }}'})
    def test_time01(self):
        output = self.engine.render_to_string('time01', {'dt': self.now_tz_i})
        self.assertEqual(output, '+0315:+0315:+0315:11700')

    @setup({'time02': '{{ dt|time:"e:T" }}'})
    def test_time02(self):
        output = self.engine.render_to_string('time02', {'dt': self.now})
        self.assertEqual(output, ':' + self.now_tz.tzinfo.tzname(self.now_tz))

    @setup({'time03': '{{ t|time:"P:e:O:T:Z" }}'})
    def test_time03(self):
        output = self.engine.render_to_string('time03', {'t': time(4, 0, tzinfo=timezone.get_fixed_timezone(30))})
        self.assertEqual(output, '4 a.m.::::')

    @setup({'time04': '{{ t|time:"P:e:O:T:Z" }}'})
    def test_time04(self):
        output = self.engine.render_to_string('time04', {'t': time(4, 0)})
        self.assertEqual(output, '4 a.m.::::')

    @setup({'time05': '{{ d|time:"P:e:O:T:Z" }}'})
    def test_time05(self):
        output = self.engine.render_to_string('time05', {'d': self.today})
        self.assertEqual(output, '')

    @setup({'time06': '{{ obj|time:"P:e:O:T:Z" }}'})
    def test_time06(self):
        output = self.engine.render_to_string('time06', {'obj': 'non-datetime-value'})
        self.assertEqual(output, '')


class FunctionTests(SimpleTestCase):

    def test_inputs(self):
        self.assertEqual(time_filter(time(13), 'h'), '01')
        self.assertEqual(time_filter(time(0), 'h'), '12')
