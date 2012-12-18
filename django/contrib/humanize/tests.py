from __future__ import unicode_literals
import datetime

try:
    import pytz
except ImportError:
    pytz = None

from django.conf import settings
from django.contrib.humanize.templatetags import humanize
from django.template import Template, Context, defaultfilters
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.html import escape
from django.utils.timezone import utc
from django.utils import translation
from django.utils.translation import ugettext as _
from django.utils import tzinfo
from django.utils.unittest import skipIf


# Mock out datetime in some tests so they don't fail occasionally when they
# run too slow. Use a fixed datetime for datetime.now(). DST change in
# America/Chicago (the default time zone) happened on March 11th in 2012.

now = datetime.datetime(2012, 3, 9, 22, 30)

class MockDateTime(datetime.datetime):
    @classmethod
    def now(self, tz=None):
        if tz is None or tz.utcoffset(now) is None:
            return now
        else:
            # equals now.replace(tzinfo=utc)
            return now.replace(tzinfo=tz) + tz.utcoffset(now)


class HumanizeTests(TestCase):

    def humanize_tester(self, test_list, result_list, method):
        # Using max below ensures we go through both lists
        # However, if the lists are not equal length, this raises an exception
        for test_content, result in zip(test_list, result_list):
            t = Template('{%% load humanize %%}{{ test_content|%s }}' % method)
            rendered = t.render(Context(locals())).strip()
            self.assertEqual(rendered, escape(result),
                             msg="%s test failed, produced '%s', should've produced '%s'" % (method, rendered, result))

    def test_ordinal(self):
        test_list = ('1', '2', '3', '4', '11', '12',
                     '13', '101', '102', '103', '111',
                     'something else', None)
        result_list = ('1st', '2nd', '3rd', '4th', '11th',
                       '12th', '13th', '101st', '102nd', '103rd',
                       '111th', 'something else', None)

        self.humanize_tester(test_list, result_list, 'ordinal')

    def test_intcomma(self):
        test_list = (100, 1000, 10123, 10311, 1000000, 1234567.25,
                     '100', '1000', '10123', '10311', '1000000', '1234567.1234567',
                     None)
        result_list = ('100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.25',
                       '100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.1234567',
                     None)

        self.humanize_tester(test_list, result_list, 'intcomma')

    def test_l10n_intcomma(self):
        test_list = (100, 1000, 10123, 10311, 1000000, 1234567.25,
                     '100', '1000', '10123', '10311', '1000000', '1234567.1234567',
                     None)
        result_list = ('100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.25',
                       '100', '1,000', '10,123', '10,311', '1,000,000', '1,234,567.1234567',
                     None)

        with self.settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=False):
            self.humanize_tester(test_list, result_list, 'intcomma')

    def test_intcomma_without_number_grouping(self):
        # Regression for #17414
        with translation.override('ja'):
            with self.settings(USE_L10N=True):
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
        tz_one = tzinfo.FixedOffset(datetime.timedelta(hours=-12))
        tz_two = tzinfo.FixedOffset(datetime.timedelta(hours=12))

        # Can be today or yesterday
        date_one = datetime.datetime(today.year, today.month, today.day, tzinfo=tz_one)
        naturalday_one = humanize.naturalday(date_one)
        # Can be today or tomorrow
        date_two = datetime.datetime(today.year, today.month, today.day, tzinfo=tz_two)
        naturalday_two = humanize.naturalday(date_two)

        # As 24h of difference they will never be the same
        self.assertNotEqual(naturalday_one, naturalday_two)

    @skipIf(settings.TIME_ZONE != "America/Chicago" and pytz is None,
            "this test requires pytz when a non-default time zone is set")
    def test_naturalday_uses_localtime(self):
        # Regression for #18504
        # This is 2012-03-08HT19:30:00-06:00 in America/Chicago
        dt = datetime.datetime(2012, 3, 9, 1, 30, tzinfo=utc)

        orig_humanize_datetime, humanize.datetime = humanize.datetime, MockDateTime
        try:
            with override_settings(TIME_ZONE="America/Chicago", USE_TZ=True):
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
            '30 seconds ago',
            'a minute ago',
            '2 minutes ago',
            'an hour ago',
            '23 hours ago',
            '1 day ago',
            '1 year, 4 months ago',
            'a second from now',
            '30 seconds from now',
            'a minute from now',
            '2 minutes from now',
            'an hour from now',
            '23 hours from now',
            '1 day from now',
            '2 days, 6 hours from now',
            '1 year, 4 months from now',
            'now',
            'now',
        ]
        # Because of the DST change, 2 days and 6 hours after the chosen
        # date in naive arithmetic is only 2 days and 5 hours after in
        # aware arithmetic.
        result_list_with_tz_support = result_list[:]
        assert result_list_with_tz_support[-4] == '2 days, 6 hours from now'
        result_list_with_tz_support[-4] == '2 days, 5 hours from now'

        orig_humanize_datetime, humanize.datetime = humanize.datetime, MockDateTime
        try:
            self.humanize_tester(test_list, result_list, 'naturaltime')
            with override_settings(USE_TZ=True):
                self.humanize_tester(test_list, result_list_with_tz_support, 'naturaltime')
        finally:
            humanize.datetime = orig_humanize_datetime
