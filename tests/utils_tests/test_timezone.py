import copy
import datetime
import pickle
import unittest

from django.test import override_settings
from django.utils import timezone

try:
    import pytz
except ImportError:
    pytz = None


if pytz is not None:
    CET = pytz.timezone("Europe/Paris")
EAT = timezone.get_fixed_timezone(180)      # Africa/Nairobi
ICT = timezone.get_fixed_timezone(420)      # Asia/Bangkok


class TimezoneTests(unittest.TestCase):

    def test_localtime(self):
        now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
        local_tz = timezone.LocalTimezone()
        local_now = timezone.localtime(now, local_tz)
        self.assertEqual(local_now.tzinfo, local_tz)

    def test_localtime_naive(self):
        with self.assertRaises(ValueError):
            timezone.localtime(datetime.datetime.now())

    def test_localtime_out_of_range(self):
        local_tz = timezone.LocalTimezone()
        long_ago = datetime.datetime(1900, 1, 1, tzinfo=timezone.utc)
        try:
            timezone.localtime(long_ago, local_tz)
        except (OverflowError, ValueError) as exc:
            self.assertIn("install pytz", exc.args[0])
        else:
            raise unittest.SkipTest("Failed to trigger an OverflowError or ValueError")

    def test_now(self):
        with override_settings(USE_TZ=True):
            self.assertTrue(timezone.is_aware(timezone.now()))
        with override_settings(USE_TZ=False):
            self.assertTrue(timezone.is_naive(timezone.now()))

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

    def test_copy(self):
        self.assertIsInstance(copy.copy(timezone.UTC()), timezone.UTC)
        self.assertIsInstance(copy.copy(timezone.LocalTimezone()), timezone.LocalTimezone)

    def test_deepcopy(self):
        self.assertIsInstance(copy.deepcopy(timezone.UTC()), timezone.UTC)
        self.assertIsInstance(copy.deepcopy(timezone.LocalTimezone()), timezone.LocalTimezone)

    def test_pickling_unpickling(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(timezone.UTC())), timezone.UTC)
        self.assertIsInstance(pickle.loads(pickle.dumps(timezone.LocalTimezone())), timezone.LocalTimezone)

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
        with self.assertRaises(ValueError):
            timezone.make_naive(datetime.datetime(2011, 9, 1, 13, 20, 30), EAT)

    @unittest.skipIf(pytz is None, "this test requires pytz")
    def test_make_aware2(self):
        self.assertEqual(
            timezone.make_aware(datetime.datetime(2011, 9, 1, 12, 20, 30), CET),
            CET.localize(datetime.datetime(2011, 9, 1, 12, 20, 30)))
        with self.assertRaises(ValueError):
            timezone.make_aware(CET.localize(datetime.datetime(2011, 9, 1, 12, 20, 30)), CET)

    @unittest.skipIf(pytz is None, "this test requires pytz")
    def test_make_aware_pytz(self):
        self.assertEqual(
            timezone.make_naive(CET.localize(datetime.datetime(2011, 9, 1, 12, 20, 30)), CET),
            datetime.datetime(2011, 9, 1, 12, 20, 30))
        self.assertEqual(
            timezone.make_naive(pytz.timezone("Asia/Bangkok").localize(datetime.datetime(2011, 9, 1, 17, 20, 30)), CET),
            datetime.datetime(2011, 9, 1, 12, 20, 30))
        with self.assertRaises(ValueError):
            timezone.make_naive(datetime.datetime(2011, 9, 1, 12, 20, 30), CET)
