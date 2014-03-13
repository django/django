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
from __future__ import unicode_literals

import datetime
import pickle
import re
import os
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import *
from django.test import SimpleTestCase
from django.utils import formats
from django.utils import six
from django.utils import translation
from django.utils._os import upath


def fix_os_paths(x):
    if isinstance(x, six.string_types):
        return x.replace('\\', '/')
    elif isinstance(x, tuple):
        return tuple(fix_os_paths(list(x)))
    elif isinstance(x, list):
        return [fix_os_paths(y) for y in x]
    else:
        return x


class FieldsTests(SimpleTestCase):

    def assertWidgetRendersTo(self, field, to):
        class _Form(Form):
            f = field
        self.assertHTMLEqual(str(_Form()['f']), to)

    def test_field_sets_widget_is_required(self):
        self.assertTrue(Field(required=True).widget.is_required)
        self.assertFalse(Field(required=False).widget.is_required)

    def test_cooperative_multiple_inheritance(self):
        class A(object):
            def __init__(self):
                self.class_a_var = True
                super(A, self).__init__()


        class ComplexField(Field, A):
            def __init__(self):
                super(ComplexField, self).__init__()

        f = ComplexField()
        self.assertTrue(f.class_a_var)

    # CharField ###################################################################

    def test_charfield_1(self):
        f = CharField()
        self.assertEqual('1', f.clean(1))
        self.assertEqual('hello', f.clean('hello'))
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertEqual('[1, 2, 3]', f.clean([1, 2, 3]))
        self.assertEqual(f.max_length, None)
        self.assertEqual(f.min_length, None)

    def test_charfield_2(self):
        f = CharField(required=False)
        self.assertEqual('1', f.clean(1))
        self.assertEqual('hello', f.clean('hello'))
        self.assertEqual('', f.clean(None))
        self.assertEqual('', f.clean(''))
        self.assertEqual('[1, 2, 3]', f.clean([1, 2, 3]))
        self.assertEqual(f.max_length, None)
        self.assertEqual(f.min_length, None)

    def test_charfield_3(self):
        f = CharField(max_length=10, required=False)
        self.assertEqual('12345', f.clean('12345'))
        self.assertEqual('1234567890', f.clean('1234567890'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 10 characters (it has 11).'", f.clean, '1234567890a')
        self.assertEqual(f.max_length, 10)
        self.assertEqual(f.min_length, None)

    def test_charfield_4(self):
        f = CharField(min_length=10, required=False)
        self.assertEqual('', f.clean(''))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 10 characters (it has 5).'", f.clean, '12345')
        self.assertEqual('1234567890', f.clean('1234567890'))
        self.assertEqual('1234567890a', f.clean('1234567890a'))
        self.assertEqual(f.max_length, None)
        self.assertEqual(f.min_length, 10)

    def test_charfield_5(self):
        f = CharField(min_length=10, required=True)
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 10 characters (it has 5).'", f.clean, '12345')
        self.assertEqual('1234567890', f.clean('1234567890'))
        self.assertEqual('1234567890a', f.clean('1234567890a'))
        self.assertEqual(f.max_length, None)
        self.assertEqual(f.min_length, 10)

    def test_charfield_length_not_int(self):
        """
        Ensure that setting min_length or max_length to something that is not a
        number returns an exception.
        """
        self.assertRaises(ValueError, CharField, min_length='a')
        self.assertRaises(ValueError, CharField, max_length='a')
        self.assertRaises(ValueError, CharField, 'a')

    def test_charfield_widget_attrs(self):
        """
        Ensure that CharField.widget_attrs() always returns a dictionary.
        Refs #15912
        """
        # Return an empty dictionary if max_length is None
        f = CharField()
        self.assertEqual(f.widget_attrs(TextInput()), {})

        # Or if the widget is not TextInput or PasswordInput
        f = CharField(max_length=10)
        self.assertEqual(f.widget_attrs(HiddenInput()), {})

        # Otherwise, return a maxlength attribute equal to max_length
        self.assertEqual(f.widget_attrs(TextInput()), {'maxlength': '10'})
        self.assertEqual(f.widget_attrs(PasswordInput()), {'maxlength': '10'})

    # IntegerField ################################################################

    def test_integerfield_1(self):
        f = IntegerField()
        self.assertWidgetRendersTo(f, '<input type="number" name="f" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual(1, f.clean('1'))
        self.assertEqual(True, isinstance(f.clean('1'), int))
        self.assertEqual(23, f.clean('23'))
        self.assertRaisesMessage(ValidationError, "'Enter a whole number.'", f.clean, 'a')
        self.assertEqual(42, f.clean(42))
        self.assertRaisesMessage(ValidationError, "'Enter a whole number.'", f.clean, 3.14)
        self.assertEqual(1, f.clean('1 '))
        self.assertEqual(1, f.clean(' 1'))
        self.assertEqual(1, f.clean(' 1 '))
        self.assertRaisesMessage(ValidationError, "'Enter a whole number.'", f.clean, '1a')
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, None)

    def test_integerfield_2(self):
        f = IntegerField(required=False)
        self.assertEqual(None, f.clean(''))
        self.assertEqual('None', repr(f.clean('')))
        self.assertEqual(None, f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertEqual(1, f.clean('1'))
        self.assertEqual(True, isinstance(f.clean('1'), int))
        self.assertEqual(23, f.clean('23'))
        self.assertRaisesMessage(ValidationError, "'Enter a whole number.'", f.clean, 'a')
        self.assertEqual(1, f.clean('1 '))
        self.assertEqual(1, f.clean(' 1'))
        self.assertEqual(1, f.clean(' 1 '))
        self.assertRaisesMessage(ValidationError, "'Enter a whole number.'", f.clean, '1a')
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, None)

    def test_integerfield_3(self):
        f = IntegerField(max_value=10)
        self.assertWidgetRendersTo(f, '<input max="10" type="number" name="f" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual(1, f.clean(1))
        self.assertEqual(10, f.clean(10))
        self.assertRaisesMessage(ValidationError, "'Ensure this value is less than or equal to 10.'", f.clean, 11)
        self.assertEqual(10, f.clean('10'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value is less than or equal to 10.'", f.clean, '11')
        self.assertEqual(f.max_value, 10)
        self.assertEqual(f.min_value, None)

    def test_integerfield_4(self):
        f = IntegerField(min_value=10)
        self.assertWidgetRendersTo(f, '<input id="id_f" type="number" name="f" min="10" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertRaisesMessage(ValidationError, "'Ensure this value is greater than or equal to 10.'", f.clean, 1)
        self.assertEqual(10, f.clean(10))
        self.assertEqual(11, f.clean(11))
        self.assertEqual(10, f.clean('10'))
        self.assertEqual(11, f.clean('11'))
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, 10)

    def test_integerfield_5(self):
        f = IntegerField(min_value=10, max_value=20)
        self.assertWidgetRendersTo(f, '<input id="id_f" max="20" type="number" name="f" min="10" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertRaisesMessage(ValidationError, "'Ensure this value is greater than or equal to 10.'", f.clean, 1)
        self.assertEqual(10, f.clean(10))
        self.assertEqual(11, f.clean(11))
        self.assertEqual(10, f.clean('10'))
        self.assertEqual(11, f.clean('11'))
        self.assertEqual(20, f.clean(20))
        self.assertRaisesMessage(ValidationError, "'Ensure this value is less than or equal to 20.'", f.clean, 21)
        self.assertEqual(f.max_value, 20)
        self.assertEqual(f.min_value, 10)

    def test_integerfield_localized(self):
        """
        Make sure localized IntegerField's widget renders to a text input with
        no number input specific attributes.
        """
        f1 = IntegerField(localize=True)
        self.assertWidgetRendersTo(f1, '<input id="id_f" name="f" type="text" />')

    def test_integerfield_subclass(self):
        """
        Test that class-defined widget is not overwritten by __init__ (#22245).
        """
        class MyIntegerField(IntegerField):
            widget = Textarea

        f = MyIntegerField()
        self.assertEqual(f.widget.__class__, Textarea)
        f = MyIntegerField(localize=True)
        self.assertEqual(f.widget.__class__, Textarea)

    # FloatField ##################################################################

    def test_floatfield_1(self):
        f = FloatField()
        self.assertWidgetRendersTo(f, '<input step="any" type="number" name="f" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual(1.0, f.clean('1'))
        self.assertEqual(True, isinstance(f.clean('1'), float))
        self.assertEqual(23.0, f.clean('23'))
        self.assertEqual(3.1400000000000001, f.clean('3.14'))
        self.assertEqual(3.1400000000000001, f.clean(3.14))
        self.assertEqual(42.0, f.clean(42))
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, 'a')
        self.assertEqual(1.0, f.clean('1.0 '))
        self.assertEqual(1.0, f.clean(' 1.0'))
        self.assertEqual(1.0, f.clean(' 1.0 '))
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, '1.0a')
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, None)

    def test_floatfield_2(self):
        f = FloatField(required=False)
        self.assertEqual(None, f.clean(''))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(1.0, f.clean('1'))
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, None)

    def test_floatfield_3(self):
        f = FloatField(max_value=1.5, min_value=0.5)
        self.assertWidgetRendersTo(f, '<input step="any" name="f" min="0.5" max="1.5" type="number" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'Ensure this value is less than or equal to 1.5.'", f.clean, '1.6')
        self.assertRaisesMessage(ValidationError, "'Ensure this value is greater than or equal to 0.5.'", f.clean, '0.4')
        self.assertEqual(1.5, f.clean('1.5'))
        self.assertEqual(0.5, f.clean('0.5'))
        self.assertEqual(f.max_value, 1.5)
        self.assertEqual(f.min_value, 0.5)

    def test_floatfield_localized(self):
        """
        Make sure localized FloatField's widget renders to a text input with
        no number input specific attributes.
        """
        f = FloatField(localize=True)
        self.assertWidgetRendersTo(f, '<input id="id_f" name="f" type="text" />')

    def test_floatfield_changed(self):
        f = FloatField()
        n = 4.35
        self.assertFalse(f._has_changed(n, '4.3500'))

        with translation.override('fr'):
            with self.settings(USE_L10N=True):
                f = FloatField(localize=True)
                localized_n = formats.localize_input(n)  # -> '4,35' in French
                self.assertFalse(f._has_changed(n, localized_n))

    # DecimalField ################################################################

    def test_decimalfield_1(self):
        f = DecimalField(max_digits=4, decimal_places=2)
        self.assertWidgetRendersTo(f, '<input id="id_f" step="0.01" type="number" name="f" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual(f.clean('1'), Decimal("1"))
        self.assertEqual(True, isinstance(f.clean('1'), Decimal))
        self.assertEqual(f.clean('23'), Decimal("23"))
        self.assertEqual(f.clean('3.14'), Decimal("3.14"))
        self.assertEqual(f.clean(3.14), Decimal("3.14"))
        self.assertEqual(f.clean(Decimal('3.14')), Decimal("3.14"))
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, 'NaN')
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, 'Inf')
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, '-Inf')
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, 'a')
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, 'łąść')
        self.assertEqual(f.clean('1.0 '), Decimal("1.0"))
        self.assertEqual(f.clean(' 1.0'), Decimal("1.0"))
        self.assertEqual(f.clean(' 1.0 '), Decimal("1.0"))
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, '1.0a')
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 4 digits in total.'", f.clean, '123.45')
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 decimal places.'", f.clean, '1.234')
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 digits before the decimal point.'", f.clean, '123.4')
        self.assertEqual(f.clean('-12.34'), Decimal("-12.34"))
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 4 digits in total.'", f.clean, '-123.45')
        self.assertEqual(f.clean('-.12'), Decimal("-0.12"))
        self.assertEqual(f.clean('-00.12'), Decimal("-0.12"))
        self.assertEqual(f.clean('-000.12'), Decimal("-0.12"))
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 decimal places.'", f.clean, '-000.123')
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 4 digits in total.'", f.clean, '-000.12345')
        self.assertRaisesMessage(ValidationError, "'Enter a number.'", f.clean, '--0.12')
        self.assertEqual(f.max_digits, 4)
        self.assertEqual(f.decimal_places, 2)
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, None)

    def test_decimalfield_2(self):
        f = DecimalField(max_digits=4, decimal_places=2, required=False)
        self.assertEqual(None, f.clean(''))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(f.clean('1'), Decimal("1"))
        self.assertEqual(f.max_digits, 4)
        self.assertEqual(f.decimal_places, 2)
        self.assertEqual(f.max_value, None)
        self.assertEqual(f.min_value, None)

    def test_decimalfield_3(self):
        f = DecimalField(max_digits=4, decimal_places=2, max_value=Decimal('1.5'), min_value=Decimal('0.5'))
        self.assertWidgetRendersTo(f, '<input step="0.01" name="f" min="0.5" max="1.5" type="number" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'Ensure this value is less than or equal to 1.5.'", f.clean, '1.6')
        self.assertRaisesMessage(ValidationError, "'Ensure this value is greater than or equal to 0.5.'", f.clean, '0.4')
        self.assertEqual(f.clean('1.5'), Decimal("1.5"))
        self.assertEqual(f.clean('0.5'), Decimal("0.5"))
        self.assertEqual(f.clean('.5'), Decimal("0.5"))
        self.assertEqual(f.clean('00.50'), Decimal("0.50"))
        self.assertEqual(f.max_digits, 4)
        self.assertEqual(f.decimal_places, 2)
        self.assertEqual(f.max_value, Decimal('1.5'))
        self.assertEqual(f.min_value, Decimal('0.5'))

    def test_decimalfield_4(self):
        f = DecimalField(decimal_places=2)
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 2 decimal places.'", f.clean, '0.00000001')

    def test_decimalfield_5(self):
        f = DecimalField(max_digits=3)
        # Leading whole zeros "collapse" to one digit.
        self.assertEqual(f.clean('0000000.10'), Decimal("0.1"))
        # But a leading 0 before the . doesn't count towards max_digits
        self.assertEqual(f.clean('0000000.100'), Decimal("0.100"))
        # Only leading whole zeros "collapse" to one digit.
        self.assertEqual(f.clean('000000.02'), Decimal('0.02'))
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 3 digits in total.'", f.clean, '000000.0002')
        self.assertEqual(f.clean('.002'), Decimal("0.002"))

    def test_decimalfield_6(self):
        f = DecimalField(max_digits=2, decimal_places=2)
        self.assertEqual(f.clean('.01'), Decimal(".01"))
        self.assertRaisesMessage(ValidationError, "'Ensure that there are no more than 0 digits before the decimal point.'", f.clean, '1.1')

    def test_decimalfield_widget_attrs(self):
        f = DecimalField(max_digits=6, decimal_places=2)
        self.assertEqual(f.widget_attrs(Widget()), {})
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': '0.01'})
        f = DecimalField(max_digits=10, decimal_places=0)
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': '1'})
        f = DecimalField(max_digits=19, decimal_places=19)
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': '1e-19'})
        f = DecimalField(max_digits=20)
        self.assertEqual(f.widget_attrs(NumberInput()), {'step': 'any'})

    def test_decimalfield_localized(self):
        """
        Make sure localized DecimalField's widget renders to a text input with
        no number input specific attributes.
        """
        f = DecimalField(localize=True)
        self.assertWidgetRendersTo(f, '<input id="id_f" name="f" type="text" />')

    def test_decimalfield_changed(self):
        f = DecimalField(max_digits=2, decimal_places=2)
        d = Decimal("0.1")
        self.assertFalse(f._has_changed(d, '0.10'))
        self.assertTrue(f._has_changed(d, '0.101'))

        with translation.override('fr'):
            with self.settings(USE_L10N=True):
                f = DecimalField(max_digits=2, decimal_places=2, localize=True)
                localized_d = formats.localize_input(d)  # -> '0,1' in French
                self.assertFalse(f._has_changed(d, localized_d))

    # DateField ###################################################################

    def test_datefield_1(self):
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
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '2006-4-31')
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '200a-10-25')
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '25/10/06')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)

    def test_datefield_2(self):
        f = DateField(required=False)
        self.assertEqual(None, f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertEqual(None, f.clean(''))
        self.assertEqual('None', repr(f.clean('')))

    def test_datefield_3(self):
        f = DateField(input_formats=['%Y %m %d'])
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean('2006 10 25'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '2006-10-25')
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '10/25/2006')
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '10/25/06')

    def test_datefield_4(self):
        # Test whitespace stripping behavior (#5714)
        f = DateField()
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(' 10/25/2006 '))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(' 10/25/06 '))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(' Oct 25   2006 '))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(' October  25 2006 '))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(' October 25, 2006 '))
        self.assertEqual(datetime.date(2006, 10, 25), f.clean(' 25 October 2006 '))
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, '   ')

    def test_datefield_5(self):
        # Test null bytes (#18982)
        f = DateField()
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, 'a\x00b')

    def test_datefield_changed(self):
        format = '%d/%m/%Y'
        f = DateField(input_formats=[format])
        d = datetime.date(2007, 9, 17)
        self.assertFalse(f._has_changed(d, '17/09/2007'))

    def test_datefield_strptime(self):
        """Test that field.strptime doesn't raise an UnicodeEncodeError (#16123)"""
        f = DateField()
        try:
            f.strptime('31 мая 2011', '%d-%b-%y')
        except Exception as e:
            # assertIsInstance or assertRaises cannot be used because UnicodeEncodeError
            # is a subclass of ValueError
            self.assertEqual(e.__class__, ValueError)

    # TimeField ###################################################################

    def test_timefield_1(self):
        f = TimeField()
        self.assertEqual(datetime.time(14, 25), f.clean(datetime.time(14, 25)))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(datetime.time(14, 25, 59)))
        self.assertEqual(datetime.time(14, 25), f.clean('14:25'))
        self.assertEqual(datetime.time(14, 25, 59), f.clean('14:25:59'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, 'hello')
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, '1:24 p.m.')

    def test_timefield_2(self):
        f = TimeField(input_formats=['%I:%M %p'])
        self.assertEqual(datetime.time(14, 25), f.clean(datetime.time(14, 25)))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(datetime.time(14, 25, 59)))
        self.assertEqual(datetime.time(4, 25), f.clean('4:25 AM'))
        self.assertEqual(datetime.time(16, 25), f.clean('4:25 PM'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, '14:30:45')

    def test_timefield_3(self):
        f = TimeField()
        # Test whitespace stripping behavior (#5714)
        self.assertEqual(datetime.time(14, 25), f.clean(' 14:25 '))
        self.assertEqual(datetime.time(14, 25, 59), f.clean(' 14:25:59 '))
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, '   ')

    def test_timefield_changed(self):
        t1 = datetime.time(12, 51, 34, 482548)
        t2 = datetime.time(12, 51)
        f = TimeField(input_formats=['%H:%M', '%H:%M %p'])
        self.assertTrue(f._has_changed(t1, '12:51'))
        self.assertFalse(f._has_changed(t2, '12:51'))
        self.assertFalse(f._has_changed(t2, '12:51 PM'))

    # DateTimeField ###############################################################

    def test_datetimefield_1(self):
        f = DateTimeField()
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59, 200), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200)))
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
        self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'", f.clean, 'hello')
        self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'", f.clean, '2006-10-25 4:30 p.m.')

    def test_datetimefield_2(self):
        f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
        self.assertEqual(datetime.datetime(2006, 10, 25, 0, 0), f.clean(datetime.date(2006, 10, 25)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean(datetime.datetime(2006, 10, 25, 14, 30)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 59, 200), f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200)))
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30), f.clean('2006 10 25 2:30 PM'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'", f.clean, '2006-10-25 14:30:45')

    def test_datetimefield_3(self):
        f = DateTimeField(required=False)
        self.assertEqual(None, f.clean(None))
        self.assertEqual('None', repr(f.clean(None)))
        self.assertEqual(None, f.clean(''))
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
        self.assertRaisesMessage(ValidationError, "'Enter a valid date/time.'", f.clean, '   ')

    def test_datetimefield_5(self):
        f = DateTimeField(input_formats=['%Y.%m.%d %H:%M:%S.%f'])
        self.assertEqual(datetime.datetime(2006, 10, 25, 14, 30, 45, 200), f.clean('2006.10.25 14:30:45.0002'))

    def test_datetimefield_changed(self):
        format = '%Y %m %d %I:%M %p'
        f = DateTimeField(input_formats=[format])
        d = datetime.datetime(2006, 9, 17, 14, 30, 0)
        self.assertFalse(f._has_changed(d, '2006 09 17 2:30 PM'))

    # RegexField ##################################################################

    def test_regexfield_1(self):
        f = RegexField('^\d[A-F]\d$')
        self.assertEqual('2A2', f.clean('2A2'))
        self.assertEqual('3F3', f.clean('3F3'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, '3G3')
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, ' 2A2')
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, '2A2 ')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')

    def test_regexfield_2(self):
        f = RegexField('^\d[A-F]\d$', required=False)
        self.assertEqual('2A2', f.clean('2A2'))
        self.assertEqual('3F3', f.clean('3F3'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, '3G3')
        self.assertEqual('', f.clean(''))

    def test_regexfield_3(self):
        f = RegexField(re.compile('^\d[A-F]\d$'))
        self.assertEqual('2A2', f.clean('2A2'))
        self.assertEqual('3F3', f.clean('3F3'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, '3G3')
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, ' 2A2')
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, '2A2 ')

    def test_regexfield_4(self):
        f = RegexField('^\d\d\d\d$', error_message='Enter a four-digit number.')
        self.assertEqual('1234', f.clean('1234'))
        self.assertRaisesMessage(ValidationError, "'Enter a four-digit number.'", f.clean, '123')
        self.assertRaisesMessage(ValidationError, "'Enter a four-digit number.'", f.clean, 'abcd')

    def test_regexfield_5(self):
        f = RegexField('^\d+$', min_length=5, max_length=10)
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 5 characters (it has 3).'", f.clean, '123')
        six.assertRaisesRegex(self, ValidationError, "'Ensure this value has at least 5 characters \(it has 3\)\.', u?'Enter a valid value\.'", f.clean, 'abc')
        self.assertEqual('12345', f.clean('12345'))
        self.assertEqual('1234567890', f.clean('1234567890'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 10 characters (it has 11).'", f.clean, '12345678901')
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, '12345a')

    def test_regexfield_6(self):
        """
        Ensure that it works with unicode characters.
        Refs #.
        """
        f = RegexField('^\w+$')
        self.assertEqual('éèøçÎÎ你好', f.clean('éèøçÎÎ你好'))

    def test_change_regex_after_init(self):
        f = RegexField('^[a-z]+$')
        f.regex = '^\d+$'
        self.assertEqual('1234', f.clean('1234'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid value.'", f.clean, 'abcd')

    # EmailField ##################################################################
    # See also validators tests for validate_email specific tests

    def test_emailfield_1(self):
        f = EmailField()
        self.assertWidgetRendersTo(f, '<input type="email" name="f" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual('person@example.com', f.clean('person@example.com'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid email address.'", f.clean, 'foo')
        self.assertEqual('local@domain.with.idn.xyz\xe4\xf6\xfc\xdfabc.part.com',
            f.clean('local@domain.with.idn.xyzäöüßabc.part.com'))

    def test_email_regexp_for_performance(self):
        f = EmailField()
        # Check for runaway regex security problem. This will take for-freeking-ever
        # if the security fix isn't in place.
        addr = 'viewx3dtextx26qx3d@yahoo.comx26latlngx3d15854521645943074058'
        self.assertEqual(addr, f.clean(addr))

    def test_emailfield_not_required(self):
        f = EmailField(required=False)
        self.assertEqual('', f.clean(''))
        self.assertEqual('', f.clean(None))
        self.assertEqual('person@example.com', f.clean('person@example.com'))
        self.assertEqual('example@example.com', f.clean('      example@example.com  \t   \t '))
        self.assertRaisesMessage(ValidationError, "'Enter a valid email address.'", f.clean, 'foo')

    def test_emailfield_min_max_length(self):
        f = EmailField(min_length=10, max_length=15)
        self.assertWidgetRendersTo(f, '<input id="id_f" type="email" name="f" maxlength="15" />')
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 10 characters (it has 9).'", f.clean, 'a@foo.com')
        self.assertEqual('alf@foo.com', f.clean('alf@foo.com'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 15 characters (it has 20).'", f.clean, 'alf123456788@foo.com')

    # FileField ##################################################################

    def test_filefield_1(self):
        f = FileField()
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '', '')
        self.assertEqual('files/test1.pdf', f.clean('', 'files/test1.pdf'))
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None, '')
        self.assertEqual('files/test2.pdf', f.clean(None, 'files/test2.pdf'))
        self.assertRaisesMessage(ValidationError, "'No file was submitted. Check the encoding type on the form.'", f.clean, SimpleUploadedFile('', b''))
        self.assertRaisesMessage(ValidationError, "'No file was submitted. Check the encoding type on the form.'", f.clean, SimpleUploadedFile('', b''), '')
        self.assertEqual('files/test3.pdf', f.clean(None, 'files/test3.pdf'))
        self.assertRaisesMessage(ValidationError, "'No file was submitted. Check the encoding type on the form.'", f.clean, 'some content that is not a file')
        self.assertRaisesMessage(ValidationError, "'The submitted file is empty.'", f.clean, SimpleUploadedFile('name', None))
        self.assertRaisesMessage(ValidationError, "'The submitted file is empty.'", f.clean, SimpleUploadedFile('name', b''))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('name', b'Some File Content'))))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह'.encode('utf-8')))))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('name', b'Some File Content'), 'files/test4.pdf')))

    def test_filefield_2(self):
        f = FileField(max_length = 5)
        self.assertRaisesMessage(ValidationError, "'Ensure this filename has at most 5 characters (it has 18).'", f.clean, SimpleUploadedFile('test_maxlength.txt', b'hello world'))
        self.assertEqual('files/test1.pdf', f.clean('', 'files/test1.pdf'))
        self.assertEqual('files/test2.pdf', f.clean(None, 'files/test2.pdf'))
        self.assertEqual(SimpleUploadedFile, type(f.clean(SimpleUploadedFile('name', b'Some File Content'))))

    def test_filefield_3(self):
        f = FileField(allow_empty_file=True)
        self.assertEqual(SimpleUploadedFile,
                         type(f.clean(SimpleUploadedFile('name', b''))))

    def test_filefield_changed(self):
        '''
        Test for the behavior of _has_changed for FileField. The value of data will
        more than likely come from request.FILES. The value of initial data will
        likely be a filename stored in the database. Since its value is of no use to
        a FileField it is ignored.
        '''
        f = FileField()

        # No file was uploaded and no initial data.
        self.assertFalse(f._has_changed('', None))

        # A file was uploaded and no initial data.
        self.assertTrue(f._has_changed('', {'filename': 'resume.txt', 'content': 'My resume'}))

        # A file was not uploaded, but there is initial data
        self.assertFalse(f._has_changed('resume.txt', None))

        # A file was uploaded and there is initial data (file identity is not dealt
        # with here)
        self.assertTrue(f._has_changed('resume.txt', {'filename': 'resume.txt', 'content': 'My resume'}))


    # URLField ##################################################################

    def test_urlfield_1(self):
        f = URLField()
        self.assertWidgetRendersTo(f, '<input type="url" name="f" id="id_f" />')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual('http://localhost/', f.clean('http://localhost'))
        self.assertEqual('http://example.com/', f.clean('http://example.com'))
        self.assertEqual('http://example.com./', f.clean('http://example.com.'))
        self.assertEqual('http://www.example.com/', f.clean('http://www.example.com'))
        self.assertEqual('http://www.example.com:8000/test', f.clean('http://www.example.com:8000/test'))
        self.assertEqual('http://valid-with-hyphens.com/', f.clean('valid-with-hyphens.com'))
        self.assertEqual('http://subdomain.domain.com/', f.clean('subdomain.domain.com'))
        self.assertEqual('http://200.8.9.10/', f.clean('http://200.8.9.10'))
        self.assertEqual('http://200.8.9.10:8000/test', f.clean('http://200.8.9.10:8000/test'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'foo')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://example')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://example.')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'com.')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, '.')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://.com')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://invalid-.com')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://-invalid.com')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://inv-.alid-.com')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://inv-.-alid.com')
        self.assertEqual('http://valid-----hyphens.com/', f.clean('http://valid-----hyphens.com'))
        self.assertEqual('http://some.idn.xyz\xe4\xf6\xfc\xdfabc.domain.com:123/blah', f.clean('http://some.idn.xyzäöüßabc.domain.com:123/blah'))
        self.assertEqual('http://www.example.com/s/http://code.djangoproject.com/ticket/13804', f.clean('www.example.com/s/http://code.djangoproject.com/ticket/13804'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, '[a')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://[a')

    def test_url_regex_ticket11198(self):
        f = URLField()
        # hangs "forever" if catastrophic backtracking in ticket:#11198 not fixed
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://%s' % ("X"*200,))

        # a second test, to make sure the problem is really addressed, even on
        # domains that don't fail the domain label length check in the regex
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://%s' % ("X"*60,))

    def test_urlfield_2(self):
        f = URLField(required=False)
        self.assertEqual('', f.clean(''))
        self.assertEqual('', f.clean(None))
        self.assertEqual('http://example.com/', f.clean('http://example.com'))
        self.assertEqual('http://www.example.com/', f.clean('http://www.example.com'))
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'foo')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://example')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://example.')
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 'http://.com')

    def test_urlfield_5(self):
        f = URLField(min_length=15, max_length=20)
        self.assertWidgetRendersTo(f, '<input id="id_f" type="url" name="f" maxlength="20" />')
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at least 15 characters (it has 13).'", f.clean, 'http://f.com')
        self.assertEqual('http://example.com/', f.clean('http://example.com'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 20 characters (it has 38).'", f.clean, 'http://abcdefghijklmnopqrstuvwxyz.com')

    def test_urlfield_6(self):
        f = URLField(required=False)
        self.assertEqual('http://example.com/', f.clean('example.com'))
        self.assertEqual('', f.clean(''))
        self.assertEqual('https://example.com/', f.clean('https://example.com'))

    def test_urlfield_7(self):
        f = URLField()
        self.assertEqual('http://example.com/', f.clean('http://example.com'))
        self.assertEqual('http://example.com/test', f.clean('http://example.com/test'))

    def test_urlfield_8(self):
        # ticket #11826
        f = URLField()
        self.assertEqual('http://example.com/?some_param=some_value', f.clean('http://example.com?some_param=some_value'))

    def test_urlfield_9(self):
        f = URLField()
        urls = (
            'http://עברית.idn.icann.org/',
            'http://sãopaulo.com/',
            'http://sãopaulo.com.br/',
            'http://пример.испытание/',
            'http://مثال.إختبار/',
            'http://例子.测试/',
            'http://例子.測試/',
            'http://उदाहरण.परीक्षा/',
            'http://例え.テスト/',
            'http://مثال.آزمایشی/',
            'http://실례.테스트/',
            'http://العربية.idn.icann.org/',
        )
        for url in urls:
            # Valid IDN
            self.assertEqual(url, f.clean(url))

    def test_urlfield_10(self):
        """Test URLField correctly validates IPv6 (#18779)."""
        f = URLField()
        urls = (
            'http://::/',
            'http://6:21b4:92/',
            'http://[12:34:3a53]/',
            'http://[a34:9238::]:8080/',
        )
        for url in urls:
            self.assertEqual(url, f.clean(url))

    def test_urlfield_not_string(self):
        f = URLField(required=False)
        self.assertRaisesMessage(ValidationError, "'Enter a valid URL.'", f.clean, 23)

    # BooleanField ################################################################

    def test_booleanfield_1(self):
        f = BooleanField()
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual(True, f.clean(True))
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, False)
        self.assertEqual(True, f.clean(1))
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, 0)
        self.assertEqual(True, f.clean('Django rocks'))
        self.assertEqual(True, f.clean('True'))
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, 'False')

    def test_booleanfield_2(self):
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
        self.assertEqual(False, f.clean('false'))
        self.assertEqual(False, f.clean('FaLsE'))

    def test_boolean_picklable(self):
        self.assertIsInstance(pickle.loads(pickle.dumps(BooleanField())), BooleanField)

    def test_booleanfield_changed(self):
        f = BooleanField()
        self.assertFalse(f._has_changed(None, None))
        self.assertFalse(f._has_changed(None, ''))
        self.assertFalse(f._has_changed('', None))
        self.assertFalse(f._has_changed('', ''))
        self.assertTrue(f._has_changed(False, 'on'))
        self.assertFalse(f._has_changed(True, 'on'))
        self.assertTrue(f._has_changed(True, ''))
        # Initial value may have mutated to a string due to show_hidden_initial (#19537)
        self.assertTrue(f._has_changed('False', 'on'))

    # ChoiceField #################################################################

    def test_choicefield_1(self):
        f = ChoiceField(choices=[('1', 'One'), ('2', 'Two')])
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual('1', f.clean(1))
        self.assertEqual('1', f.clean('1'))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 3 is not one of the available choices.'", f.clean, '3')

    def test_choicefield_2(self):
        f = ChoiceField(choices=[('1', 'One'), ('2', 'Two')], required=False)
        self.assertEqual('', f.clean(''))
        self.assertEqual('', f.clean(None))
        self.assertEqual('1', f.clean(1))
        self.assertEqual('1', f.clean('1'))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 3 is not one of the available choices.'", f.clean, '3')

    def test_choicefield_3(self):
        f = ChoiceField(choices=[('J', 'John'), ('P', 'Paul')])
        self.assertEqual('J', f.clean('J'))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. John is not one of the available choices.'", f.clean, 'John')

    def test_choicefield_4(self):
        f = ChoiceField(choices=[('Numbers', (('1', 'One'), ('2', 'Two'))), ('Letters', (('3','A'),('4','B'))), ('5','Other')])
        self.assertEqual('1', f.clean(1))
        self.assertEqual('1', f.clean('1'))
        self.assertEqual('3', f.clean(3))
        self.assertEqual('3', f.clean('3'))
        self.assertEqual('5', f.clean(5))
        self.assertEqual('5', f.clean('5'))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 6 is not one of the available choices.'", f.clean, '6')

    # TypedChoiceField ############################################################
    # TypedChoiceField is just like ChoiceField, except that coerced types will
    # be returned:

    def test_typedchoicefield_1(self):
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int)
        self.assertEqual(1, f.clean('1'))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 2 is not one of the available choices.'", f.clean, '2')

    def test_typedchoicefield_2(self):
        # Different coercion, same validation.
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=float)
        self.assertEqual(1.0, f.clean('1'))

    def test_typedchoicefield_3(self):
        # This can also cause weirdness: be careful (bool(-1) == True, remember)
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=bool)
        self.assertEqual(True, f.clean('-1'))

    def test_typedchoicefield_4(self):
        # Even more weirdness: if you have a valid choice but your coercion function
        # can't coerce, yo'll still get a validation error. Don't do this!
        f = TypedChoiceField(choices=[('A', 'A'), ('B', 'B')], coerce=int)
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. B is not one of the available choices.'", f.clean, 'B')
        # Required fields require values
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')

    def test_typedchoicefield_5(self):
        # Non-required fields aren't required
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False)
        self.assertEqual('', f.clean(''))
        # If you want cleaning an empty value to return a different type, tell the field

    def test_typedchoicefield_6(self):
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False, empty_value=None)
        self.assertEqual(None, f.clean(''))

    def test_typedchoicefield_has_changed(self):
        # has_changed should not trigger required validation
        f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=True)
        self.assertFalse(f._has_changed(None, ''))

    # NullBooleanField ############################################################

    def test_nullbooleanfield_1(self):
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


    def test_nullbooleanfield_2(self):
        # Make sure that the internal value is preserved if using HiddenInput (#7753)
        class HiddenNullBooleanForm(Form):
            hidden_nullbool1 = NullBooleanField(widget=HiddenInput, initial=True)
            hidden_nullbool2 = NullBooleanField(widget=HiddenInput, initial=False)
        f = HiddenNullBooleanForm()
        self.assertHTMLEqual('<input type="hidden" name="hidden_nullbool1" value="True" id="id_hidden_nullbool1" /><input type="hidden" name="hidden_nullbool2" value="False" id="id_hidden_nullbool2" />', str(f))

    def test_nullbooleanfield_3(self):
        class HiddenNullBooleanForm(Form):
            hidden_nullbool1 = NullBooleanField(widget=HiddenInput, initial=True)
            hidden_nullbool2 = NullBooleanField(widget=HiddenInput, initial=False)
        f = HiddenNullBooleanForm({ 'hidden_nullbool1': 'True', 'hidden_nullbool2': 'False' })
        self.assertEqual(None, f.full_clean())
        self.assertEqual(True, f.cleaned_data['hidden_nullbool1'])
        self.assertEqual(False, f.cleaned_data['hidden_nullbool2'])

    def test_nullbooleanfield_4(self):
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

    def test_nullbooleanfield_changed(self):
        f = NullBooleanField()
        self.assertTrue(f._has_changed(False, None))
        self.assertTrue(f._has_changed(None, False))
        self.assertFalse(f._has_changed(None, None))
        self.assertFalse(f._has_changed(False, False))
        self.assertTrue(f._has_changed(True, False))
        self.assertTrue(f._has_changed(True, None))
        self.assertTrue(f._has_changed(True, False))

    # MultipleChoiceField #########################################################

    def test_multiplechoicefield_1(self):
        f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two')])
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertEqual(['1'], f.clean([1]))
        self.assertEqual(['1'], f.clean(['1']))
        self.assertEqual(['1', '2'], f.clean(['1', '2']))
        self.assertEqual(['1', '2'], f.clean([1, '2']))
        self.assertEqual(['1', '2'], f.clean((1, '2')))
        self.assertRaisesMessage(ValidationError, "'Enter a list of values.'", f.clean, 'hello')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, [])
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, ())
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 3 is not one of the available choices.'", f.clean, ['3'])

    def test_multiplechoicefield_2(self):
        f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two')], required=False)
        self.assertEqual([], f.clean(''))
        self.assertEqual([], f.clean(None))
        self.assertEqual(['1'], f.clean([1]))
        self.assertEqual(['1'], f.clean(['1']))
        self.assertEqual(['1', '2'], f.clean(['1', '2']))
        self.assertEqual(['1', '2'], f.clean([1, '2']))
        self.assertEqual(['1', '2'], f.clean((1, '2')))
        self.assertRaisesMessage(ValidationError, "'Enter a list of values.'", f.clean, 'hello')
        self.assertEqual([], f.clean([]))
        self.assertEqual([], f.clean(()))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 3 is not one of the available choices.'", f.clean, ['3'])

    def test_multiplechoicefield_3(self):
        f = MultipleChoiceField(choices=[('Numbers', (('1', 'One'), ('2', 'Two'))), ('Letters', (('3','A'),('4','B'))), ('5','Other')])
        self.assertEqual(['1'], f.clean([1]))
        self.assertEqual(['1'], f.clean(['1']))
        self.assertEqual(['1', '5'], f.clean([1, 5]))
        self.assertEqual(['1', '5'], f.clean([1, '5']))
        self.assertEqual(['1', '5'], f.clean(['1', 5]))
        self.assertEqual(['1', '5'], f.clean(['1', '5']))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 6 is not one of the available choices.'", f.clean, ['6'])
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 6 is not one of the available choices.'", f.clean, ['1','6'])

    def test_multiplechoicefield_changed(self):
        f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two'), ('3', 'Three')])
        self.assertFalse(f._has_changed(None, None))
        self.assertFalse(f._has_changed([], None))
        self.assertTrue(f._has_changed(None, ['1']))
        self.assertFalse(f._has_changed([1, 2], ['1', '2']))
        self.assertFalse(f._has_changed([2, 1], ['1', '2']))
        self.assertTrue(f._has_changed([1, 2], ['1']))
        self.assertTrue(f._has_changed([1, 2], ['1', '3']))

    # TypedMultipleChoiceField ############################################################
    # TypedMultipleChoiceField is just like MultipleChoiceField, except that coerced types
    # will be returned:

    def test_typedmultiplechoicefield_1(self):
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int)
        self.assertEqual([1], f.clean(['1']))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 2 is not one of the available choices.'", f.clean, ['2'])

    def test_typedmultiplechoicefield_2(self):
        # Different coercion, same validation.
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=float)
        self.assertEqual([1.0], f.clean(['1']))

    def test_typedmultiplechoicefield_3(self):
        # This can also cause weirdness: be careful (bool(-1) == True, remember)
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=bool)
        self.assertEqual([True], f.clean(['-1']))

    def test_typedmultiplechoicefield_4(self):
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int)
        self.assertEqual([1, -1], f.clean(['1','-1']))
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. 2 is not one of the available choices.'", f.clean, ['1','2'])

    def test_typedmultiplechoicefield_5(self):
        # Even more weirdness: if you have a valid choice but your coercion function
        # can't coerce, you'll still get a validation error. Don't do this!
        f = TypedMultipleChoiceField(choices=[('A', 'A'), ('B', 'B')], coerce=int)
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. B is not one of the available choices.'", f.clean, ['B'])
        # Required fields require values
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, [])

    def test_typedmultiplechoicefield_6(self):
        # Non-required fields aren't required
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False)
        self.assertEqual([], f.clean([]))

    def test_typedmultiplechoicefield_7(self):
        # If you want cleaning an empty value to return a different type, tell the field
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False, empty_value=None)
        self.assertEqual(None, f.clean([]))

    def test_typedmultiplechoicefield_has_changed(self):
        # has_changed should not trigger required validation
        f = TypedMultipleChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=True)
        self.assertFalse(f._has_changed(None, ''))

   # ComboField ##################################################################

    def test_combofield_1(self):
        f = ComboField(fields=[CharField(max_length=20), EmailField()])
        self.assertEqual('test@example.com', f.clean('test@example.com'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 20 characters (it has 28).'", f.clean, 'longemailaddress@example.com')
        self.assertRaisesMessage(ValidationError, "'Enter a valid email address.'", f.clean, 'not an email')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)

    def test_combofield_2(self):
        f = ComboField(fields=[CharField(max_length=20), EmailField()], required=False)
        self.assertEqual('test@example.com', f.clean('test@example.com'))
        self.assertRaisesMessage(ValidationError, "'Ensure this value has at most 20 characters (it has 28).'", f.clean, 'longemailaddress@example.com')
        self.assertRaisesMessage(ValidationError, "'Enter a valid email address.'", f.clean, 'not an email')
        self.assertEqual('', f.clean(''))
        self.assertEqual('', f.clean(None))

    # FilePathField ###############################################################

    def test_filepathfield_1(self):
        path = os.path.abspath(upath(forms.__file__))
        path = os.path.dirname(path) + '/'
        self.assertTrue(fix_os_paths(path).endswith('/django/forms/'))

    def test_filepathfield_2(self):
        path = upath(forms.__file__)
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
        self.assertRaisesMessage(ValidationError, "'Select a valid choice. fields.py is not one of the available choices.'", f.clean, 'fields.py')
        assert fix_os_paths(f.clean(path + 'fields.py')).endswith('/django/forms/fields.py')

    def test_filepathfield_3(self):
        path = upath(forms.__file__)
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

    def test_filepathfield_4(self):
        path = os.path.abspath(upath(forms.__file__))
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

    def test_filepathfield_folders(self):
        path = os.path.dirname(upath(__file__)) + '/filepath_test_files/'
        f = FilePathField(path=path, allow_folders=True, allow_files=False)
        f.choices.sort()
        expected = [
            ('/tests/forms_tests/tests/filepath_test_files/directory', 'directory'),
        ]
        for exp, got in zip(expected, fix_os_paths(f.choices)):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))

        f = FilePathField(path=path, allow_folders=True, allow_files=True)
        f.choices.sort()
        expected = [
            ('/tests/forms_tests/tests/filepath_test_files/.dot-file', '.dot-file'),
            ('/tests/forms_tests/tests/filepath_test_files/directory', 'directory'),
            ('/tests/forms_tests/tests/filepath_test_files/fake-image.jpg', 'fake-image.jpg'),
            ('/tests/forms_tests/tests/filepath_test_files/real-text-file.txt', 'real-text-file.txt'),
        ]

        actual = fix_os_paths(f.choices)
        self.assertEqual(len(expected), len(actual))
        for exp, got in zip(expected, actual):
            self.assertEqual(exp[1], got[1])
            self.assertTrue(got[0].endswith(exp[0]))


    # SplitDateTimeField ##########################################################

    def test_splitdatetimefield_1(self):
        from django.forms.widgets import SplitDateTimeWidget
        f = SplitDateTimeField()
        assert isinstance(f.widget, SplitDateTimeWidget)
        self.assertEqual(datetime.datetime(2006, 1, 10, 7, 30), f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)]))
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, None)
        self.assertRaisesMessage(ValidationError, "'This field is required.'", f.clean, '')
        self.assertRaisesMessage(ValidationError, "'Enter a list of values.'", f.clean, 'hello')
        six.assertRaisesRegex(self, ValidationError, "'Enter a valid date\.', u?'Enter a valid time\.'", f.clean, ['hello', 'there'])
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, ['2006-01-10', 'there'])
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, ['hello', '07:30'])

    def test_splitdatetimefield_2(self):
        f = SplitDateTimeField(required=False)
        self.assertEqual(datetime.datetime(2006, 1, 10, 7, 30), f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)]))
        self.assertEqual(datetime.datetime(2006, 1, 10, 7, 30), f.clean(['2006-01-10', '07:30']))
        self.assertEqual(None, f.clean(None))
        self.assertEqual(None, f.clean(''))
        self.assertEqual(None, f.clean(['']))
        self.assertEqual(None, f.clean(['', '']))
        self.assertRaisesMessage(ValidationError, "'Enter a list of values.'", f.clean, 'hello')
        six.assertRaisesRegex(self, ValidationError, "'Enter a valid date\.', u?'Enter a valid time\.'", f.clean, ['hello', 'there'])
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, ['2006-01-10', 'there'])
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, ['hello', '07:30'])
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, ['2006-01-10', ''])
        self.assertRaisesMessage(ValidationError, "'Enter a valid time.'", f.clean, ['2006-01-10'])
        self.assertRaisesMessage(ValidationError, "'Enter a valid date.'", f.clean, ['', '07:30'])

    def test_splitdatetimefield_changed(self):
        f = SplitDateTimeField(input_date_formats=['%d/%m/%Y'])
        self.assertFalse(f._has_changed(['11/01/2012', '09:18:15'], ['11/01/2012', '09:18:15']))
        self.assertTrue(f._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), ['2008-05-06', '12:40:00']))
        self.assertFalse(f._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), ['06/05/2008', '12:40']))
        self.assertTrue(f._has_changed(datetime.datetime(2008, 5, 6, 12, 40, 00), ['06/05/2008', '12:41']))
