from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.forms import DateTimeField
from django.test import SimpleTestCase
from django.utils.timezone import get_fixed_timezone, utc


class DateTimeFieldTest(SimpleTestCase):

    def test_datetimefield_clean(self):
        tests = [
            (date(2006, 10, 25), datetime(2006, 10, 25, 0, 0)),
            (datetime(2006, 10, 25, 14, 30), datetime(2006, 10, 25, 14, 30)),
            (datetime(2006, 10, 25, 14, 30, 59), datetime(2006, 10, 25, 14, 30, 59)),
            (
                datetime(2006, 10, 25, 14, 30, 59, 200),
                datetime(2006, 10, 25, 14, 30, 59, 200),
            ),
            ('2006-10-25 14:30:45.000200', datetime(2006, 10, 25, 14, 30, 45, 200)),
            ('2006-10-25 14:30:45.0002', datetime(2006, 10, 25, 14, 30, 45, 200)),
            ('2006-10-25 14:30:45', datetime(2006, 10, 25, 14, 30, 45)),
            ('2006-10-25 14:30:00', datetime(2006, 10, 25, 14, 30)),
            ('2006-10-25 14:30', datetime(2006, 10, 25, 14, 30)),
            ('2006-10-25', datetime(2006, 10, 25, 0, 0)),
            ('10/25/2006 14:30:45.000200', datetime(2006, 10, 25, 14, 30, 45, 200)),
            ('10/25/2006 14:30:45', datetime(2006, 10, 25, 14, 30, 45)),
            ('10/25/2006 14:30:00', datetime(2006, 10, 25, 14, 30)),
            ('10/25/2006 14:30', datetime(2006, 10, 25, 14, 30)),
            ('10/25/2006', datetime(2006, 10, 25, 0, 0)),
            ('10/25/06 14:30:45.000200', datetime(2006, 10, 25, 14, 30, 45, 200)),
            ('10/25/06 14:30:45', datetime(2006, 10, 25, 14, 30, 45)),
            ('10/25/06 14:30:00', datetime(2006, 10, 25, 14, 30)),
            ('10/25/06 14:30', datetime(2006, 10, 25, 14, 30)),
            ('10/25/06', datetime(2006, 10, 25, 0, 0)),
            # ISO 8601 formats.
            (
                '2014-09-23T22:34:41.614804',
                datetime(2014, 9, 23, 22, 34, 41, 614804),
            ),
            ('2014-09-23T22:34:41', datetime(2014, 9, 23, 22, 34, 41)),
            ('2014-09-23T22:34', datetime(2014, 9, 23, 22, 34)),
            ('2014-09-23', datetime(2014, 9, 23, 0, 0)),
            ('2014-09-23T22:34Z', datetime(2014, 9, 23, 22, 34, tzinfo=utc)),
            (
                '2014-09-23T22:34+07:00',
                datetime(2014, 9, 23, 22, 34, tzinfo=get_fixed_timezone(420)),
            ),
            # Whitespace stripping.
            (' 2006-10-25   14:30:45 ', datetime(2006, 10, 25, 14, 30, 45)),
            (' 2006-10-25 ', datetime(2006, 10, 25, 0, 0)),
            (' 10/25/2006 14:30:45 ', datetime(2006, 10, 25, 14, 30, 45)),
            (' 10/25/2006 14:30 ', datetime(2006, 10, 25, 14, 30)),
            (' 10/25/2006 ', datetime(2006, 10, 25, 0, 0)),
            (' 10/25/06 14:30:45 ', datetime(2006, 10, 25, 14, 30, 45)),
            (' 10/25/06 ', datetime(2006, 10, 25, 0, 0)),
            (
                ' 2014-09-23T22:34:41.614804 ',
                datetime(2014, 9, 23, 22, 34, 41, 614804),
            ),
            (' 2014-09-23T22:34Z ', datetime(2014, 9, 23, 22, 34, tzinfo=utc)),
        ]
        f = DateTimeField()
        for value, expected_datetime in tests:
            with self.subTest(value=value):
                self.assertEqual(f.clean(value), expected_datetime)

    def test_datetimefield_clean_invalid(self):
        f = DateTimeField()
        msg = "'Enter a valid date/time.'"
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('hello')
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('2006-10-25 4:30 p.m.')
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('   ')
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('2014-09-23T28:23')
        f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
        with self.assertRaisesMessage(ValidationError, msg):
            f.clean('2006.10.25 14:30:45')

    def test_datetimefield_clean_input_formats(self):
        tests = [
            ('%Y %m %d %I:%M %p', (
                (date(2006, 10, 25), datetime(2006, 10, 25, 0, 0)),
                (datetime(2006, 10, 25, 14, 30), datetime(2006, 10, 25, 14, 30)),
                (
                    datetime(2006, 10, 25, 14, 30, 59),
                    datetime(2006, 10, 25, 14, 30, 59),
                ),
                (
                    datetime(2006, 10, 25, 14, 30, 59, 200),
                    datetime(2006, 10, 25, 14, 30, 59, 200),
                ),
                ('2006 10 25 2:30 PM', datetime(2006, 10, 25, 14, 30)),
                # ISO-like formats are always accepted.
                ('2006-10-25 14:30:45', datetime(2006, 10, 25, 14, 30, 45)),
            )),
            ('%Y.%m.%d %H:%M:%S.%f', (
                (
                    '2006.10.25 14:30:45.0002',
                    datetime(2006, 10, 25, 14, 30, 45, 200),
                ),
            )),
        ]
        f = DateTimeField()
        for input_format, values in tests:
            f = DateTimeField(input_formats=[input_format])
            for value, expected_datetime in values:
                with self.subTest(value=value, input_format=input_format):
                    self.assertEqual(f.clean(value), expected_datetime)

    def test_datetimefield_not_required(self):
        f = DateTimeField(required=False)
        self.assertIsNone(f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertIsNone(f.clean(''))
        self.assertEqual('None', repr(f.clean('')))

    def test_datetimefield_changed(self):
        f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
        d = datetime(2006, 9, 17, 14, 30, 0)
        self.assertFalse(f.has_changed(d, '2006 09 17 2:30 PM'))
