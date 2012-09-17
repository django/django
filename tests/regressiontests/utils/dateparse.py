from __future__ import unicode_literals

from datetime import date, time, datetime

from django.utils.dateparse import parse_date, parse_time, parse_datetime
from django.utils import unittest
from django.utils.tzinfo import FixedOffset


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
            datetime(2012, 4, 23, 9, 15, 0, 0, FixedOffset(0)))
        self.assertEqual(parse_datetime('2012-4-9 4:8:16-0320'),
            datetime(2012, 4, 9, 4, 8, 16, 0, FixedOffset(-200)))
        self.assertEqual(parse_datetime('2012-04-23T10:20:30.400+02:30'),
            datetime(2012, 4, 23, 10, 20, 30, 400000, FixedOffset(150)))
        # Invalid inputs
        self.assertEqual(parse_datetime('20120423091500'), None)
        self.assertRaises(ValueError, parse_datetime, '2012-04-56T09:15:90')
