# Unit tests for typecast functions in django.db.backends.util

import datetime
import unittest

from django.db.backends import utils as typecasts

TEST_CASES = {
    'typecast_date': (
        ('', None),
        (None, None),
        ('2005-08-11', datetime.date(2005, 8, 11)),
        ('1990-01-01', datetime.date(1990, 1, 1)),
    ),
    'typecast_time': (
        ('', None),
        (None, None),
        ('0:00:00', datetime.time(0, 0)),
        ('0:30:00', datetime.time(0, 30)),
        ('8:50:00', datetime.time(8, 50)),
        ('08:50:00', datetime.time(8, 50)),
        ('12:00:00', datetime.time(12, 00)),
        ('12:30:00', datetime.time(12, 30)),
        ('13:00:00', datetime.time(13, 00)),
        ('23:59:00', datetime.time(23, 59)),
        ('00:00:12', datetime.time(0, 0, 12)),
        ('00:00:12.5', datetime.time(0, 0, 12, 500000)),
        ('7:22:13.312', datetime.time(7, 22, 13, 312000)),
        ('12:45:30.126631', datetime.time(12, 45, 30, 126631)),
        ('12:45:30.126630', datetime.time(12, 45, 30, 126630)),
        ('12:45:30.123456789', datetime.time(12, 45, 30, 123456)),
    ),
    'typecast_timestamp': (
        ('', None),
        (None, None),
        ('2005-08-11 0:00:00', datetime.datetime(2005, 8, 11)),
        ('2005-08-11 0:30:00', datetime.datetime(2005, 8, 11, 0, 30)),
        ('2005-08-11 8:50:30', datetime.datetime(2005, 8, 11, 8, 50, 30)),
        ('2005-08-11 8:50:30.123', datetime.datetime(2005, 8, 11, 8, 50, 30, 123000)),
        ('2005-08-11 8:50:30.9', datetime.datetime(2005, 8, 11, 8, 50, 30, 900000)),
        ('2005-08-11 8:50:30.312-05', datetime.datetime(2005, 8, 11, 8, 50, 30, 312000)),
        ('2005-08-11 8:50:30.312+02', datetime.datetime(2005, 8, 11, 8, 50, 30, 312000)),
        # ticket 14453
        ('2010-10-12 15:29:22.063202', datetime.datetime(2010, 10, 12, 15, 29, 22, 63202)),
        ('2010-10-12 15:29:22.063202-03', datetime.datetime(2010, 10, 12, 15, 29, 22, 63202)),
        ('2010-10-12 15:29:22.063202+04', datetime.datetime(2010, 10, 12, 15, 29, 22, 63202)),
        ('2010-10-12 15:29:22.0632021', datetime.datetime(2010, 10, 12, 15, 29, 22, 63202)),
        ('2010-10-12 15:29:22.0632029', datetime.datetime(2010, 10, 12, 15, 29, 22, 63202)),
    ),
}


class DBTypeCasts(unittest.TestCase):
    def test_typeCasts(self):
        for k, v in TEST_CASES.items():
            for inpt, expected in v:
                got = getattr(typecasts, k)(inpt)
                self.assertEqual(
                    got,
                    expected,
                    "In %s: %r doesn't match %r. Got %r instead." % (k, inpt, expected, got)
                )
