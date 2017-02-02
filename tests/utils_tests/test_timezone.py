import datetime
import pickle
from unittest import mock

import pytz

from django.test import SimpleTestCase, override_settings
from django.utils import timezone

CET = pytz.timezone("Europe/Paris")
EAT = timezone.get_fixed_timezone(180)      # Africa/Nairobi
ICT = timezone.get_fixed_timezone(420)      # Asia/Bangkok


class TimezoneTests(SimpleTestCase):

    def test_now(self):
        with override_settings(USE_TZ=True):
            self.assertTrue(timezone.is_aware(timezone.now()))
        with override_settings(USE_TZ=False):
            self.assertTrue(timezone.is_naive(timezone.now()))

    def test_localdate(self):
        naive = datetime.datetime(2015, 1, 1, 0, 0, 1)
        with self.assertRaisesMessage(ValueError, 'localtime() cannot be applied to a naive datetime'):
            timezone.localdate(naive)
        with self.assertRaisesMessage(ValueError, 'localtime() cannot be applied to a naive datetime'):
            timezone.localdate(naive, timezone=EAT)

        aware = datetime.datetime(2015, 1, 1, 0, 0, 1, tzinfo=ICT)
        self.assertEqual(timezone.localdate(aware, timezone=EAT), datetime.date(2014, 12, 31))
        with timezone.override(EAT):
            self.assertEqual(timezone.localdate(aware), datetime.date(2014, 12, 31))

        with mock.patch('django.utils.timezone.now', return_value=aware):
            self.assertEqual(timezone.localdate(timezone=EAT), datetime.date(2014, 12, 31))
            with timezone.override(EAT):
                self.assertEqual(timezone.localdate(), datetime.date(2014, 12, 31))

    def test_override(self):
        default = timezone.get_default_timezone()
        try:
            timezone.activate(ICT)

            with timezone.override(EAT):
                self.assertIs(EAT, timezone.get_current_timezone())
            self.assertIs(ICT, timezone.get_current_timezone())

            with timezone.override(None):
                self.assertIs(default, timezone.get_current_timezone())
            self.assertIs(ICT, timezone.get_current_timezone())

            timezone.deactivate()

            with timezone.override(EAT):
                self.assertIs(EAT, timezone.get_current_timezone())
            self.assertIs(default, timezone.get_current_timezone())

            with timezone.override(None):
                self.assertIs(default, timezone.get_current_timezone())
            self.assertIs(default, timezone.get_current_timezone())
        finally:
            timezone.deactivate()

    def test_override_decorator(self):
        default = timezone.get_default_timezone()

        @timezone.override(EAT)
        def func_tz_eat():
            self.assertIs(EAT, timezone.get_current_timezone())

        @timezone.override(None)
        def func_tz_none():
            self.assertIs(default, timezone.get_current_timezone())

        try:
            timezone.activate(ICT)

            func_tz_eat()
            self.assertIs(ICT, timezone.get_current_timezone())

            func_tz_none()
            self.assertIs(ICT, timezone.get_current_timezone())

            timezone.deactivate()

            func_tz_eat()
            self.assertIs(default, timezone.get_current_timezone())

            func_tz_none()
            self.assertIs(default, timezone.get_current_timezone())
        finally:
            timezone.deactivate()

    def test_override_string_tz(self):
        with timezone.override('Asia/Bangkok'):
            self.assertEqual(timezone.get_current_timezone_name(), 'Asia/Bangkok')

    def test_override_fixed_offset(self):
        with timezone.override(timezone.FixedOffset(0, 'tzname')):
            self.assertEqual(timezone.get_current_timezone_name(), 'tzname')

    def test_activate_invalid_timezone(self):
        with self.assertRaisesMessage(ValueError, 'Invalid timezone: None'):
            timezone.activate(None)

    def test_is_aware(self):
        self.assertTrue(timezone.is_aware(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)))
        self.assertFalse(timezone.is_aware(datetime.datetime(2011, 9, 1, 13, 20, 30)))

    def test_is_naive(self):
        self.assertFalse(timezone.is_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)))
        self.assertTrue(timezone.is_naive(datetime.datetime(2011, 9, 1, 13, 20, 30)))

    def test_make_aware(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 13, 20, 30), EAT),
            datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT))
        with self.assertRaises(ValueError):
            timezone.make_aware(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), EAT)

    def test_make_naive(self):
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT), EAT),
            datetime.datetime(2011, 9, 1, 13, 20, 30))
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 17, 20, 30, tzinfo=ICT), EAT),
            datetime.datetime(2011, 9, 1, 13, 20, 30))

        with self.assertRaisesMessage(ValueError, 'make_naive() cannot be applied to a naive datetime'):
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30), EAT)

    def test_make_naive_no_tz(self):
        self.assertEqual(
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=EAT)),
            datetime.datetime(2011, 9, 1, 5, 20, 30)
        )

    def test_make_aware_no_tz(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 13, 20, 30)),
            datetime.datetime(2011, 9, 1, 13, 20, 30, tzinfo=timezone.get_fixed_timezone(-300))
        )

    def test_make_aware2(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 12, 20, 30), CET),
            CET.localize(datetime.datetime(2011, 9, 1, 12, 20, 30)))
        with self.assertRaises(ValueError):
            timezone.make_aware(CET.localize(datetime.datetime(2011, 9, 1, 12, 20, 30)), CET)

    def test_make_aware_pytz(self):
        self.assertEqual(
            timezone.make_naive(CET.localize(datetime.datetime(2011, 9, 1, 12, 20, 30)), CET),
            datetime.datetime(2011, 9, 1, 12, 20, 30))
        self.assertEqual(
            timezone.make_naive(
                pytz.timezone("Asia/Bangkok").localize(datetime.datetime(2011, 9, 1, 17, 20, 30)), CET
            ),
            datetime.datetime(2011, 9, 1, 12, 20, 30))
        with self.assertRaisesMessage(ValueError, 'make_naive() cannot be applied to a naive datetime'):
            timezone.make_naive(datetime.datetime(2011, 9, 1, 12, 20, 30), CET)

    def test_make_aware_pytz_ambiguous(self):
        # 2:30 happens twice, once before DST ends and once after
        ambiguous = datetime.datetime(2015, 10, 25, 2, 30)

        with self.assertRaises(pytz.AmbiguousTimeError):
            timezone.make_aware(ambiguous, timezone=CET)

        std = timezone.make_aware(ambiguous, timezone=CET, is_dst=False)
        dst = timezone.make_aware(ambiguous, timezone=CET, is_dst=True)
        self.assertEqual(std - dst, datetime.timedelta(hours=1))
        self.assertEqual(std.tzinfo.utcoffset(std), datetime.timedelta(hours=1))
        self.assertEqual(dst.tzinfo.utcoffset(dst), datetime.timedelta(hours=2))

    def test_make_aware_pytz_non_existent(self):
        # 2:30 never happened due to DST
        non_existent = datetime.datetime(2015, 3, 29, 2, 30)

        with self.assertRaises(pytz.NonExistentTimeError):
            timezone.make_aware(non_existent, timezone=CET)

        std = timezone.make_aware(non_existent, timezone=CET, is_dst=False)
        dst = timezone.make_aware(non_existent, timezone=CET, is_dst=True)
        self.assertEqual(std - dst, datetime.timedelta(hours=1))
        self.assertEqual(std.tzinfo.utcoffset(std), datetime.timedelta(hours=1))
        self.assertEqual(dst.tzinfo.utcoffset(dst), datetime.timedelta(hours=2))

    def test_get_default_timezone(self):
        self.assertEqual(timezone.get_default_timezone_name(), 'America/Chicago')

    def test_fixedoffset_timedelta(self):
        delta = datetime.timedelta(hours=1)
        self.assertEqual(timezone.get_fixed_timezone(delta).utcoffset(''), delta)

    def test_fixedoffset_pickle(self):
        self.assertEqual(pickle.loads(pickle.dumps(timezone.FixedOffset(0, 'tzname'))).tzname(''), 'tzname')
