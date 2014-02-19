from __future__ import unicode_literals
import datetime
from decimal import Decimal
from unittest import skipIf

try:
    import pytz
except ImportError:
    pytz = None

from django.contrib.humanize.templatetags import humanize
from django.template import Template, Context, defaultfilters
from django.test import TestCase, override_settings
from django.utils.html import escape
from django.utils.timezone import utc, get_fixed_timezone
from django.utils import translation
from django.utils.translation import ugettext as _


# Mock out datetime in some tests so they don't fail occasionally when they
# run too slow. Use a fixed datetime for datetime.now(). DST change in
# America/Chicago (the default time zone) happened on March 11th in 2012.

now = datetime.datetime(2012, 3, 9, 22, 30)


class MockDateTime(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        if tz is None or tz.utcoffset(now) is None:
            return now
        else:
            # equals now.replace(tzinfo=utc)
            return now.replace(tzinfo=tz) + tz.utcoffset(now)


class HumanizeTests(TestCase):

    def humanize_tester(self, test_list, result_list, method, normalize_result_func=escape):
        for test_content, result in zip(test_list, result_list):
            t = Template('{%% load humanize %%}{{ test_content|%s }}' % method)
            rendered = t.render(Context(locals())).strip()
            self.assertEqual(rendered, normalize_result_func(result),
                             msg="%s test failed, produced '%s', should've produced '%s'" % (method, rendered, result))

    def test_ordinal(self):
        test_list = ('1', '2', '3', '4', '11', '12',
                     '13', '101', '102', '103', '111',
                     'something else', None)
        result_list = ('1st', '2nd', '3rd', '4th', '11th',
                       '12th', '13th', '101st', '102nd', '103rd',
                       '111th', 'something else', None)

        with translation.override('en'):
            self.humanize_tester(test_list, result_list, 'ordinal')

    def test_i18n_html_ordinal(self):
        """Allow html in output on i18n strings"""
        test_list = ('1', '2', '3', '4', '11', '12',
                     '13', '101', '102', '103', '111',
                     'something else', None)
        result_list = ('1<sup>er</sup>', '2<sup>e</sup>', '3<sup>e</sup>', '4<sup>e</sup>',
                       '11<sup>e</sup>', '12<sup>e</sup>', '13<sup>e</sup>', '101<sup>er</sup>',
                       '102<sup>e</sup>', '103<sup>e</sup>', '111<sup>e</sup>', 'something else',
                       'None')

        with translation.override('fr-fr'):
            self.humanize_tester(test_list, result_list, 'ordinal', lambda x: x)

    def test_intcomma(self):
        test_list = (100, 1000, 10123, 10311, 1000000, 1234567.25,
                     '100', '1000', '10123', '10311', '1000000', '1234567.1234567', Decimal('1234567.1234567'),
                     None)
        result_list = ('100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.25',
                       '100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.1234567', '1,234,567.1234567',
                     None)

        with translation.override('en'):
            self.humanize_tester(test_list, result_list, 'intcomma')

    def test_l10n_intcomma(self):
        test_list = (100, 1000, 10123, 10311, 1000000, 1234567.25,
                     '100', '1000', '10123', '10311', '1000000', '1234567.1234567', Decimal('1234567.1234567'),
                     None)
        result_list = ('100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.25',
                       '100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.1234567', '1,234,567.1234567',
                     None)

        with self.settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=False):
            with translation.override('en'):
                self.humanize_tester(test_list, result_list, 'intcomma')

    def test_intcomma_without_number_grouping(self):
        # Regression for #17414
        with translation.override('ja'), self.settings(USE_L10N=True):
            self.humanize_tester([100], ['100'], 'intcomma')

    def test_intword(self):
        test_list = ('100', '1000000', '1200000', '1290000',
                     '1000000000', '2000000000', '6000000000000',
                     '1300000000000000', '3500000000000000000000',
                     '8100000000000000000000000000000000', None)
        result_list = ('100', '1.0 million', '1.2 million', '1.3 million',
                       '1.0 billion', '2.0 billion', '6.0 trillion',
                       '1.3 quadrillion', '3.5 sextillion',
                       '8.1 decillion', None)
        with translation.override('en'):
            self.humanize_tester(test_list, result_list, 'intword')

    def test_i18n_intcomma(self):
        test_list = (100, 1000, 10123, 10311, 1000000, 1234567.25,
                     '100', '1000', '10123', '10311', '1000000', None)
        result_list = ('100', '1.000', '10.123', '10.311', '1.000.000', '1.234.567,25',
                       '100', '1.000', '10.123', '10.311', '1.000.000', None)
        with self.settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True):
            with translation.override('de'):
                self.humanize_tester(test_list, result_list, 'intcomma')

    def test_i18n_intword(self):
        test_list = ('100', '1000000', '1200000', '1290000',
                     '1000000000', '2000000000', '6000000000000')
        result_list = ('100', '1,0 Million', '1,2 Millionen', '1,3 Millionen',
                       '1,0 Milliarde', '2,0 Milliarden', '6,0 Billionen')
        with self.settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True):
            with translation.override('de'):
                self.humanize_tester(test_list, result_list, 'intword')

    def test_apnumber(self):
        test_list = [str(x) for x in range(1, 11)]
        test_list.append(None)
        result_list = ('one', 'two', 'three', 'four', 'five', 'six',
                       'seven', 'eight', 'nine', '10', None)
        with translation.override('en'):
            self.humanize_tester(test_list, result_list, 'apnumber')

    def test_naturalday(self):
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)
        someday = today - datetime.timedelta(days=10)
        notdate = "I'm not a date value"

        test_list = (today, yesterday, tomorrow, someday, notdate, None)
        someday_result = defaultfilters.date(someday)
        result_list = (_('today'), _('yesterday'), _('tomorrow'),
                       someday_result, "I'm not a date value", None)
        self.humanize_tester(test_list, result_list, 'naturalday')

    def test_naturalday_tz(self):
        today = datetime.date.today()
        tz_one = get_fixed_timezone(-720)
        tz_two = get_fixed_timezone(720)

        # Can be today or yesterday
        date_one = datetime.datetime(today.year, today.month, today.day, tzinfo=tz_one)
        naturalday_one = humanize.naturalday(date_one)
        # Can be today or tomorrow
        date_two = datetime.datetime(today.year, today.month, today.day, tzinfo=tz_two)
        naturalday_two = humanize.naturalday(date_two)

        # As 24h of difference they will never be the same
        self.assertNotEqual(naturalday_one, naturalday_two)

    @skipIf(pytz is None, "this test requires pytz")
    def test_naturalday_uses_localtime(self):
        # Regression for #18504
        # This is 2012-03-08HT19:30:00-06:00 in America/Chicago
        dt = datetime.datetime(2012, 3, 9, 1, 30, tzinfo=utc)

        orig_humanize_datetime, humanize.datetime = humanize.datetime, MockDateTime
        try:
            with override_settings(TIME_ZONE="America/Chicago", USE_TZ=True):
                with translation.override('en'):
                    self.humanize_tester([dt], ['yesterday'], 'naturalday')
        finally:
            humanize.datetime = orig_humanize_datetime

    def test_naturaltime(self):
        class naive(datetime.tzinfo):
            def utcoffset(self, dt):
                return None
        test_list = [
            now,
            now - datetime.timedelta(seconds=1),
            now - datetime.timedelta(seconds=30),
            now - datetime.timedelta(minutes=1, seconds=30),
            now - datetime.timedelta(minutes=2),
            now - datetime.timedelta(hours=1, minutes=30, seconds=30),
            now - datetime.timedelta(hours=23, minutes=50, seconds=50),
            now - datetime.timedelta(days=1),
            now - datetime.timedelta(days=500),
            now + datetime.timedelta(seconds=1),
            now + datetime.timedelta(seconds=30),
            now + datetime.timedelta(minutes=1, seconds=30),
            now + datetime.timedelta(minutes=2),
            now + datetime.timedelta(hours=1, minutes=30, seconds=30),
            now + datetime.timedelta(hours=23, minutes=50, seconds=50),
            now + datetime.timedelta(days=1),
            now + datetime.timedelta(days=2, hours=6),
            now + datetime.timedelta(days=500),
            now.replace(tzinfo=naive()),
            now.replace(tzinfo=utc),
        ]
        result_list = [
            'now',
            'a second ago',
            '30\xa0seconds ago',
            'a minute ago',
            '2\xa0minutes ago',
            'an hour ago',
            '23\xa0hours ago',
            '1\xa0day ago',
            '1\xa0year, 4\xa0months ago',
            'a second from now',
            '30\xa0seconds from now',
            'a minute from now',
            '2\xa0minutes from now',
            'an hour from now',
            '23\xa0hours from now',
            '1\xa0day from now',
            '2\xa0days, 6\xa0hours from now',
            '1\xa0year, 4\xa0months from now',
            'now',
            'now',
        ]
        # Because of the DST change, 2 days and 6 hours after the chosen
        # date in naive arithmetic is only 2 days and 5 hours after in
        # aware arithmetic.
        result_list_with_tz_support = result_list[:]
        assert result_list_with_tz_support[-4] == '2\xa0days, 6\xa0hours from now'
        result_list_with_tz_support[-4] == '2\xa0days, 5\xa0hours from now'

        orig_humanize_datetime, humanize.datetime = humanize.datetime, MockDateTime
        try:
            with translation.override('en'):
                self.humanize_tester(test_list, result_list, 'naturaltime')
                with override_settings(USE_TZ=True):
                    self.humanize_tester(
                        test_list, result_list_with_tz_support, 'naturaltime')
        finally:
            humanize.datetime = orig_humanize_datetime
