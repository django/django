
from django.utils import dateformat, translation
from unittest import TestCase
import datetime, os, time

class DateFormatTests(TestCase):
    def setUp(self):
        self.old_TZ = os.environ.get('TZ')
        os.environ['TZ'] = 'Europe/Copenhagen'
        translation.activate('en-us')

        try:
            # Check if a timezone has been set
            time.tzset()
            self.tz_tests = True
        except AttributeError:
            # No timezone available. Don't run the tests that require a TZ
            self.tz_tests = False

    def tearDown(self):
        if self.old_TZ is None:
            del os.environ['TZ']
        else:
            os.environ['TZ'] = self.old_TZ

        # Cleanup - force re-evaluation of TZ environment variable.
        if self.tz_tests:
            time.tzset()

    def test_empty_format(self):
        my_birthday = datetime.datetime(1979, 7, 8, 22, 00)

        self.assertEquals(dateformat.format(my_birthday, ''), u'')

    def test_am_pm(self):
        my_birthday = datetime.datetime(1979, 7, 8, 22, 00)

        self.assertEquals(dateformat.format(my_birthday, 'a'), u'p.m.')

    def test_date_formats(self):
        my_birthday = datetime.datetime(1979, 7, 8, 22, 00)
        timestamp = datetime.datetime(2008, 5, 19, 11, 45, 23, 123456)

        self.assertEquals(dateformat.format(my_birthday, 'A'), u'PM')
        self.assertEquals(dateformat.format(timestamp, 'c'), u'2008-05-19 11:45:23.123456')
        self.assertEquals(dateformat.format(my_birthday, 'd'), u'08')
        self.assertEquals(dateformat.format(my_birthday, 'j'), u'8')
        self.assertEquals(dateformat.format(my_birthday, 'l'), u'Sunday')
        self.assertEquals(dateformat.format(my_birthday, 'L'), u'False')
        self.assertEquals(dateformat.format(my_birthday, 'm'), u'07')
        self.assertEquals(dateformat.format(my_birthday, 'M'), u'Jul')
        self.assertEquals(dateformat.format(my_birthday, 'b'), u'jul')
        self.assertEquals(dateformat.format(my_birthday, 'n'), u'7')
        self.assertEquals(dateformat.format(my_birthday, 'N'), u'July')

    def test_time_formats(self):
        my_birthday = datetime.datetime(1979, 7, 8, 22, 00)

        self.assertEquals(dateformat.format(my_birthday, 'P'), u'10 p.m.')
        self.assertEquals(dateformat.format(my_birthday, 's'), u'00')
        self.assertEquals(dateformat.format(my_birthday, 'S'), u'th')
        self.assertEquals(dateformat.format(my_birthday, 't'), u'31')
        self.assertEquals(dateformat.format(my_birthday, 'w'), u'0')
        self.assertEquals(dateformat.format(my_birthday, 'W'), u'27')
        self.assertEquals(dateformat.format(my_birthday, 'y'), u'79')
        self.assertEquals(dateformat.format(my_birthday, 'Y'), u'1979')
        self.assertEquals(dateformat.format(my_birthday, 'z'), u'189')

    def test_dateformat(self):
        my_birthday = datetime.datetime(1979, 7, 8, 22, 00)

        self.assertEquals(dateformat.format(my_birthday, r'Y z \C\E\T'), u'1979 189 CET')

        self.assertEquals(dateformat.format(my_birthday, r'jS o\f F'), u'8th of July')

    def test_futuredates(self):
        the_future = datetime.datetime(2100, 10, 25, 0, 00)
        self.assertEquals(dateformat.format(the_future, r'Y'), u'2100')

    def test_timezones(self):
        my_birthday = datetime.datetime(1979, 7, 8, 22, 00)
        summertime = datetime.datetime(2005, 10, 30, 1, 00)
        wintertime = datetime.datetime(2005, 10, 30, 4, 00)
        timestamp = datetime.datetime(2008, 5, 19, 11, 45, 23, 123456)

        if self.tz_tests:
            self.assertEquals(dateformat.format(my_birthday, 'O'), u'+0100')
            self.assertEquals(dateformat.format(my_birthday, 'r'), u'Sun, 8 Jul 1979 22:00:00 +0100')
            self.assertEquals(dateformat.format(my_birthday, 'T'), u'CET')
            self.assertEquals(dateformat.format(my_birthday, 'U'), u'300315600')
            self.assertEquals(dateformat.format(timestamp, 'u'), u'123456')
            self.assertEquals(dateformat.format(my_birthday, 'Z'), u'3600')
            self.assertEquals(dateformat.format(summertime, 'I'), u'1')
            self.assertEquals(dateformat.format(summertime, 'O'), u'+0200')
            self.assertEquals(dateformat.format(wintertime, 'I'), u'0')
            self.assertEquals(dateformat.format(wintertime, 'O'), u'+0100')
