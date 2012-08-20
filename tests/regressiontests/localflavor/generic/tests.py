from __future__ import unicode_literals

import datetime

from django.contrib.localflavor.generic.forms import DateField, DateTimeField

from django.test import SimpleTestCase


class GenericLocalFlavorTests(SimpleTestCase):
    def test_GenericDateField(self):
        error_invalid = ['Enter a valid date.']
        valid = {
            datetime.date(2006, 10, 25): datetime.date(2006, 10, 25),
            datetime.datetime(2006, 10, 25, 14, 30): datetime.date(2006, 10, 25),
            datetime.datetime(2006, 10, 25, 14, 30, 59): datetime.date(2006, 10, 25),
            datetime.datetime(2006, 10, 25, 14, 30, 59, 200): datetime.date(2006, 10, 25),
            '2006-10-25': datetime.date(2006, 10, 25),
            '25/10/2006': datetime.date(2006, 10, 25),
            '25/10/06': datetime.date(2006, 10, 25),
            'Oct 25 2006': datetime.date(2006, 10, 25),
            'October 25 2006': datetime.date(2006, 10, 25),
            'October 25, 2006': datetime.date(2006, 10, 25),
            '25 October 2006': datetime.date(2006, 10, 25),
            '25 October, 2006': datetime.date(2006, 10, 25),
        }
        invalid = {
            '2006-4-31': error_invalid,
            '200a-10-25': error_invalid,
            '10/25/06': error_invalid,
        }
        self.assertFieldOutput(DateField, valid, invalid, empty_value=None)

        # DateField with optional input_formats parameter
        valid = {
            datetime.date(2006, 10, 25): datetime.date(2006, 10, 25),
            datetime.datetime(2006, 10, 25, 14, 30): datetime.date(2006, 10, 25),
            '2006 10 25': datetime.date(2006, 10, 25),
        }
        invalid = {
            '2006-10-25': error_invalid,
            '25/10/2006': error_invalid,
            '25/10/06': error_invalid,
        }
        kwargs = {'input_formats':['%Y %m %d'],}
        self.assertFieldOutput(DateField,
            valid, invalid, field_kwargs=kwargs, empty_value=None
        )

    def test_GenericDateTimeField(self):
        error_invalid = ['Enter a valid date/time.']
        valid = {
            datetime.date(2006, 10, 25): datetime.datetime(2006, 10, 25, 0, 0),
            datetime.datetime(2006, 10, 25, 14, 30): datetime.datetime(2006, 10, 25, 14, 30),
            datetime.datetime(2006, 10, 25, 14, 30, 59): datetime.datetime(2006, 10, 25, 14, 30, 59),
            datetime.datetime(2006, 10, 25, 14, 30, 59, 200): datetime.datetime(2006, 10, 25, 14, 30, 59, 200),
            '2006-10-25 14:30:45': datetime.datetime(2006, 10, 25, 14, 30, 45),
            '2006-10-25 14:30:00': datetime.datetime(2006, 10, 25, 14, 30),
            '2006-10-25 14:30': datetime.datetime(2006, 10, 25, 14, 30),
            '2006-10-25': datetime.datetime(2006, 10, 25, 0, 0),
            '25/10/2006 14:30:45': datetime.datetime(2006, 10, 25, 14, 30, 45),
            '25/10/2006 14:30:00': datetime.datetime(2006, 10, 25, 14, 30),
            '25/10/2006 14:30': datetime.datetime(2006, 10, 25, 14, 30),
            '25/10/2006': datetime.datetime(2006, 10, 25, 0, 0),
            '25/10/06 14:30:45': datetime.datetime(2006, 10, 25, 14, 30, 45),
            '25/10/06 14:30:00': datetime.datetime(2006, 10, 25, 14, 30),
            '25/10/06 14:30': datetime.datetime(2006, 10, 25, 14, 30),
            '25/10/06': datetime.datetime(2006, 10, 25, 0, 0),
        }
        invalid = {
            'hello': error_invalid,
            '2006-10-25 4:30 p.m.': error_invalid,
        }
        self.assertFieldOutput(DateTimeField, valid, invalid, empty_value=None)

        # DateTimeField with optional input_formats paramter
        valid = {
            datetime.date(2006, 10, 25): datetime.datetime(2006, 10, 25, 0, 0),
            datetime.datetime(2006, 10, 25, 14, 30): datetime.datetime(2006, 10, 25, 14, 30),
            datetime.datetime(2006, 10, 25, 14, 30, 59): datetime.datetime(2006, 10, 25, 14, 30, 59),
            datetime.datetime(2006, 10, 25, 14, 30, 59, 200): datetime.datetime(2006, 10, 25, 14, 30, 59, 200),
            '2006 10 25 2:30 PM': datetime.datetime(2006, 10, 25, 14, 30),
        }
        invalid = {
            '2006-10-25 14:30:45': error_invalid,
        }
        kwargs = {'input_formats':['%Y %m %d %I:%M %p'],}
        self.assertFieldOutput(DateTimeField,
            valid, invalid, field_kwargs=kwargs, empty_value=None
        )
