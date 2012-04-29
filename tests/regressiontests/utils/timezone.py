import copy
import datetime
import pickle
from django.test.utils import override_settings
from django.utils import timezone
from django.utils import unittest


class TimezoneTests(unittest.TestCase):

    def test_localtime(self):
        now = datetime.datetime.utcnow().replace(tzinfo=timezone.utc)
        local_tz = timezone.LocalTimezone()
        local_now = timezone.localtime(now, local_tz)
        self.assertEqual(local_now.tzinfo, local_tz)

    def test_now(self):
        with override_settings(USE_TZ=True):
            self.assertTrue(timezone.is_aware(timezone.now()))
        with override_settings(USE_TZ=False):
            self.assertTrue(timezone.is_naive(timezone.now()))

    def test_copy(self):
        self.assertIsInstance(copy.copy(timezone.UTC()), timezone.UTC)
        self.assertIsInstance(copy.copy(timezone.LocalTimezone()), timezone.LocalTimezone)

    def test_deepcopy(self):
        self.assertIsInstance(copy.deepcopy(timezone.UTC()), timezone.UTC)
        self.assertIsInstance(copy.deepcopy(timezone.LocalTimezone()), timezone.LocalTimezone)

    def test_pickling_unpickling(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(timezone.UTC())), timezone.UTC)
        self.assertIsInstance(pickle.loads(pickle.dumps(timezone.LocalTimezone())), timezone.LocalTimezone)
