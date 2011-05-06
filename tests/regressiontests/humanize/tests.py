from __future__ import with_statement
from datetime import timedelta, date, datetime, tzinfo, timedelta

from django.conf import settings
from django.template import Template, Context, add_to_builtins
from django.test import TestCase
from django.utils import translation
from django.utils.dateformat import DateFormat
from django.utils.translation import ugettext as _
from django.utils.html import escape
from django.conf import settings

add_to_builtins('django.contrib.humanize.templatetags.humanize')


class FixedOffset(tzinfo):
    """Fixed offset in hours east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(hours=offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)


class HumanizeTests(TestCase):

    def humanize_tester(self, test_list, result_list, method):
        # Using max below ensures we go through both lists
        # However, if the lists are not equal length, this raises an exception
        for index in xrange(max(len(test_list), len(result_list))):
            test_content = test_list[index]
            t = Template('{{ test_content|%s }}' % method)
            rendered = t.render(Context(locals())).strip()
            self.assertEqual(rendered, escape(result_list[index]),
                             msg="%s test failed, produced %s, should've produced %s" % (method, rendered, result_list[index]))

    def test_ordinal(self):
        test_list = ('1','2','3','4','11','12',
                     '13','101','102','103','111',
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

    def test_intword(self):
        test_list = ('100', '1000000', '1200000', '1290000',
                     '1000000000', '2000000000', '6000000000000',
                     None)
        result_list = ('100', '1.0 million', '1.2 million', '1.3 million',
                       '1.0 billion', '2.0 billion', '6.0 trillion',
                       None)
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
                     '1000000000','2000000000','6000000000000')
        result_list = ('100', '1,0 Million', '1,2 Millionen', '1,3 Millionen',
                       '1,0 Milliarde', '2,0 Milliarden', '6,0 Billionen')
        with self.settings(USE_L10N=True, USE_THOUSAND_SEPARATOR=True):
            with translation.override('de'):
                self.humanize_tester(test_list, result_list, 'intword')

    def test_apnumber(self):
        test_list = [str(x) for x in range(1, 11)]
        test_list.append(None)
        result_list = (u'one', u'two', u'three', u'four', u'five', u'six',
                       u'seven', u'eight', u'nine', u'10', None)

        self.humanize_tester(test_list, result_list, 'apnumber')

    def test_naturalday(self):
        from django.template import defaultfilters
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        someday = today - timedelta(days=10)
        notdate = u"I'm not a date value"

        test_list = (today, yesterday, tomorrow, someday, notdate, None)
        someday_result = defaultfilters.date(someday)
        result_list = (_(u'today'), _(u'yesterday'), _(u'tomorrow'),
                       someday_result, u"I'm not a date value", None)
        self.humanize_tester(test_list, result_list, 'naturalday')

    def test_naturaltime(self):
        from django.template import defaultfilters
        now = datetime.now()
        seconds_ago = now - timedelta(seconds=30)
        a_minute_ago = now - timedelta(minutes=1, seconds=30)
        minutes_ago = now - timedelta(minutes=2)
        an_hour_ago = now - timedelta(hours=1, minutes=30, seconds=30)
        hours_ago = now - timedelta(hours=23, minutes=50, seconds=50)

        test_list = (now, a_minute_ago, an_hour_ago)
        result_list = (_(u'now'), _(u'a minute ago'), _(u'an hour ago'))
        self.humanize_tester(test_list, result_list, 'naturaltime')

        t = Template('{{ seconds_ago|%s }}' % 'naturaltime')
        rendered = t.render(Context(locals())).strip()
        self.assertTrue(u' seconds ago' in rendered)

        t = Template('{{ minutes_ago|%s }}' % 'naturaltime')
        rendered = t.render(Context(locals())).strip()
        self.assertTrue(u' minutes ago' in rendered)

        t = Template('{{ hours_ago|%s }}' % 'naturaltime')
        rendered = t.render(Context(locals())).strip()
        self.assertTrue(u' hours ago' in rendered)

    def test_naturalday_tz(self):
        from django.contrib.humanize.templatetags.humanize import naturalday

        today = date.today()
        tz_one = FixedOffset(-12, 'TzOne')
        tz_two = FixedOffset(12, 'TzTwo')

        # Can be today or yesterday
        date_one = datetime(today.year, today.month, today.day, tzinfo=tz_one)
        naturalday_one = naturalday(date_one)
        # Can be today or tomorrow
        date_two = datetime(today.year, today.month, today.day, tzinfo=tz_two)
        naturalday_two = naturalday(date_two)

        # As 24h of difference they will never be the same
        self.assertNotEqual(naturalday_one, naturalday_two)
