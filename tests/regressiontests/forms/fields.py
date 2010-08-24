# -*- coding: utf-8 -*-
"""
##########
# Fields #
##########

Each Field class does some sort of validation. Each Field has a clean() method,
which either raises django.forms.ValidationError or returns the "clean"
data -- usually a Unicode object, but, in some rare cases, a list.

Each Field's __init__() takes at least these parameters:
    required -- Boolean that specifies whether the field is required.
                True by default.
    widget -- A Widget class, or instance of a Widget class, that should be
              used for this Field when displaying it. Each Field has a default
              Widget that it'll use if you don't specify this. In most cases,
              the default widget is TextInput.
    label -- A verbose name for this field, for use in displaying this field in
             a form. By default, Django will use a "pretty" version of the form
             field name, if the Field is part of a Form.
    initial -- A value to use in this Field's initial display. This value is
               *not* used as a fallback if data isn't given.

Other than that, the Field subclasses have class-specific options for
__init__(). For example, CharField has a max_length option.
"""
import datetime
import time
import re
import os
from decimal import Decimal

from unittest import TestCase

from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import *
from django.forms.widgets import RadioFieldRenderer


def fix_os_paths(x):
    if isinstance(x, basestring):
        return x.replace('\\', '/')
    elif isinstance(x, tuple):
        return tuple(fix_os_paths(list(x)))
    elif isinstance(x, list):
        return [fix_os_paths(y) for y in x]
    else:
        return x


