import os
from unittest import TestCase
from datetime import datetime, date
from django.utils.dateformat import format
from django.utils.tzinfo import FixedOffset, LocalTimezone

class DateFormatTests(TestCase):
    def setUp(self):
        self.old_TZ = os.environ['TZ']
        os.environ['TZ'] = 'Europe/Copenhagen'

    def tearDown(self):
        os.environ['TZ'] = self.old_TZ

    def test_date(self):
        d = date(2009, 5, 16)
        self.assertEquals(date.fromtimestamp(int(format(d, 'U'))), d)

    def test_naive_datetime(self):
        dt = datetime(2009, 5, 16, 5, 30, 30)
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U'))), dt)

    def test_datetime_with_local_tzinfo(self):
        ltz = LocalTimezone(datetime.now())
        dt = datetime(2009, 5, 16, 5, 30, 30, tzinfo=ltz)
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U')), ltz), dt)
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U'))), dt.replace(tzinfo=None))

    def test_datetime_with_tzinfo(self):
        tz = FixedOffset(-510)
        ltz = LocalTimezone(datetime.now())
        dt = datetime(2009, 5, 16, 5, 30, 30, tzinfo=tz)
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U')), tz), dt)
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U')), ltz), dt)
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U'))), dt.astimezone(ltz).replace(tzinfo=None))
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U')), tz).utctimetuple(), dt.utctimetuple())
        self.assertEquals(datetime.fromtimestamp(int(format(dt, 'U')), ltz).utctimetuple(), dt.utctimetuple())

    def test_epoch(self):
        utc = FixedOffset(0)
        udt = datetime(1970, 1, 1, tzinfo=utc)
        self.assertEquals(format(udt, 'U'), u'0')
