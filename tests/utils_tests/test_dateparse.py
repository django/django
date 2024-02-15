import unittest
from datetime import date, datetime, time, timedelta

from django.utils.dateparse import (
    parse_date,
    parse_datetime,
    parse_duration,
    parse_time,
)
from django.utils.timezone import get_fixed_timezone
from django.utils.version import PY311


class DateParseTests(unittest.TestCase):
    def test_parse_date(self):
        # Valid inputs
        self.assertEqual(parse_date("2012-04-23"), date(2012, 4, 23))
        self.assertEqual(parse_date("2012-4-9"), date(2012, 4, 9))
        if PY311:
            self.assertEqual(parse_date("20120423"), date(2012, 4, 23))
        # Invalid inputs
        self.assertIsNone(parse_date("2012423"))
        with self.assertRaises(ValueError):
            parse_date("2012-04-56")

    def test_parse_time(self):
        # Valid inputs
        self.assertEqual(parse_time("09:15:00"), time(9, 15))
        if PY311:
            self.assertEqual(parse_time("091500"), time(9, 15))
        self.assertEqual(parse_time("10:10"), time(10, 10))
        self.assertEqual(parse_time("10:20:30.400"), time(10, 20, 30, 400000))
        self.assertEqual(parse_time("10:20:30,400"), time(10, 20, 30, 400000))
        self.assertEqual(parse_time("4:8:16"), time(4, 8, 16))
        # Time zone offset is ignored.
        self.assertEqual(parse_time("00:05:23+04:00"), time(0, 5, 23))
        # Invalid inputs
        self.assertIsNone(parse_time("00:05:"))
        self.assertIsNone(parse_time("00:05:23,"))
        self.assertIsNone(parse_time("00:05:23+"))
        self.assertIsNone(parse_time("00:05:23+25:00"))
        self.assertIsNone(parse_time("4:18:101"))
        self.assertIsNone(parse_time("91500"))
        with self.assertRaises(ValueError):
            parse_time("09:15:90")

    def test_parse_datetime(self):
        valid_inputs = (
            ("2012-04-23", datetime(2012, 4, 23)),
            ("2012-04-23T09:15:00", datetime(2012, 4, 23, 9, 15)),
            ("2012-4-9 4:8:16", datetime(2012, 4, 9, 4, 8, 16)),
            (
                "2012-04-23T09:15:00Z",
                datetime(2012, 4, 23, 9, 15, 0, 0, get_fixed_timezone(0)),
            ),
            (
                "2012-4-9 4:8:16-0320",
                datetime(2012, 4, 9, 4, 8, 16, 0, get_fixed_timezone(-200)),
            ),
            (
                "2012-04-23T10:20:30.400+02:30",
                datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(150)),
            ),
            (
                "2012-04-23T10:20:30.400+02",
                datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(120)),
            ),
            (
                "2012-04-23T10:20:30.400-02",
                datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(-120)),
            ),
            (
                "2012-04-23T10:20:30,400-02",
                datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(-120)),
            ),
            (
                "2012-04-23T10:20:30.400 +0230",
                datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(150)),
            ),
            (
                "2012-04-23T10:20:30,400 +00",
                datetime(2012, 4, 23, 10, 20, 30, 400000, get_fixed_timezone(0)),
            ),
            (
                "2012-04-23T10:20:30   -02",
                datetime(2012, 4, 23, 10, 20, 30, 0, get_fixed_timezone(-120)),
            ),
        )
        for source, expected in valid_inputs:
            with self.subTest(source=source):
                self.assertEqual(parse_datetime(source), expected)

        # Invalid inputs
        self.assertIsNone(parse_datetime("20120423091500"))
        with self.assertRaises(ValueError):
            parse_datetime("2012-04-56T09:15:90")


