import copy
import pickle
from django.utils.timezone import UTC, LocalTimezone
from django.utils import unittest

class TimezoneTests(unittest.TestCase):

    def test_copy(self):
        self.assertIsInstance(copy.copy(UTC()), UTC)
        self.assertIsInstance(copy.copy(LocalTimezone()), LocalTimezone)

    def test_deepcopy(self):
        self.assertIsInstance(copy.deepcopy(UTC()), UTC)
        self.assertIsInstance(copy.deepcopy(LocalTimezone()), LocalTimezone)

    def test_pickling_unpickling(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(UTC())), UTC)
        self.assertIsInstance(pickle.loads(pickle.dumps(LocalTimezone())), LocalTimezone)