class FieldsTests(TestCase):

    def assertRaisesErrorWithMessage(self, error, message, callable, *args, **kwargs):
        self.assertRaises(error, callable, *args, **kwargs)
        try:
            callable(*args, **kwargs)
        except error, e:
            self.assertEqual(message, str(e))

    # CharField ###################################################################

    def test_charfield_0(self):
        f = CharField()
        self.assertEqual(u'1', f.clean(1))
        self.assertEqual(u'hello', f.clean('hello'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertEqual(u'[1, 2, 3]', f.clean([1, 2, 3]))

    def test_charfield_1(self):
        f = CharField(required=False)
        self.assertEqual(u'1', f.clean(1))
        self.assertEqual(u'hello', f.clean('hello'))
        self.assertEqual(u'', f.clean(None))
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'[1, 2, 3]', f.clean([1, 2, 3]))

    def test_charfield_2(self):
        f = CharField(max_length=10, required=False)
        self.assertEqual(u'12345', f.clean('12345'))
        self.assertEqual(u'1234567890', f.clean('1234567890'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 10 characters (it has 11).']", f.clean, '1234567890a')

    def test_charfield_3(self):
        f = CharField(min_length=10, required=False)
        self.assertEqual(u'', f.clean(''))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 10 characters (it has 5).']", f.clean, '12345')
        self.assertEqual(u'1234567890', f.clean('1234567890'))
        self.assertEqual(u'1234567890a', f.clean('1234567890a'))

    def test_charfield_4(self):
        f = CharField(min_length=10, required=True)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 10 characters (it has 5).']", f.clean, '12345')
        self.assertEqual(u'1234567890', f.clean('1234567890'))
        self.assertEqual(u'1234567890a', f.clean('1234567890a'))

    # IntegerField ################################################################

    def test_integerfield_5(self):
        f = IntegerField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(1, f.clean('1'))
        self.assertEqual(True, isinstance(f.clean('1'), int))
        self.assertEqual(23, f.clean('23'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a whole number.']", f.clean, 'a')
        self.assertEqual(42, f.clean(42))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a whole number.']", f.clean, 3.14)
        self.assertEqual(1, f.clean('1 '))
        self.assertEqual(1, f.clean(' 1'))
        self.assertEqual(1, f.clean(' 1 '))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a whole number.']", f.clean, '1a')

    def test_integerfield_6(self):
        f = IntegerField(required=False)
        self.assertEqual(None, f.clean(''))
        self.assertEqual('None', repr(f.clean('')))
        self.assertEqual(None, f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertEqual(1, f.clean('1'))
        self.assertEqual(True, isinstance(f.clean('1'), int))
        self.assertEqual(23, f.clean('23'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a whole number.']", f.clean, 'a')
        self.assertEqual(1, f.clean('1 '))
        self.assertEqual(1, f.clean(' 1'))
        self.assertEqual(1, f.clean(' 1 '))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a whole number.']", f.clean, '1a')

    def test_integerfield_7(self):
        f = IntegerField(max_value=10)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(1, f.clean(1))
        self.assertEqual(10, f.clean(10))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is less than or equal to 10.']", f.clean, 11)
        self.assertEqual(10, f.clean('10'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is less than or equal to 10.']", f.clean, '11')

    def test_integerfield_8(self):
        f = IntegerField(min_value=10)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is greater than or equal to 10.']", f.clean, 1)
        self.assertEqual(10, f.clean(10))
        self.assertEqual(11, f.clean(11))
        self.assertEqual(10, f.clean('10'))
        self.assertEqual(11, f.clean('11'))

    def test_integerfield_9(self):
        f = IntegerField(min_value=10, max_value=20)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is greater than or equal to 10.']", f.clean, 1)
        self.assertEqual(10, f.clean(10))
        self.assertEqual(11, f.clean(11))
        self.assertEqual(10, f.clean('10'))
        self.assertEqual(11, f.clean('11'))
        self.assertEqual(20, f.clean(20))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is less than or equal to 20.']", f.clean, 21)

    # FloatField ##################################################################

    def test_floatfield_10(self):
        f = FloatField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(1.0, f.clean('1'))
        self.assertEqual(True, isinstance(f.clean('1'), float))
        self.assertEqual(23.0, f.clean('23'))
        self.assertEqual(3.1400000000000001, f.clean('3.14'))
        self.assertEqual(3.1400000000000001, f.clean(3.14))
        self.assertEqual(42.0, f.clean(42))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, 'a')
        self.assertEqual(1.0, f.clean('1.0 '))
        self.assertEqual(1.0, f.clean(' 1.0'))
        self.assertEqual(1.0, f.clean(' 1.0 '))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, '1.0a')

    def test_floatfield_11(self):
        f = FloatField(required=False)
        self.assertEqual(None, f.clean(''))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(1.0, f.clean('1'))

    def test_floatfield_12(self):
        f = FloatField(max_value=1.5, min_value=0.5)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is less than or equal to 1.5.']", f.clean, '1.6')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is greater than or equal to 0.5.']", f.clean, '0.4')
        self.assertEqual(1.5, f.clean('1.5'))
        self.assertEqual(0.5, f.clean('0.5'))

    # DecimalField ################################################################

    def test_decimalfield_13(self):
        f = DecimalField(max_digits=4, decimal_places=2)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(f.clean('1'), Decimal("1"))
        self.assertEqual(True, isinstance(f.clean('1'), Decimal))
        self.assertEqual(f.clean('23'), Decimal("23"))
        self.assertEqual(f.clean('3.14'), Decimal("3.14"))
        self.assertEqual(f.clean(3.14), Decimal("3.14"))
        self.assertEqual(f.clean(Decimal('3.14')), Decimal("3.14"))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, 'NaN')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, 'Inf')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, '-Inf')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, 'a')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, u'łąść')
        self.assertEqual(f.clean('1.0 '), Decimal("1.0"))
        self.assertEqual(f.clean(' 1.0'), Decimal("1.0"))
        self.assertEqual(f.clean(' 1.0 '), Decimal("1.0"))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, '1.0a')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 4 digits in total.']", f.clean, '123.45')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 2 decimal places.']", f.clean, '1.234')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 2 digits before the decimal point.']", f.clean, '123.4')
        self.assertEqual(f.clean('-12.34'), Decimal("-12.34"))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 4 digits in total.']", f.clean, '-123.45')
        self.assertEqual(f.clean('-.12'), Decimal("-0.12"))
        self.assertEqual(f.clean('-00.12'), Decimal("-0.12"))
        self.assertEqual(f.clean('-000.12'), Decimal("-0.12"))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 2 decimal places.']", f.clean, '-000.123')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 4 digits in total.']", f.clean, '-000.12345')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a number.']", f.clean, '--0.12')

    def test_decimalfield_14(self):
        f = DecimalField(max_digits=4, decimal_places=2, required=False)
        self.assertEqual(None, f.clean(''))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(f.clean('1'), Decimal("1"))

    def test_decimalfield_15(self):
        f = DecimalField(max_digits=4, decimal_places=2, max_value=Decimal('1.5'), min_value=Decimal('0.5'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is less than or equal to 1.5.']", f.clean, '1.6')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value is greater than or equal to 0.5.']", f.clean, '0.4')
        self.assertEqual(f.clean('1.5'), Decimal("1.5"))
        self.assertEqual(f.clean('0.5'), Decimal("0.5"))
        self.assertEqual(f.clean('.5'), Decimal("0.5"))
        self.assertEqual(f.clean('00.50'), Decimal("0.50"))

    def test_decimalfield_16(self):
        f = DecimalField(decimal_places=2)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 2 decimal places.']", f.clean, '0.00000001')

    def test_decimalfield_17(self):
        f = DecimalField(max_digits=3)
        # Leading whole zeros "collapse" to one digit.
        self.assertEqual(f.clean('0000000.10'), Decimal("0.1"))
        # But a leading 0 before the . doesn't count towards max_digits
        self.assertEqual(f.clean('0000000.100'), Decimal("0.100"))
        # Only leading whole zeros "collapse" to one digit.
        self.assertEqual(f.clean('000000.02'), Decimal('0.02'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 3 digits in total.']", f.clean, '000000.0002')
        self.assertEqual(f.clean('.002'), Decimal("0.002"))

    def test_decimalfield_18(self):
        f = DecimalField(max_digits=2, decimal_places=2)
        self.assertEqual(f.clean('.01'), Decimal(".01"))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure that there are no more than 0 digits before the decimal point.']", f.clean, '1.1')

    # DateField ###################################################################

    def test_datefield_19(self):
        f = DateField()
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('2006-10-25'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('10/25/2006'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('10/25/06'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('Oct 25 2006'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('October 25 2006'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('October 25, 2006'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('25 October 2006'))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('25 October, 2006'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, '2006-4-31')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, '200a-10-25')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, '25/10/06')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)

    def test_datefield_20(self):
        f = DateField(required=False)
        self.assertEqual(None, f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertEqual(None, f.clean(''))
        self.assertEqual('None', repr(f.clean('')))

    def test_datefield_21(self):
        f = DateField(input_formats=['%Y %m %d'])
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('2006 10 25'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, '2006-10-25')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, '10/25/2006')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, '10/25/06')

    # TimeField ###################################################################

    def test_timefield_22(self):
        f = TimeField()
        self.assertEqual(datetime.time(14, 25), f.clean(datetime.time(14, 25)))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(datetime.time(14, 25, 59)))
        self.assertEqual(datetime.time(14, 25), f.clean('14:25'))
        self.assertEqual(datetime.time(14, 25, 59), f.clean('14:25:59'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, 'hello')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, '1:24 p.m.')

    def test_timefield_23(self):
        f = TimeField(input_formats=['%I:%M %p'])
        self.assertEqual(datetime.time(14, 25), f.clean(datetime.time(14, 25)))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(datetime.time(14, 25, 59)))
        self.assertEqual(datetime.time(4, 25), f.clean('4:25 AM'))
        self.assertEqual(datetime.time(16, 25), f.clean('4:25 PM'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, '14:30:45')

    # DateTimeField ###############################################################

    def test_datetimefield_24(self):
        f = DateTimeField()
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59, 200), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean('2006-10-25 14:30:45'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006-10-25 14:30:00'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006-10-25 14:30'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean('2006-10-25'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean('10/25/2006 14:30:45'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/2006 14:30:00'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/2006 14:30'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean('10/25/2006'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45), f.clean('10/25/06 14:30:45'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/06 14:30:00'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('10/25/06 14:30'))
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean('10/25/06'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date/time.']", f.clean, 'hello')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date/time.']", f.clean, '2006-10-25 4:30 p.m.')

    def test_datetimefield_25(self):
        f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59, 200), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006 10 25 2:30 PM'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date/time.']", f.clean, '2006-10-25 14:30:45')

    def test_datetimefield_26(self):
        f = DateTimeField(required=False)
        self.assertEqual(None, f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertEqual(None, f.clean(''))
        self.assertEqual('None', repr(f.clean('')))

    # RegexField ##################################################################

    def test_regexfield_27(self):
        f = RegexField('^\d[A-F]\d$')
        self.assertEqual(u'2A2', f.clean('2A2'))
        self.assertEqual(u'3F3', f.clean('3F3'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, '3G3')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, ' 2A2')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, '2A2 ')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')

    def test_regexfield_28(self):
        f = RegexField('^\d[A-F]\d$', required=False)
        self.assertEqual(u'2A2', f.clean('2A2'))
        self.assertEqual(u'3F3', f.clean('3F3'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, '3G3')
        self.assertEqual(u'', f.clean(''))

    def test_regexfield_29(self):
        f = RegexField(re.compile('^\d[A-F]\d$'))
        self.assertEqual(u'2A2', f.clean('2A2'))
        self.assertEqual(u'3F3', f.clean('3F3'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, '3G3')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, ' 2A2')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, '2A2 ')

    def test_regexfield_30(self):
        f = RegexField('^\d\d\d\d$', error_message='Enter a four-digit number.')
        self.assertEqual(u'1234', f.clean('1234'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a four-digit number.']", f.clean, '123')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a four-digit number.']", f.clean, 'abcd')

    def test_regexfield_31(self):
        f = RegexField('^\d+$', min_length=5, max_length=10)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 5 characters (it has 3).']", f.clean, '123')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 5 characters (it has 3).', u'Enter a valid value.']", f.clean, 'abc')
        self.assertEqual(u'12345', f.clean('12345'))
        self.assertEqual(u'1234567890', f.clean('1234567890'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 10 characters (it has 11).']", f.clean, '12345678901')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid value.']", f.clean, '12345a')

    # EmailField ##################################################################

    def test_emailfield_32(self):
        f = EmailField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(u'person@example.com', f.clean('person@example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@bar')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@invalid-.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@-invalid.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@inv-.alid-.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@inv-.-alid.com')
        self.assertEqual(u'example@valid-----hyphens.com', f.clean('example@valid-----hyphens.com'))
        self.assertEqual(u'example@valid-with-hyphens.com', f.clean('example@valid-with-hyphens.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'example@.com')
        self.assertEqual(u'local@domain.with.idn.xyz\xe4\xf6\xfc\xdfabc.part.com', f.clean('local@domain.with.idn.xyzäöüßabc.part.com'))

    def test_email_regexp_for_performance(self):
        f = EmailField()
        # Check for runaway regex security problem. This will take for-freeking-ever
        # if the security fix isn't in place.
        self.assertRaisesErrorWithMessage(
                ValidationError,
                "[u'Enter a valid e-mail address.']",
                f.clean,
                'viewx3dtextx26qx3d@yahoo.comx26latlngx3d15854521645943074058'
            )

    def test_emailfield_33(self):
        f = EmailField(required=False)
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'', f.clean(None))
        self.assertEqual(u'person@example.com', f.clean('person@example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'foo@bar')

    def test_emailfield_34(self):
        f = EmailField(min_length=10, max_length=15)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 10 characters (it has 9).']", f.clean, 'a@foo.com')
        self.assertEqual(u'alf@foo.com', f.clean('alf@foo.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 15 characters (it has 20).']", f.clean, 'alf123456788@foo.com')

    # FileField ##################################################################

    def test_filefield_35(self):
        f = FileField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '', '')
        self.assertEqual('files/test1.pdf', f.clean('', 'files/test1.pdf'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None, '')
        self.assertEqual('files/test2.pdf', f.clean(None, 'files/test2.pdf'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'No file was submitted. Check the encoding type on the form.']", f.clean, SimpleUploadedFile('', ''))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'No file was submitted. Check the encoding type on the form.']", f.clean, SimpleUploadedFile('', ''), '')
        self.assertEqual('files/test3.pdf', f.clean(None, 'files/test3.pdf'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'No file was submitted. Check the encoding type on the form.']", f.clean, 'some content that is not a file')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'The submitted file is empty.']", f.clean, SimpleUploadedFile('name', None))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'The submitted file is empty.']", f.clean, SimpleUploadedFile('name', ''))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('name', 'Some File Content'))))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह'))))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('name', 'Some File Content'), 'files/test4.pdf')))

    def test_filefield_36(self):
        f = FileField(max_length = 5)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this filename has at most 5 characters (it has 18).']", f.clean, SimpleUploadedFile('test_maxlength.txt', 'hello world'))
        self.assertEqual('files/test1.pdf', f.clean('', 'files/test1.pdf'))
        self.assertEqual('files/test2.pdf', f.clean(None, 'files/test2.pdf'))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('name', 'Some File Content'))))

    # URLField ##################################################################

    def test_urlfield_37(self):
        f = URLField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(u'http://localhost/', f.clean('http://localhost'))
        self.assertEqual(u'http://example.com/', f.clean('http://example.com'))
        self.assertEqual(u'http://example.com./', f.clean('http://example.com.'))
        self.assertEqual(u'http://www.example.com/', f.clean('http://www.example.com'))
        self.assertEqual(u'http://www.example.com:8000/test', f.clean('http://www.example.com:8000/test'))
        self.assertEqual(u'http://valid-with-hyphens.com/', f.clean('valid-with-hyphens.com'))
        self.assertEqual(u'http://subdomain.domain.com/', f.clean('subdomain.domain.com'))
        self.assertEqual(u'http://200.8.9.10/', f.clean('http://200.8.9.10'))
        self.assertEqual(u'http://200.8.9.10:8000/test', f.clean('http://200.8.9.10:8000/test'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'foo')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://example')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://example.')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'com.')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, '.')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://invalid-.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://-invalid.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://inv-.alid-.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://inv-.-alid.com')
        self.assertEqual(u'http://valid-----hyphens.com/', f.clean('http://valid-----hyphens.com'))
        self.assertEqual(u'http://some.idn.xyz\xe4\xf6\xfc\xdfabc.domain.com:123/blah', f.clean('http://some.idn.xyzäöüßabc.domain.com:123/blah'))

    def test_url_regex_ticket11198(self):
        f = URLField()
        # hangs "forever" if catastrophic backtracking in ticket:#11198 not fixed
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://%s' % ("X"*200,))

        # a second test, to make sure the problem is really addressed, even on
        # domains that don't fail the domain label length check in the regex
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://%s' % ("X"*60,))

    def test_urlfield_38(self):
        f = URLField(required=False)
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'', f.clean(None))
        self.assertEqual(u'http://example.com/', f.clean('http://example.com'))
        self.assertEqual(u'http://www.example.com/', f.clean('http://www.example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'foo')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://example')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://example.')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://.com')

    def test_urlfield_39(self):
        f = URLField(verify_exists=True)
        self.assertEqual(u'http://www.google.com/', f.clean('http://www.google.com')) # This will fail if there's no Internet connection
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid URL.']", f.clean, 'http://example')
        self.assertRaises(ValidationError, f.clean, 'http://www.broken.djangoproject.com') # bad domain
        try:
            f.clean('http://www.broken.djangoproject.com') # bad domain
        except ValidationError, e:
            self.assertEqual("[u'This URL appears to be a broken link.']", str(e))
        self.assertRaises(ValidationError, f.clean, 'http://google.com/we-love-microsoft.html') # good domain, bad page
        try:
            f.clean('http://google.com/we-love-microsoft.html') # good domain, bad page
        except ValidationError, e:
            self.assertEqual("[u'This URL appears to be a broken link.']", str(e))
        # Valid and existent IDN
        self.assertEqual(u'http://\u05e2\u05d1\u05e8\u05d9\u05ea.idn.icann.org/', f.clean(u'http://עברית.idn.icann.org/'))
        # Valid but non-existent IDN
        try:
            f.clean(u'http://broken.עברית.idn.icann.org/')
        except ValidationError, e:
            self.assertEqual("[u'This URL appears to be a broken link.']", str(e))

    def test_urlfield_40(self):
        f = URLField(verify_exists=True, required=False)
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'http://www.google.com/', f.clean('http://www.google.com')) # This will fail if there's no Internet connection

    def test_urlfield_41(self):
        f = URLField(min_length=15, max_length=20)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at least 15 characters (it has 13).']", f.clean, 'http://f.com')
        self.assertEqual(u'http://example.com/', f.clean('http://example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 20 characters (it has 38).']", f.clean, 'http://abcdefghijklmnopqrstuvwxyz.com')

    def test_urlfield_42(self):
        f = URLField(required=False)
        self.assertEqual(u'http://example.com/', f.clean('example.com'))
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'https://example.com/', f.clean('https://example.com'))

    def test_urlfield_43(self):
        f = URLField()
        self.assertEqual(u'http://example.com/', f.clean('http://example.com'))
        self.assertEqual(u'http://example.com/test', f.clean('http://example.com/test'))

    def test_urlfield_ticket11826(self):
        f = URLField()
        self.assertEqual(u'http://example.com/?some_param=some_value', f.clean('http://example.com?some_param=some_value'))

    # BooleanField ################################################################

    def test_booleanfield_44(self):
        f = BooleanField()
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(True, f.clean(True))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, False)
        self.assertEqual(True, f.clean(1))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, 0)
        self.assertEqual(True, f.clean('Django rocks'))
        self.assertEqual(True, f.clean('True'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, 'False')

    def test_booleanfield_45(self):
        f = BooleanField(required=False)
        self.assertEqual(False, f.clean(''))
        self.assertEqual(False, f.clean(None))
        self.assertEqual(True, f.clean(True))
        self.assertEqual(False, f.clean(False))
        self.assertEqual(True, f.clean(1))
        self.assertEqual(False, f.clean(0))
        self.assertEqual(True, f.clean('1'))
        self.assertEqual(False, f.clean('0'))
        self.assertEqual(True, f.clean('Django rocks'))
        self.assertEqual(False, f.clean('False'))

    # ChoiceField #################################################################

    def test_choicefield_46(self):
        f = ChoiceField(choices=[('1', 'One'), ('2', 'Two')])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual(u'1', f.clean(1))
        self.assertEqual(u'1', f.clean('1'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 3 is not one of the available choices.']", f.clean, '3')

    def test_choicefield_47(self):
        f = ChoiceField(choices=[('1', 'One'), ('2', 'Two')], required=False)
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'', f.clean(None))
        self.assertEqual(u'1', f.clean(1))
        self.assertEqual(u'1', f.clean('1'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 3 is not one of the available choices.']", f.clean, '3')

    def test_choicefield_48(self):
        f = ChoiceField(choices=[('J', 'John'), ('P', 'Paul')])
        self.assertEqual(u'J', f.clean('J'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. John is not one of the available choices.']", f.clean, 'John')

    def test_choicefield_49(self):
        f = ChoiceField(choices=[('Numbers', (('1', 'One'), ('2', 'Two'))), ('Letters', (('3','A'),('4','B'))), ('5','Other')])
        self.assertEqual(u'1', f.clean(1))
        self.assertEqual(u'1', f.clean('1'))
        self.assertEqual(u'3', f.clean(3))
        self.assertEqual(u'3', f.clean('3'))
        self.assertEqual(u'5', f.clean(5))
        self.assertEqual(u'5', f.clean('5'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 6 is not one of the available choices.']", f.clean, '6')

    # TypedChoiceField ############################################################
    # TypedChoiceField is just like ChoiceField, except that coerced types will
    # be returned:

    def test_typedchoicefield_50(self):
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int)
        self.assertEqual(1, f.clean('1'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 2 is not one of the available choices.']", f.clean, '2')

    def test_typedchoicefield_51(self):
        # Different coercion, same validation.
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=float)
        self.assertEqual(1.0, f.clean('1'))

    def test_typedchoicefield_52(self):
        # This can also cause weirdness: be careful (bool(-1) == True, remember)
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=bool)
        self.assertEqual(True, f.clean('-1'))

    def test_typedchoicefield_53(self):
        # Even more weirdness: if you have a valid choice but your coercion function
        # can't coerce, you'll still get a validation error. Don't do this!
        f = TypedChoiceField(choices=[('A', 'A'), ('B', 'B')], coerce=int)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. B is not one of the available choices.']", f.clean, 'B')
        # Required fields require values
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')

    def test_typedchoicefield_54(self):
        # Non-required fields aren't required
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False)
        self.assertEqual('', f.clean(''))
        # If you want cleaning an empty value to return a different type, tell the field

    def test_typedchoicefield_55(self):
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False, empty_value=None)
        self.assertEqual(None, f.clean(''))

    # NullBooleanField ############################################################

    def test_nullbooleanfield_56(self):
        f = NullBooleanField()
        self.assertEqual(None, f.clean(''))
        self.assertEqual(True, f.clean(True))
        self.assertEqual(False, f.clean(False))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(False, f.clean('0'))
        self.assertEqual(True, f.clean('1'))
        self.assertEqual(None, f.clean('2'))
        self.assertEqual(None, f.clean('3'))
        self.assertEqual(None, f.clean('hello'))


    def test_nullbooleanfield_57(self):
        # Make sure that the internal value is preserved if using HiddenInput (#7753)
        class HiddenNullBooleanForm(Form):
            hidden_nullbool1 = NullBooleanField(widget=HiddenInput, initial=True)
            hidden_nullbool2 = NullBooleanField(widget=HiddenInput, initial=False)
        f = HiddenNullBooleanForm()
        self.assertEqual('<input type="hidden" name="hidden_nullbool1" value="True" id="id_hidden_nullbool1" /><input type="hidden" name="hidden_nullbool2" value="False" id="id_hidden_nullbool2" />', str(f))

    def test_nullbooleanfield_58(self):
        class HiddenNullBooleanForm(Form):
            hidden_nullbool1 = NullBooleanField(widget=HiddenInput, initial=True)
            hidden_nullbool2 = NullBooleanField(widget=HiddenInput, initial=False)
        f = HiddenNullBooleanForm({ 'hidden_nullbool1': 'True', 'hidden_nullbool2': 'False' })
        self.assertEqual(None, f.full_clean())
        self.assertEqual(True, f.cleaned_data['hidden_nullbool1'])
        self.assertEqual(False, f.cleaned_data['hidden_nullbool2'])

    def test_nullbooleanfield_59(self):
        # Make sure we're compatible with MySQL, which uses 0 and 1 for its boolean
        # values. (#9609)
        NULLBOOL_CHOICES = (('1', 'Yes'), ('0', 'No'), ('', 'Unknown'))
        class MySQLNullBooleanForm(Form):
            nullbool0 = NullBooleanField(widget=RadioSelect(choices=NULLBOOL_CHOICES))
            nullbool1 = NullBooleanField(widget=RadioSelect(choices=NULLBOOL_CHOICES))
            nullbool2 = NullBooleanField(widget=RadioSelect(choices=NULLBOOL_CHOICES))
        f = MySQLNullBooleanForm({ 'nullbool0': '1', 'nullbool1': '0', 'nullbool2': '' })
        self.assertEqual(None, f.full_clean())
        self.assertEqual(True, f.cleaned_data['nullbool0'])
        self.assertEqual(False, f.cleaned_data['nullbool1'])
        self.assertEqual(None, f.cleaned_data['nullbool2'])

    # MultipleChoiceField #########################################################

    def test_multiplechoicefield_60(self):
        f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two')])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertEqual([u'1'], f.clean([1]))
        self.assertEqual([u'1'], f.clean(['1']))
        self.assertEqual([u'1', u'2'], f.clean(['1', '2']))
        self.assertEqual([u'1', u'2'], f.clean([1, '2']))
        self.assertEqual([u'1', u'2'], f.clean((1, '2')))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a list of values.']", f.clean, 'hello')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, [])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, ())
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 3 is not one of the available choices.']", f.clean, ['3'])

    def test_multiplechoicefield_61(self):
        f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two')], required=False)
        self.assertEqual([], f.clean(''))
        self.assertEqual([], f.clean(None))
        self.assertEqual([u'1'], f.clean([1]))
        self.assertEqual([u'1'], f.clean(['1']))
        self.assertEqual([u'1', u'2'], f.clean(['1', '2']))
        self.assertEqual([u'1', u'2'], f.clean([1, '2']))
        self.assertEqual([u'1', u'2'], f.clean((1, '2')))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a list of values.']", f.clean, 'hello')
        self.assertEqual([], f.clean([]))
        self.assertEqual([], f.clean(()))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 3 is not one of the available choices.']", f.clean, ['3'])

    def test_multiplechoicefield_62(self):
        f = MultipleChoiceField(choices=[('Numbers', (('1', 'One'), ('2', 'Two'))), ('Letters', (('3','A'),('4','B'))), ('5','Other')])
        self.assertEqual([u'1'], f.clean([1]))
        self.assertEqual([u'1'], f.clean(['1']))
        self.assertEqual([u'1', u'5'], f.clean([1, 5]))
        self.assertEqual([u'1', u'5'], f.clean([1, '5']))
        self.assertEqual([u'1', u'5'], f.clean(['1', 5]))
        self.assertEqual([u'1', u'5'], f.clean(['1', '5']))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 6 is not one of the available choices.']", f.clean, ['6'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. 6 is not one of the available choices.']", f.clean, ['1','6'])

    # ComboField ##################################################################

    def test_combofield_63(self):
        f = ComboField(fields=[CharField(max_length=20), EmailField()])
        self.assertEqual(u'test@example.com', f.clean('test@example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 20 characters (it has 28).']", f.clean, 'longemailaddress@example.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'not an e-mail')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)

    def test_combofield_64(self):
        f = ComboField(fields=[CharField(max_length=20), EmailField()], required=False)
        self.assertEqual(u'test@example.com', f.clean('test@example.com'))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Ensure this value has at most 20 characters (it has 28).']", f.clean, 'longemailaddress@example.com')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid e-mail address.']", f.clean, 'not an e-mail')
        self.assertEqual(u'', f.clean(''))
        self.assertEqual(u'', f.clean(None))

    # FilePathField ###############################################################

    def test_filepathfield_65(self):
        path = os.path.abspath(forms.__file__)
        path = os.path.dirname(path) + '/'
        self.assertTrue(fix_os_paths(path).endswith('/django/forms/'))

    def test_filepathfield_66(self):
        path = forms.__file__
        path = os.path.dirname(os.path.abspath(path)) + '/'
        f = FilePathField(path=path)
        f.choices = [p for p in f.choices if p[0].endswith('.py')]
        f.choices.sort()
        expected = [
                ('/django/forms/__init__.py', '__init__.py'),
                ('/django/forms/fields.py', 'fields.py'),
                ('/django/forms/forms.py', 'forms.py'),
                ('/django/forms/formsets.py', 'formsets.py'),
                ('/django/forms/models.py', 'models.py'),
                ('/django/forms/util.py', 'util.py'),
                ('/django/forms/widgets.py', 'widgets.py')
            ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Select a valid choice. fields.py is not one of the available choices.']", f.clean, 'fields.py')
        assert fix_os_paths(f.clean(path + 'fields.py')).endswith('/django/forms/fields.py')

    def test_filepathfield_67(self):
        path = forms.__file__
        path = os.path.dirname(os.path.abspath(path)) + '/'
        f = FilePathField(path=path, match='^.*?\.py$')
        f.choices.sort()
        expected = [
                ('/django/forms/__init__.py', '__init__.py'),
                ('/django/forms/fields.py', 'fields.py'),
                ('/django/forms/forms.py', 'forms.py'),
                ('/django/forms/formsets.py', 'formsets.py'),
                ('/django/forms/models.py', 'models.py'),
                ('/django/forms/util.py', 'util.py'),
                ('/django/forms/widgets.py', 'widgets.py')
            ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))

    def test_filepathfield_68(self):
        path = os.path.abspath(forms.__file__)
        path = os.path.dirname(path) + '/'
        f = FilePathField(path=path, recursive=True, match='^.*?\.py$')
        f.choices.sort()
        expected = [
                ('/django/forms/__init__.py', '__init__.py'),
                ('/django/forms/extras/__init__.py', 'extras/__init__.py'),
                ('/django/forms/extras/widgets.py', 'extras/widgets.py'),
                ('/django/forms/fields.py', 'fields.py'),
                ('/django/forms/forms.py', 'forms.py'),
                ('/django/forms/formsets.py', 'formsets.py'),
                ('/django/forms/models.py', 'models.py'),
                ('/django/forms/util.py', 'util.py'),
                ('/django/forms/widgets.py', 'widgets.py')
            ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))

    # SplitDateTimeField ##########################################################

    def test_splitdatetimefield_69(self):
        from django.forms.widgets import SplitDateTimeWidget
        f = SplitDateTimeField()
        assert isinstance(f.widget, SplitDateTimeWidget)
        self.assertEqual(datetime.datetime(2006, 1, 10, 7, 30), f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)]))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, None)
        self.assertRaisesErrorWithMessage(ValidationError, "[u'This field is required.']", f.clean, '')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a list of values.']", f.clean, 'hello')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.', u'Enter a valid time.']", f.clean, ['hello', 'there'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, ['2006-01-10', 'there'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, ['hello', '07:30'])

    def test_splitdatetimefield_70(self):
        f = SplitDateTimeField(required=False)
        self.assertEqual(datetime.datetime(2006, 1, 10, 7, 30), f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)]))
        self.assertEqual(datetime.datetime(2006, 1, 10, 7, 30), f.clean(['2006-01-10', '07:30']))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(None, f.clean(''))
        self.assertEqual(None, f.clean(['']))
        self.assertEqual(None, f.clean(['', '']))
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a list of values.']", f.clean, 'hello')
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.', u'Enter a valid time.']", f.clean, ['hello', 'there'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, ['2006-01-10', 'there'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, ['hello', '07:30'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, ['2006-01-10', ''])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid time.']", f.clean, ['2006-01-10'])
        self.assertRaisesErrorWithMessage(ValidationError, "[u'Enter a valid date.']", f.clean, ['', '07:30'])
