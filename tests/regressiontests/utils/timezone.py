import copy
import datetime
import pickle
from django.test.utils import override_settings
from django.utils import timezone
from django.utils import unittest
from django.utils.tzinfo import FixedOffset


UTC = timezone.utc
EAT = FixedOffset(180)      # Africa/Nairobi
ICT = FixedOffset(420)      # Asia/Bangkok


class TimezoneTests(unittest.TestCase):
    def setUp(self):
        super(TimezoneTests, self).setUp()
        self._has_active_value = hasattr(timezone._active, 'value')
        self._active_value = getattr(timezone._active, 'value', None)
    
    def tearDown(self):
        super(TimezoneTests, self).tearDown()
        if self._has_active_value:
            setattr(timezone._active, 'value', self._active_value)
        elif hasattr(timezone._active, 'value'):
            del timezone._active.value
    
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
    
    @override_settings(TIMEZONE='Africa/Nairobi')
    def test_override(self):
        # timezone is None, old_timezone is not None
        timezone.activate(ICT)
        with timezone.override(None):
            self.assertIs(timezone.get_default_timezone(), timezone.get_current_timezone())
        self.assertIs(ICT, timezone.get_current_timezone())
        
        # timezone is not None, old_timezone is not None
        timezone.activate(ICT)
        with timezone.override(UTC):
            self.assertIs(UTC, timezone.get_current_timezone())
        self.assertIs(ICT, timezone.get_current_timezone())
        
        # timezone is not None, old_timezone is None
        timezone.deactivate()
        with timezone.override(UTC):
            self.assertIs(UTC, timezone.get_current_timezone())
        self.assertIs(timezone.get_default_timezone(), timezone.get_current_timezone())
        
        # timezone is None, old_timezone is None
        timezone.deactivate()
        with timezone.override(None):
            self.assertIs(timezone.get_default_timezone(), timezone.get_current_timezone())
        self.assertIs(timezone.get_default_timezone(), timezone.get_current_timezone())
    