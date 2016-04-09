from __future__ import unicode_literals

import datetime

from django.forms import DateTimeField, ValidationError
from django.test import SimpleTestCase


class DateTimeFieldTest(SimpleTestCase):

    def test_datetimefield_1(self):
        f = DateTimeField()
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(
            datetime.datetime(2006, 10, 25, 14, 30, 59),
            f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
        )
        self.assertEqual(
            datetime.datetime(2006, 10, 25, 14, 30, 59, 200),
            f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
        )
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45, 200), f.clean('2006-10-25 14:30:45.000200'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45, 200), f.clean('2006-10-25 14:30:45.0002'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean('2006-10-25 14:30:45'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006-10-25 14:30:00'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006-10-25 14:30'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean('2006-10-25'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45, 200), f.clean('10/25/2006 14:30:45.000200'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean('10/25/2006 14:30:45'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/2006 14:30:00'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/2006 14:30'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean('10/25/2006'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45, 200), f.clean('10/25/06 14:30:45.000200'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean('10/25/06 14:30:45'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/06 14:30:00'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/06 14:30'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean('10/25/06'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'"):
            f.clean('hello')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'"):
            f.clean('2006-10-25 4:30 p.m.')

    def test_datetimefield_2(self):
        f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(
            datetime.datetime(2006, 10, 25, 14, 30, 59),
            f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
        )
        self.assertEqual(
            datetime.datetime(2006, 10, 25, 14, 30, 59, 200),
            f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
        )
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006 10 25 2:30 PM'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'"):
            f.clean('2006-10-25 14:30:45')

    def test_datetimefield_3(self):
        f = DateTimeField(required=False)
        self.assertIsNone(f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertIsNone(f.clean(''))
        self.assertEqual('None', repr(f.clean('')))

    def test_datetimefield_4(self):
        f = DateTimeField()
        # Test whitespace stripping behavior (#5714)
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean(' 2006-10-25   14:30:45 '))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(' 2006-10-25 '))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean(' 10/25/2006 14:30:45 '))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(' 10/25/2006 14:30 '))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(' 10/25/2006 '))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean(' 10/25/06 14:30:45 '))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(' 10/25/06 '))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'"):
            f.clean('   ')

    def test_datetimefield_5(self):
        f = DateTimeField(input_formats=['%Y.%m.%d %H:%M:%S.%f'])
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45, 200), f.clean('2006.10.25 14:30:45.0002'))

    def test_datetimefield_changed(self):
        format = '%Y %m %d %I:%M %p'
        f = DateTimeField(input_formats=[format])
        d = datetime.datetime(2006, 9, 17, 14, 30, 0)
        self.assertFalse(f.has_changed(d, '2006 09 17 2:30 PM'))
