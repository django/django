import copy
import datetime
import pickle
from django.test.utils import override_settings
from django.utils import six
from django.utils import timezone
from django.utils.tzinfo import FixedOffset
from django.utils import unittest


EAT = FixedOffset(180)      # Africa/Nairobi
ICT = FixedOffset(420)      # Asia/Bangkok


class TimezoneTests(unittest.TestCase):

    def test_localtime(self):
        now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
        local_tz = timezone.LocalTimezone()
        local_now = timezone.localtime(now, local_tz)
        self.assertEqual(local_now.tzinfo, local_tz)

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

    def test_copy(self):
        self.assertIsInstance(copy.copy(timezone.UTC()), timezone.UTC)
        self.assertIsInstance(copy.copy(timezone.LocalTimezone()), timezone.LocalTimezone)

    def test_deepcopy(self):
        self.assertIsInstance(copy.deepcopy(timezone.UTC()), timezone.UTC)
        self.assertIsInstance(copy.deepcopy(timezone.LocalTimezone()), timezone.LocalTimezone)

    def test_pickling_unpickling(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(timezone.UTC())), timezone.UTC)
        self.assertIsInstance(pickle.loads(pickle.dumps(timezone.LocalTimezone())), timezone.LocalTimezone)
