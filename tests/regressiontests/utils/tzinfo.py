import copy
import datetime
import os
import pickle
import time
from django.utils.tzinfo import FixedOffset, LocalTimezone
from django.utils import unittest

class TzinfoTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.old_TZ = os.environ.get('TZ')
        os.environ['TZ'] = 'US/Eastern'

        try:
            # Check if a timezone has been set
            time.tzset()
            cls.tz_tests = True
        except AttributeError:
            # No timezone available. Don't run the tests that require a TZ
            cls.tz_tests = False

    @classmethod
    def tearDownClass(cls):
        if cls.old_TZ is None:
            del os.environ['TZ']
        else:
            os.environ['TZ'] = cls.old_TZ

        # Cleanup - force re-evaluation of TZ environment variable.
        if cls.tz_tests:
            time.tzset()

    def test_fixedoffset(self):
        self.assertEqual(repr(FixedOffset(0)), '+0000')
        self.assertEqual(repr(FixedOffset(60)), '+0100')
        self.assertEqual(repr(FixedOffset(-60)), '-0100')
        self.assertEqual(repr(FixedOffset(280)), '+0440')
        self.assertEqual(repr(FixedOffset(-280)), '-0440')
        self.assertEqual(repr(FixedOffset(-78.4)), '-0118')
        self.assertEqual(repr(FixedOffset(78.4)), '+0118')
        self.assertEqual(repr(FixedOffset(-5.5*60)), '-0530')
        self.assertEqual(repr(FixedOffset(5.5*60)), '+0530')
        self.assertEqual(repr(FixedOffset(-.5*60)), '-0030')
        self.assertEqual(repr(FixedOffset(.5*60)), '+0030')

    def test_16899(self):
        if not self.tz_tests:
            return
        ts = 1289106000
        # Midnight at the end of DST in US/Eastern: 2010-11-07T05:00:00Z
        dt = datetime.datetime.utcfromtimestamp(ts)
        # US/Eastern -- we force its representation to "EST"
        tz = LocalTimezone(dt + datetime.timedelta(days=1))
        self.assertEqual(
                repr(datetime.datetime.fromtimestamp(ts - 3600, tz)),
                'datetime.datetime(2010, 11, 7, 0, 0, tzinfo=EST)')
        self.assertEqual(
                repr(datetime.datetime.fromtimestamp(ts, tz)),
                'datetime.datetime(2010, 11, 7, 1, 0, tzinfo=EST)')
        self.assertEqual(
                repr(datetime.datetime.fromtimestamp(ts + 3600, tz)),
                'datetime.datetime(2010, 11, 7, 1, 0, tzinfo=EST)')

    def test_copy(self):
        now = datetime.datetime.now()
        self.assertIsInstance(copy.copy(FixedOffset(90)), FixedOffset)
        self.assertIsInstance(copy.copy(LocalTimezone(now)), LocalTimezone)

    def test_deepcopy(self):
        now = datetime.datetime.now()
        self.assertIsInstance(copy.deepcopy(FixedOffset(90)), FixedOffset)
        self.assertIsInstance(copy.deepcopy(LocalTimezone(now)), LocalTimezone)

    def test_pickling_unpickling(self):
        now = datetime.datetime.now()
        self.assertIsInstance(pickle.loads(pickle.dumps(FixedOffset(90))), FixedOffset)
        self.assertIsInstance(pickle.loads(pickle.dumps(LocalTimezone(now))), LocalTimezone)
