import datetime
import unittest

from django.utils.dateparse import parse_duration
from django.utils.duration import duration_string


class TestDurationString(unittest.TestCase):

    def test_simple(self):
        duration = datetime.timedelta(hours=1, minutes=3, seconds=5)
        self.assertEqual(duration_string(duration), '01:03:05')

    def test_days(self):
        duration = datetime.timedelta(days=1, hours=1, minutes=3, seconds=5)
        self.assertEqual(duration_string(duration), '1 01:03:05')

    def test_microseconds(self):
        duration = datetime.timedelta(hours=1, minutes=3, seconds=5, microseconds=12345)
        self.assertEqual(duration_string(duration), '01:03:05.012345')

    def test_negative(self):
        duration = datetime.timedelta(days=-1, hours=1, minutes=3, seconds=5)
        self.assertEqual(duration_string(duration), '-1 01:03:05')


class TestParseDurationRoundtrip(unittest.TestCase):

    def test_simple(self):
        duration = datetime.timedelta(hours=1, minutes=3, seconds=5)
        self.assertEqual(parse_duration(duration_string(duration)), duration)

    def test_days(self):
        duration = datetime.timedelta(days=1, hours=1, minutes=3, seconds=5)
        self.assertEqual(parse_duration(duration_string(duration)), duration)

    def test_microseconds(self):
        duration = datetime.timedelta(hours=1, minutes=3, seconds=5, microseconds=12345)
        self.assertEqual(parse_duration(duration_string(duration)), duration)

    def test_negative(self):
        duration = datetime.timedelta(days=-1, hours=1, minutes=3, seconds=5)
        self.assertEqual(parse_duration(duration_string(duration)), duration)
