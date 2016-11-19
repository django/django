import datetime

from django.forms import TimeField, ValidationError
from django.test import SimpleTestCase

from . import FormFieldAssertionsMixin


class TimeFieldTest(FormFieldAssertionsMixin, SimpleTestCase):

    def test_timefield_1(self):
        f = TimeField()
        self.assertEqual(datetime.time(14, 25), f.clean(datetime.time(14, 25)))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(datetime.time(14, 25, 59)))
        self.assertEqual(datetime.time(14, 25), f.clean('14:25'))
        self.assertEqual(datetime.time(14, 25, 59), f.clean('14:25:59'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid time.'"):
            f.clean('hello')
        with self.assertRaisesMessage(ValidationError, "'Enter a valid time.'"):
            f.clean('1:24 p.m.')

    def test_timefield_2(self):
        f = TimeField(input_formats=['%I:%M %p'])
        self.assertEqual(datetime.time(14, 25), f.clean(datetime.time(14, 25)))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(datetime.time(14, 25, 59)))
        self.assertEqual(datetime.time(4, 25), f.clean('4:25 AM'))
        self.assertEqual(datetime.time(16, 25), f.clean('4:25 PM'))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid time.'"):
            f.clean('14:30:45')

    def test_timefield_3(self):
        f = TimeField()
        # Test whitespace stripping behavior (#5714)
        self.assertEqual(datetime.time(14, 25), f.clean(' 14:25 '))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(' 14:25:59 '))
        with self.assertRaisesMessage(ValidationError, "'Enter a valid time.'"):
            f.clean('   ')

    def test_timefield_changed(self):
        t1 = datetime.time(12, 51, 34, 482548)
        t2 = datetime.time(12, 51)
        f = TimeField(input_formats=['%H:%M', '%H:%M %p'])
        self.assertTrue(f.has_changed(t1, '12:51'))
        self.assertFalse(f.has_changed(t2, '12:51'))
        self.assertFalse(f.has_changed(t2, '12:51 PM'))
