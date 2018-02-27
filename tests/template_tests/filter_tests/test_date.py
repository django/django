from datetime import datetime, time

from django.template.defaultfilters import date
from django.test import SimpleTestCase, override_settings
from django.utils import timezone, translation

from ..utils import setup
from .timezone_utils import TimezoneTestCase


class DateTests(TimezoneTestCase):

    @setup({'date01': '{{ d|date:"m" }}'})
    def test_date01(self):
        output = self.engine.render_to_string('date01', {'d': datetime(2008, 1, 1)})
        self.assertEqual(output, '01')

    @setup({'date02': '{{ d|date }}'})
    def test_date02(self):
        output = self.engine.render_to_string('date02', {'d': datetime(2008, 1, 1)})
        self.assertEqual(output, 'Jan. 1, 2008')

    @override_settings(USE_L10N=True)
    @setup({'date02_l10n': '{{ d|date }}'})
    def test_date02_l10n(self):
        """
        Without arg and when USE_L10N is True, the active language's DATE_FORMAT
        is used.
        """
        with translation.override('fr'):
            output = self.engine.render_to_string('date02_l10n', {'d': datetime(2008, 1, 1)})
        self.assertEqual(output, '1 janvier 2008')

    @setup({'date03': '{{ d|date:"m" }}'})
    def test_date03(self):
        """
        #9520: Make sure |date doesn't blow up on non-dates
        """
        output = self.engine.render_to_string('date03', {'d': 'fail_string'})
        self.assertEqual(output, '')

    # ISO date formats
    @setup({'date04': '{{ d|date:"o" }}'})
    def test_date04(self):
        output = self.engine.render_to_string('date04', {'d': datetime(2008, 12, 29)})
        self.assertEqual(output, '2009')

    @setup({'date05': '{{ d|date:"o" }}'})
    def test_date05(self):
        output = self.engine.render_to_string('date05', {'d': datetime(2010, 1, 3)})
        self.assertEqual(output, '2009')

    # Timezone name
    @setup({'date06': '{{ d|date:"e" }}'})
    def test_date06(self):
        output = self.engine.render_to_string(
            'date06', {'d': datetime(2009, 3, 12, tzinfo=timezone.get_fixed_timezone(30))}
        )
        self.assertEqual(output, '+0030')

    @setup({'date07': '{{ d|date:"e" }}'})
    def test_date07(self):
        output = self.engine.render_to_string('date07', {'d': datetime(2009, 3, 12)})
        self.assertEqual(output, '')

    # #19370: Make sure |date doesn't blow up on a midnight time object
    @setup({'date08': '{{ t|date:"H:i" }}'})
    def test_date08(self):
        output = self.engine.render_to_string('date08', {'t': time(0, 1)})
        self.assertEqual(output, '00:01')

    @setup({'date09': '{{ t|date:"H:i" }}'})
    def test_date09(self):
        output = self.engine.render_to_string('date09', {'t': time(0, 0)})
        self.assertEqual(output, '00:00')


class FunctionTests(SimpleTestCase):

    def test_date(self):
        self.assertEqual(date(datetime(2005, 12, 29), "d F Y"), '29 December 2005')

    def test_no_args(self):
        self.assertEqual(date(''), '')
        self.assertEqual(date(None), '')

    def test_escape_characters(self):
        self.assertEqual(date(datetime(2005, 12, 29), r'jS \o\f F'), '29th of December')