class DurationParseTests(unittest.TestCase):
    def test_parse_python_format(self):
        timedeltas = [
            timedelta(
                days=4, minutes=15, seconds=30, milliseconds=100
            ),  # fractions of seconds
            timedelta(hours=10, minutes=15, seconds=30),  # hours, minutes, seconds
            timedelta(days=4, minutes=15, seconds=30),  # multiple days
            timedelta(days=1, minutes=00, seconds=00),  # single day
            timedelta(days=-4, minutes=15, seconds=30),  # negative durations
            timedelta(minutes=15, seconds=30),  # minute & seconds
            timedelta(seconds=30),  # seconds
        ]
        for delta in timedeltas:
            with self.subTest(delta=delta):
                self.assertEqual(parse_duration(format(delta)), delta)

    def test_parse_postgresql_format(self):
        test_values = (
            ("1 day", timedelta(1)),
            ("-1 day", timedelta(-1)),
            ("1 day 0:00:01", timedelta(days=1, seconds=1)),
            ("1 day -0:00:01", timedelta(days=1, seconds=-1)),
            ("-1 day -0:00:01", timedelta(days=-1, seconds=-1)),
            ("-1 day +0:00:01", timedelta(days=-1, seconds=1)),
            (
                "4 days 0:15:30.1",
                timedelta(days=4, minutes=15, seconds=30, milliseconds=100),
            ),
            (
                "4 days 0:15:30.0001",
                timedelta(days=4, minutes=15, seconds=30, microseconds=100),
            ),
            ("-4 days -15:00:30", timedelta(days=-4, hours=-15, seconds=-30)),
        )
        for source, expected in test_values:
            with self.subTest(source=source):
                self.assertEqual(parse_duration(source), expected)

    def test_seconds(self):
        self.assertEqual(parse_duration("30"), timedelta(seconds=30))

    def test_minutes_seconds(self):
        self.assertEqual(parse_duration("15:30"), timedelta(minutes=15, seconds=30))
        self.assertEqual(parse_duration("5:30"), timedelta(minutes=5, seconds=30))

    def test_hours_minutes_seconds(self):
        self.assertEqual(
            parse_duration("10:15:30"), timedelta(hours=10, minutes=15, seconds=30)
        )
        self.assertEqual(
            parse_duration("1:15:30"), timedelta(hours=1, minutes=15, seconds=30)
        )
        self.assertEqual(
            parse_duration("100:200:300"),
            timedelta(hours=100, minutes=200, seconds=300),
        )

    def test_days(self):
        self.assertEqual(
            parse_duration("4 15:30"), timedelta(days=4, minutes=15, seconds=30)
        )
        self.assertEqual(
            parse_duration("4 10:15:30"),
            timedelta(days=4, hours=10, minutes=15, seconds=30),
        )

    def test_fractions_of_seconds(self):
        test_values = (
            ("15:30.1", timedelta(minutes=15, seconds=30, milliseconds=100)),
            ("15:30.01", timedelta(minutes=15, seconds=30, milliseconds=10)),
            ("15:30.001", timedelta(minutes=15, seconds=30, milliseconds=1)),
            ("15:30.0001", timedelta(minutes=15, seconds=30, microseconds=100)),
            ("15:30.00001", timedelta(minutes=15, seconds=30, microseconds=10)),
            ("15:30.000001", timedelta(minutes=15, seconds=30, microseconds=1)),
            ("15:30,000001", timedelta(minutes=15, seconds=30, microseconds=1)),
        )
        for source, expected in test_values:
            with self.subTest(source=source):
                self.assertEqual(parse_duration(source), expected)

    def test_negative(self):
        test_values = (
            ("-4 15:30", timedelta(days=-4, minutes=15, seconds=30)),
            ("-172800", timedelta(days=-2)),
            ("-15:30", timedelta(minutes=-15, seconds=-30)),
            ("-1:15:30", timedelta(hours=-1, minutes=-15, seconds=-30)),
            ("-30.1", timedelta(seconds=-30, milliseconds=-100)),
            ("-30,1", timedelta(seconds=-30, milliseconds=-100)),
            ("-00:01:01", timedelta(minutes=-1, seconds=-1)),
            ("-01:01", timedelta(seconds=-61)),
            ("-01:-01", None),
        )
        for source, expected in test_values:
            with self.subTest(source=source):
                self.assertEqual(parse_duration(source), expected)

    def test_iso_8601(self):
        test_values = (
            ("P4Y", None),
            ("P4M", None),
            ("P4W", None),
            ("P4D", timedelta(days=4)),
            ("-P1D", timedelta(days=-1)),
            ("P0.5D", timedelta(hours=12)),
            ("P0,5D", timedelta(hours=12)),
            ("-P0.5D", timedelta(hours=-12)),
            ("-P0,5D", timedelta(hours=-12)),
            ("PT5H", timedelta(hours=5)),
            ("-PT5H", timedelta(hours=-5)),
            ("PT5M", timedelta(minutes=5)),
            ("-PT5M", timedelta(minutes=-5)),
            ("PT5S", timedelta(seconds=5)),
            ("-PT5S", timedelta(seconds=-5)),
            ("PT0.000005S", timedelta(microseconds=5)),
            ("PT0,000005S", timedelta(microseconds=5)),
            ("-PT0.000005S", timedelta(microseconds=-5)),
            ("-PT0,000005S", timedelta(microseconds=-5)),
            ("-P4DT1H", timedelta(days=-4, hours=-1)),
            # Invalid separators for decimal fractions.
            ("P3(3D", None),
            ("PT3)3H", None),
            ("PT3|3M", None),
            ("PT3/3S", None),
        )
        for source, expected in test_values:
            with self.subTest(source=source):
                self.assertEqual(parse_duration(source), expected)
