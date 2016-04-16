import datetime

from django.db import models
from django.test import (
    SimpleTestCase, TestCase, mock, override_settings, skipUnlessDBFeature,
)
from django.test.utils import requires_tz_support
from django.utils import timezone

from .models import DateTimeModel


class DateTimeFieldTests(TestCase):

    def test_datetimefield_to_python_microseconds(self):
        """DateTimeField.to_python() supports microseconds."""
        f = models.DateTimeField()
        self.assertEqual(f.to_python('2001-01-02 03:04:05.000006'), datetime.datetime(2001, 1, 2, 3, 4, 5, 6))
        self.assertEqual(f.to_python('2001-01-02 03:04:05.999999'), datetime.datetime(2001, 1, 2, 3, 4, 5, 999999))

    def test_timefield_to_python_microseconds(self):
        """TimeField.to_python() supports microseconds."""
        f = models.TimeField()
        self.assertEqual(f.to_python('01:02:03.000004'), datetime.time(1, 2, 3, 4))
        self.assertEqual(f.to_python('01:02:03.999999'), datetime.time(1, 2, 3, 999999))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_datetimes_save_completely(self):
        dat = datetime.date(2014, 3, 12)
        datetim = datetime.datetime(2014, 3, 12, 21, 22, 23, 240000)
        tim = datetime.time(21, 22, 23, 240000)
        DateTimeModel.objects.create(d=dat, dt=datetim, t=tim)
        obj = DateTimeModel.objects.first()
        self.assertTrue(obj)
        self.assertEqual(obj.d, dat)
        self.assertEqual(obj.dt, datetim)
        self.assertEqual(obj.t, tim)

    @override_settings(USE_TZ=False)
    def test_lookup_date_without_use_tz(self):
        d = datetime.date(2014, 3, 12)
        dt1 = datetime.datetime(2014, 3, 12, 21, 22, 23, 240000)
        dt2 = datetime.datetime(2014, 3, 11, 21, 22, 23, 240000)
        t = datetime.time(21, 22, 23, 240000)
        m = DateTimeModel.objects.create(d=d, dt=dt1, t=t)
        # Other model with different datetime.
        DateTimeModel.objects.create(d=d, dt=dt2, t=t)
        self.assertEqual(m, DateTimeModel.objects.get(dt__date=d))

    @requires_tz_support
    @skipUnlessDBFeature('has_zoneinfo_database')
    @override_settings(USE_TZ=True, TIME_ZONE='America/Vancouver')
    def test_lookup_date_with_use_tz(self):
        d = datetime.date(2014, 3, 12)
        # The following is equivalent to UTC 2014-03-12 18:34:23.24000.
        dt1 = datetime.datetime(2014, 3, 12, 10, 22, 23, 240000, tzinfo=timezone.get_current_timezone())
        # The following is equivalent to UTC 2014-03-13 05:34:23.24000.
        dt2 = datetime.datetime(2014, 3, 12, 21, 22, 23, 240000, tzinfo=timezone.get_current_timezone())
        t = datetime.time(21, 22, 23, 240000)
        m1 = DateTimeModel.objects.create(d=d, dt=dt1, t=t)
        m2 = DateTimeModel.objects.create(d=d, dt=dt2, t=t)
        # In Vancouver, we expect both results.
        self.assertQuerysetEqual(
            DateTimeModel.objects.filter(dt__date=d),
            [repr(m1), repr(m2)],
            ordered=False
        )
        with self.settings(TIME_ZONE='UTC'):
            # But in UTC, the __date only matches one of them.
            self.assertQuerysetEqual(DateTimeModel.objects.filter(dt__date=d), [repr(m1)])

    def test_to_python_mock_support(self):
        """
        to_python() method of DateField, DateTimeField and TimeField should
        handle mocked values (#21523).
        """
        class FakeDate(datetime.date):
            """
            Mock date class.
            """
            pass

        with mock.patch('datetime.date', FakeDate):
            # this will create a mock date
            fake_date = datetime.date.today()
            # this will force the creation of a 'real' date (i.e. not the mock)
            real_date = fake_date + datetime.timedelta(days=1)
            # DateField.to_python does an isinstance(value, datetime.date) check -
            # when we are mocking out datetime.date with our FakeDate class
            # then this test will FAIL if value is a real date object, which
            # is the case with issue #21523.
            self.assertIsInstance(fake_date, datetime.date)
            self.assertNotIsInstance(real_date, datetime.date)

            # if #21523 is not fixed, a call to to_python with a real date,
            # e.g. the 'tomorrow' value, will raise a TypeError.
            # What we want is for both FakeDate and real datetime.date objects
            # to pass through unchanged.
            f = models.DateField()
            self.assertEqual(f.to_python(fake_date), fake_date)
            self.assertEqual(f.to_python(real_date), real_date)

        class FakeDateTime(datetime.datetime):
            """
            Mock datetime class.
            """
            pass

        with mock.patch('datetime.datetime', FakeDateTime):
            fake_dt = datetime.datetime.today()
            real_dt = fake_dt + datetime.timedelta(days=1)
            self.assertIsInstance(fake_dt, datetime.datetime)
            self.assertNotIsInstance(real_dt, datetime.datetime)

            f = models.DateTimeField()
            self.assertEqual(f.to_python(fake_dt), fake_dt)
            self.assertEqual(f.to_python(real_dt), real_dt)

        class FakeTime(datetime.time):
            """
            Mock time class.
            """
            pass

        real_time = datetime.time(1, 3, 2)
        with mock.patch('datetime.time', FakeTime):
            fake_time = datetime.time(1, 3, 2)
            self.assertIsInstance(fake_time, datetime.time)
            self.assertNotIsInstance(real_time, datetime.time)

            f = models.TimeField()
            self.assertEqual(f.to_python(fake_time), fake_time)
            self.assertEqual(f.to_python(real_time), real_time)


class ValidationTest(SimpleTestCase):

    def test_datefield_cleans_date(self):
        f = models.DateField()
        self.assertEqual(datetime.date(2008, 10, 10), f.clean('2008-10-10', None))
