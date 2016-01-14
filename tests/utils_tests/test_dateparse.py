from __future__ import unicode_literals

import unittest
from datetime import date, datetime, time, timedelta

from django.utils.dateparse import (
    parse_date, parse_datetime, parse_duration, parse_time,
)
from django.utils.timezone import get_fixed_timezone


class DateParseTests(unittest.TestCase):

    def test_parse_date(self):
        # Valid inputs
        self.assertEqual(parse_date('2012-04-23'), date(2012, 4, 23))
        self.assertEqual(parse_date('2012-4-9'), date(2012, 4, 9))
        # Invalid inputs
        self.assertEqual(parse_date('20120423'), None)
        self.assertRaises(ValueError, parse_date, '2012-04-56')

    def test_parse_time(self):
        # Valid inputs
        self.assertEqual(parse_time('09:15:00'), time(9, 15))
        self.assertEqual(parse_time('10:10'), time(10, 10))
        self.assertEqual(parse_time('10:20:30.400'), time(10, 20, 30, 400000))
        self.assertEqual(parse_time('4:8:16'), time(4, 8, 16))
        # Invalid inputs
        self.assertEqual(parse_time('091500'), None)
        self.assertRaises(ValueError, parse_time, '09:15:90')

    def test_parse_datetime(self):
        # Valid inputs
        self.assertEqual(parse_datetime('2012-04-23T09:15:00'),
            datetime(2012, 4, 23, 9, 15))
        self.assertEqual(parse_datetime('2012-4-9 4:8:16'),
            datetime(2012, 4, 9, 4, 8, 16))
        self.assertEqual(parse_datetime('2012-04-23T09:15:00Z'),
            datetime(2012, 4, 23, 9, 15, 0, 0, get_fixed_timezone(0)))
        self.assertEqual(parse_datetime('2012-4-9 4:8:16-0320'),
            datetime(2012, 4, 9, 4, 8, 16, 0, get_fixed_timezone(-200)))
        self.assertEqual(parse_datetime('2012-04-23T10:20:30.400+02:30'),
            datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(150)))
        self.assertEqual(parse_datetime('2012-04-23T10:20:30.400+02'),
            datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(120)))
        self.assertEqual(parse_datetime('2012-04-23T10:20:30.400-02'),
            datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(-120)))
        # Invalid inputs
        self.assertEqual(parse_datetime('20120423091500'), None)
        self.assertRaises(ValueError, parse_datetime, '2012-04-56T09:15:90')


class DurationParseTests(unittest.TestCase):

    def test_parse_python_format(self):
        timedeltas = [
            timedelta(days=4, minutes=15, seconds=30, milliseconds=100),  # fractions of seconds
            timedelta(hours=10, minutes=15, seconds=30),  # hours, minutes, seconds
            timedelta(days=4, minutes=15, seconds=30),  # multiple days
            timedelta(days=1, minutes=00, seconds=00),  # single day
            timedelta(days=-4, minutes=15, seconds=30),  # negative durations
            timedelta(minutes=15, seconds=30),  # minute & seconds
            timedelta(seconds=30),  # seconds
        ]
        for delta in timedeltas:
            self.assertEqual(parse_duration(format(delta)), delta)

    def test_seconds(self):
        self.assertEqual(parse_duration('30'), timedelta(seconds=30))

    def test_minutes_seconds(self):
        self.assertEqual(parse_duration('15:30'), timedelta(minutes=15, seconds=30))
        self.assertEqual(parse_duration('5:30'), timedelta(minutes=5, seconds=30))

    def test_hours_minutes_seconds(self):
        self.assertEqual(parse_duration('10:15:30'), timedelta(hours=10, minutes=15, seconds=30))
        self.assertEqual(parse_duration('1:15:30'), timedelta(hours=1, minutes=15, seconds=30))
        self.assertEqual(parse_duration('100:200:300'), timedelta(hours=100, minutes=200, seconds=300))

    def test_days(self):
        self.assertEqual(parse_duration('4 15:30'), timedelta(days=4, minutes=15, seconds=30))
        self.assertEqual(parse_duration('4 10:15:30'), timedelta(days=4, hours=10, minutes=15, seconds=30))

    def test_fractions_of_seconds(self):
        self.assertEqual(parse_duration('15:30.1'), timedelta(minutes=15, seconds=30, milliseconds=100))
        self.assertEqual(parse_duration('15:30.01'), timedelta(minutes=15, seconds=30, milliseconds=10))
        self.assertEqual(parse_duration('15:30.001'), timedelta(minutes=15, seconds=30, milliseconds=1))
        self.assertEqual(parse_duration('15:30.0001'), timedelta(minutes=15, seconds=30, microseconds=100))
        self.assertEqual(parse_duration('15:30.00001'), timedelta(minutes=15, seconds=30, microseconds=10))
        self.assertEqual(parse_duration('15:30.000001'), timedelta(minutes=15, seconds=30, microseconds=1))

    def test_negative(self):
        self.assertEqual(parse_duration('-4 15:30'), timedelta(days=-4, minutes=15, seconds=30))

    def test_iso_8601(self):
        self.assertEqual(parse_duration('P4Y'), None)
        self.assertEqual(parse_duration('P4M'), None)
        self.assertEqual(parse_duration('P4W'), None)
        self.assertEqual(parse_duration('P4D'), timedelta(days=4))
        self.assertEqual(parse_duration('P0.5D'), timedelta(hours=12))
        self.assertEqual(parse_duration('PT5H'), timedelta(hours=5))
        self.assertEqual(parse_duration('PT5M'), timedelta(minutes=5))
        self.assertEqual(parse_duration('PT5S'), timedelta(seconds=5))
        self.assertEqual(parse_duration('PT0.000005S'), timedelta(microseconds=5))
