# -*- coding: utf-8 -*-
tests = r"""
>>> from django.forms import *
>>> from django.forms.widgets import RadioFieldRenderer
>>> from django.core.files.uploadedfile import SimpleUploadedFile
>>> import datetime
>>> import time
>>> import re
>>> try:
...     from decimal import Decimal
... except ImportError:
...     from django.utils._decimal import Decimal


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

# CharField ###################################################################

>>> f = CharField()
>>> f.clean(1)
u'1'
>>> f.clean('hello')
u'hello'
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean([1, 2, 3])
u'[1, 2, 3]'

>>> f = CharField(required=False)
>>> f.clean(1)
u'1'
>>> f.clean('hello')
u'hello'
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean([1, 2, 3])
u'[1, 2, 3]'

CharField accepts an optional max_length parameter:
>>> f = CharField(max_length=10, required=False)
>>> f.clean('12345')
u'12345'
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('1234567890a')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 10 characters (it has 11).']

CharField accepts an optional min_length parameter:
>>> f = CharField(min_length=10, required=False)
>>> f.clean('')
u''
>>> f.clean('12345')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters (it has 5).']
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('1234567890a')
u'1234567890a'

>>> f = CharField(min_length=10, required=True)
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('12345')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters (it has 5).']
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('1234567890a')
u'1234567890a'

# IntegerField ################################################################

>>> f = IntegerField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('1')
1
>>> isinstance(f.clean('1'), int)
True
>>> f.clean('23')
23
>>> f.clean('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']
>>> f.clean(42)
42
>>> f.clean(3.14)
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']
>>> f.clean('1 ')
1
>>> f.clean(' 1')
1
>>> f.clean(' 1 ')
1
>>> f.clean('1a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']

>>> f = IntegerField(required=False)
>>> f.clean('')
>>> repr(f.clean(''))
'None'
>>> f.clean(None)
>>> repr(f.clean(None))
'None'
>>> f.clean('1')
1
>>> isinstance(f.clean('1'), int)
True
>>> f.clean('23')
23
>>> f.clean('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']
>>> f.clean('1 ')
1
>>> f.clean(' 1')
1
>>> f.clean(' 1 ')
1
>>> f.clean('1a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a whole number.']

IntegerField accepts an optional max_value parameter:
>>> f = IntegerField(max_value=10)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
1
>>> f.clean(10)
10
>>> f.clean(11)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 10.']
>>> f.clean('10')
10
>>> f.clean('11')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 10.']

IntegerField accepts an optional min_value parameter:
>>> f = IntegerField(min_value=10)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is greater than or equal to 10.']
>>> f.clean(10)
10
>>> f.clean(11)
11
>>> f.clean('10')
10
>>> f.clean('11')
11

min_value and max_value can be used together:
>>> f = IntegerField(min_value=10, max_value=20)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is greater than or equal to 10.']
>>> f.clean(10)
10
>>> f.clean(11)
11
>>> f.clean('10')
10
>>> f.clean('11')
11
>>> f.clean(20)
20
>>> f.clean(21)
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 20.']

# FloatField ##################################################################

>>> f = FloatField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('1')
1.0
>>> isinstance(f.clean('1'), float)
True
>>> f.clean('23')
23.0
>>> f.clean('3.14')
3.1400000000000001
>>> f.clean(3.14)
3.1400000000000001
>>> f.clean(42)
42.0
>>> f.clean('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a number.']
>>> f.clean('1.0 ')
1.0
>>> f.clean(' 1.0')
1.0
>>> f.clean(' 1.0 ')
1.0
>>> f.clean('1.0a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a number.']

>>> f = FloatField(required=False)
>>> f.clean('')

>>> f.clean(None)

>>> f.clean('1')
1.0

FloatField accepts min_value and max_value just like IntegerField:
>>> f = FloatField(max_value=1.5, min_value=0.5)

>>> f.clean('1.6')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 1.5.']
>>> f.clean('0.4')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is greater than or equal to 0.5.']
>>> f.clean('1.5')
1.5
>>> f.clean('0.5')
0.5

# DecimalField ################################################################

>>> f = DecimalField(max_digits=4, decimal_places=2)
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('1') == Decimal("1")
True
>>> isinstance(f.clean('1'), Decimal)
True
>>> f.clean('23') == Decimal("23")
True
>>> f.clean('3.14') == Decimal("3.14")
True
>>> f.clean(3.14) == Decimal("3.14")
True
>>> f.clean(Decimal('3.14')) == Decimal("3.14")
True
>>> f.clean('a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a number.']
>>> f.clean(u'łąść')
Traceback (most recent call last):
...
ValidationError: [u'Enter a number.']
>>> f.clean('1.0 ') == Decimal("1.0")
True
>>> f.clean(' 1.0') == Decimal("1.0")
True
>>> f.clean(' 1.0 ') == Decimal("1.0")
True
>>> f.clean('1.0a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a number.']
>>> f.clean('123.45')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 4 digits in total.']
>>> f.clean('1.234')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 2 decimal places.']
>>> f.clean('123.4')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 2 digits before the decimal point.']
>>> f.clean('-12.34') == Decimal("-12.34")
True
>>> f.clean('-123.45')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 4 digits in total.']
>>> f.clean('-.12') == Decimal("-0.12")
True
>>> f.clean('-00.12') == Decimal("-0.12")
True
>>> f.clean('-000.12') == Decimal("-0.12")
True
>>> f.clean('-000.123')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 2 decimal places.']
>>> f.clean('-000.1234')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 4 digits in total.']
>>> f.clean('--0.12')
Traceback (most recent call last):
...
ValidationError: [u'Enter a number.']

>>> f = DecimalField(max_digits=4, decimal_places=2, required=False)
>>> f.clean('')

>>> f.clean(None)

>>> f.clean('1') == Decimal("1")
True

DecimalField accepts min_value and max_value just like IntegerField:
>>> f = DecimalField(max_digits=4, decimal_places=2, max_value=Decimal('1.5'), min_value=Decimal('0.5'))

>>> f.clean('1.6')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is less than or equal to 1.5.']
>>> f.clean('0.4')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value is greater than or equal to 0.5.']
>>> f.clean('1.5') == Decimal("1.5")
True
>>> f.clean('0.5') == Decimal("0.5")
True
>>> f.clean('.5') == Decimal("0.5")
True
>>> f.clean('00.50') == Decimal("0.50")
True


>>> f = DecimalField(decimal_places=2)
>>> f.clean('0.00000001')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 2 decimal places.']


>>> f = DecimalField(max_digits=3)

# Leading whole zeros "collapse" to one digit.
>>> f.clean('0000000.10') == Decimal("0.1")
True
>>> f.clean('0000000.100')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 3 digits in total.']

# Only leading whole zeros "collapse" to one digit.
>>> f.clean('000000.02') == Decimal('0.02')
True
>>> f.clean('000000.002')
Traceback (most recent call last):
...
ValidationError: [u'Ensure that there are no more than 3 digits in total.']


# DateField ###################################################################

>>> import datetime
>>> f = DateField()
>>> f.clean(datetime.date(2006, 10, 25))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.date(2006, 10, 25)
>>> f.clean('2006-10-25')
datetime.date(2006, 10, 25)
>>> f.clean('10/25/2006')
datetime.date(2006, 10, 25)
>>> f.clean('10/25/06')
datetime.date(2006, 10, 25)
>>> f.clean('Oct 25 2006')
datetime.date(2006, 10, 25)
>>> f.clean('October 25 2006')
datetime.date(2006, 10, 25)
>>> f.clean('October 25, 2006')
datetime.date(2006, 10, 25)
>>> f.clean('25 October 2006')
datetime.date(2006, 10, 25)
>>> f.clean('25 October, 2006')
datetime.date(2006, 10, 25)
>>> f.clean('2006-4-31')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('200a-10-25')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('25/10/06')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = DateField(required=False)
>>> f.clean(None)
>>> repr(f.clean(None))
'None'
>>> f.clean('')
>>> repr(f.clean(''))
'None'

DateField accepts an optional input_formats parameter:
>>> f = DateField(input_formats=['%Y %m %d'])
>>> f.clean(datetime.date(2006, 10, 25))
datetime.date(2006, 10, 25)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.date(2006, 10, 25)
>>> f.clean('2006 10 25')
datetime.date(2006, 10, 25)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.clean('2006-10-25')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('10/25/2006')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean('10/25/06')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']

# TimeField ###################################################################

>>> import datetime
>>> f = TimeField()
>>> f.clean(datetime.time(14, 25))
datetime.time(14, 25)
>>> f.clean(datetime.time(14, 25, 59))
datetime.time(14, 25, 59)
>>> f.clean('14:25')
datetime.time(14, 25)
>>> f.clean('14:25:59')
datetime.time(14, 25, 59)
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean('1:24 p.m.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']

TimeField accepts an optional input_formats parameter:
>>> f = TimeField(input_formats=['%I:%M %p'])
>>> f.clean(datetime.time(14, 25))
datetime.time(14, 25)
>>> f.clean(datetime.time(14, 25, 59))
datetime.time(14, 25, 59)
>>> f.clean('4:25 AM')
datetime.time(4, 25)
>>> f.clean('4:25 PM')
datetime.time(16, 25)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.clean('14:30:45')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']

# DateTimeField ###############################################################

>>> import datetime
>>> f = DateTimeField()
>>> f.clean(datetime.date(2006, 10, 25))
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.datetime(2006, 10, 25, 14, 30, 59)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
>>> f.clean('2006-10-25 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.clean('2006-10-25 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('2006-10-25 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('2006-10-25')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean('10/25/2006 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.clean('10/25/2006 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/2006 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/2006')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean('10/25/06 14:30:45')
datetime.datetime(2006, 10, 25, 14, 30, 45)
>>> f.clean('10/25/06 14:30:00')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/06 14:30')
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean('10/25/06')
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']
>>> f.clean('2006-10-25 4:30 p.m.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']

DateField accepts an optional input_formats parameter:
>>> f = DateTimeField(input_formats=['%Y %m %d %I:%M %p'])
>>> f.clean(datetime.date(2006, 10, 25))
datetime.datetime(2006, 10, 25, 0, 0)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30))
datetime.datetime(2006, 10, 25, 14, 30)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59))
datetime.datetime(2006, 10, 25, 14, 30, 59)
>>> f.clean(datetime.datetime(2006, 10, 25, 14, 30, 59, 200))
datetime.datetime(2006, 10, 25, 14, 30, 59, 200)
>>> f.clean('2006 10 25 2:30 PM')
datetime.datetime(2006, 10, 25, 14, 30)

The input_formats parameter overrides all default input formats,
so the default formats won't work unless you specify them:
>>> f.clean('2006-10-25 14:30:45')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date/time.']

>>> f = DateTimeField(required=False)
>>> f.clean(None)
>>> repr(f.clean(None))
'None'
>>> f.clean('')
>>> repr(f.clean(''))
'None'

# RegexField ##################################################################

>>> f = RegexField('^\d[A-F]\d$')
>>> f.clean('2A2')
u'2A2'
>>> f.clean('3F3')
u'3F3'
>>> f.clean('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 2A2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('2A2 ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = RegexField('^\d[A-F]\d$', required=False)
>>> f.clean('2A2')
u'2A2'
>>> f.clean('3F3')
u'3F3'
>>> f.clean('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('')
u''

Alternatively, RegexField can take a compiled regular expression:
>>> f = RegexField(re.compile('^\d[A-F]\d$'))
>>> f.clean('2A2')
u'2A2'
>>> f.clean('3F3')
u'3F3'
>>> f.clean('3G3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean(' 2A2')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']
>>> f.clean('2A2 ')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

RegexField takes an optional error_message argument:
>>> f = RegexField('^\d\d\d\d$', error_message='Enter a four-digit number.')
>>> f.clean('1234')
u'1234'
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Enter a four-digit number.']
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a four-digit number.']

RegexField also access min_length and max_length parameters, for convenience.
>>> f = RegexField('^\d+$', min_length=5, max_length=10)
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 5 characters (it has 3).']
>>> f.clean('abc')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 5 characters (it has 3).']
>>> f.clean('12345')
u'12345'
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('12345678901')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 10 characters (it has 11).']
>>> f.clean('12345a')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid value.']

# EmailField ##################################################################

>>> f = EmailField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('person@example.com')
u'person@example.com'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@bar')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']

>>> f = EmailField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean('person@example.com')
u'person@example.com'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('foo@bar')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']

EmailField also access min_length and max_length parameters, for convenience.
>>> f = EmailField(min_length=10, max_length=15)
>>> f.clean('a@foo.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 10 characters (it has 9).']
>>> f.clean('alf@foo.com')
u'alf@foo.com'
>>> f.clean('alf123456788@foo.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 15 characters (it has 20).']

# FileField ##################################################################

>>> f = FileField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean('', '')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean('', 'files/test1.pdf')
'files/test1.pdf'

>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None, '')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None, 'files/test2.pdf')
'files/test2.pdf'

>>> f.clean(SimpleUploadedFile('', ''))
Traceback (most recent call last):
...
ValidationError: [u'No file was submitted. Check the encoding type on the form.']

>>> f.clean(SimpleUploadedFile('', ''), '')
Traceback (most recent call last):
...
ValidationError: [u'No file was submitted. Check the encoding type on the form.']

>>> f.clean(None, 'files/test3.pdf')
'files/test3.pdf'

>>> f.clean('some content that is not a file')
Traceback (most recent call last):
...
ValidationError: [u'No file was submitted. Check the encoding type on the form.']

>>> f.clean(SimpleUploadedFile('name', None))
Traceback (most recent call last):
...
ValidationError: [u'The submitted file is empty.']

>>> f.clean(SimpleUploadedFile('name', ''))
Traceback (most recent call last):
...
ValidationError: [u'The submitted file is empty.']

>>> type(f.clean(SimpleUploadedFile('name', 'Some File Content')))
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>

>>> type(f.clean(SimpleUploadedFile('我隻氣墊船裝滿晒鱔.txt', 'मेरी मँडराने वाली नाव सर्पमीनों से भरी ह')))
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>

>>> type(f.clean(SimpleUploadedFile('name', 'Some File Content'), 'files/test4.pdf'))
<class 'django.core.files.uploadedfile.SimpleUploadedFile'>

# URLField ##################################################################

>>> f = URLField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('http://localhost')
u'http://localhost/'
>>> f.clean('http://example.com')
u'http://example.com/'
>>> f.clean('http://www.example.com')
u'http://www.example.com/'
>>> f.clean('http://www.example.com:8000/test')
u'http://www.example.com:8000/test'
>>> f.clean('http://200.8.9.10')
u'http://200.8.9.10/'
>>> f.clean('http://200.8.9.10:8000/test')
u'http://200.8.9.10:8000/test'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']

>>> f = URLField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean('http://example.com')
u'http://example.com/'
>>> f.clean('http://www.example.com')
u'http://www.example.com/'
>>> f.clean('foo')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://example.')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://.com')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']

URLField takes an optional verify_exists parameter, which is False by default.
This verifies that the URL is live on the Internet and doesn't return a 404 or 500:
>>> f = URLField(verify_exists=True)
>>> f.clean('http://www.google.com') # This will fail if there's no Internet connection
u'http://www.google.com/'
>>> f.clean('http://example')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid URL.']
>>> f.clean('http://www.broken.djangoproject.com') # bad domain
Traceback (most recent call last):
...
ValidationError: [u'This URL appears to be a broken link.']
>>> f.clean('http://google.com/we-love-microsoft.html') # good domain, bad page
Traceback (most recent call last):
...
ValidationError: [u'This URL appears to be a broken link.']
>>> f = URLField(verify_exists=True, required=False)
>>> f.clean('')
u''
>>> f.clean('http://www.google.com') # This will fail if there's no Internet connection
u'http://www.google.com/'

URLField also access min_length and max_length parameters, for convenience.
>>> f = URLField(min_length=15, max_length=20)
>>> f.clean('http://f.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at least 15 characters (it has 13).']
>>> f.clean('http://example.com')
u'http://example.com/'
>>> f.clean('http://abcdefghijklmnopqrstuvwxyz.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 20 characters (it has 38).']

URLField should prepend 'http://' if no scheme was given
>>> f = URLField(required=False)
>>> f.clean('example.com')
u'http://example.com/'
>>> f.clean('')
u''
>>> f.clean('https://example.com')
u'https://example.com/'

URLField should append '/' if no path was given
>>> f = URLField()
>>> f.clean('http://example.com')
u'http://example.com/'

URLField shouldn't change the path if it was given
>>> f.clean('http://example.com/test')
u'http://example.com/test'

# BooleanField ################################################################

>>> f = BooleanField()
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(True)
True
>>> f.clean(False)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
True
>>> f.clean(0)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('Django rocks')
True

>>> f.clean('True')
True
>>> f.clean('False')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = BooleanField(required=False)
>>> f.clean('')
False
>>> f.clean(None)
False
>>> f.clean(True)
True
>>> f.clean(False)
False
>>> f.clean(1)
True
>>> f.clean(0)
False
>>> f.clean('Django rocks')
True

A form's BooleanField with a hidden widget will output the string 'False', so
that should clean to the boolean value False:
>>> f.clean('False')
False

# ChoiceField #################################################################

>>> f = ChoiceField(choices=[('1', 'One'), ('2', 'Two')])
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(1)
u'1'
>>> f.clean('1')
u'1'
>>> f.clean('3')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

>>> f = ChoiceField(choices=[('1', 'One'), ('2', 'Two')], required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''
>>> f.clean(1)
u'1'
>>> f.clean('1')
u'1'
>>> f.clean('3')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

>>> f = ChoiceField(choices=[('J', 'John'), ('P', 'Paul')])
>>> f.clean('J')
u'J'
>>> f.clean('John')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. John is not one of the available choices.']

>>> f = ChoiceField(choices=[('Numbers', (('1', 'One'), ('2', 'Two'))), ('Letters', (('3','A'),('4','B'))), ('5','Other')])
>>> f.clean(1)
u'1'
>>> f.clean('1')
u'1'
>>> f.clean(3)
u'3'
>>> f.clean('3')
u'3'
>>> f.clean(5)
u'5'
>>> f.clean('5')
u'5'
>>> f.clean('6')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 6 is not one of the available choices.']

# TypedChoiceField ############################################################

# TypedChoiceField is just like ChoiceField, except that coerced types will 
# be returned:
>>> f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int)
>>> f.clean('1')
1
>>> f.clean('2')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 2 is not one of the available choices.']

# Different coercion, same validation.
>>> f.coerce = float
>>> f.clean('1')
1.0


# This can also cause weirdness: be careful (bool(-1) == True, remember)
>>> f.coerce = bool
>>> f.clean('-1') 
True

# Even more weirdness: if you have a valid choice but your coercion function
# can't coerce, you'll still get a validation error. Don't do this!
>>> f = TypedChoiceField(choices=[('A', 'A'), ('B', 'B')], coerce=int)
>>> f.clean('B')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. B is not one of the available choices.']

# Required fields require values
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

# Non-required fields aren't required
>>> f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False)
>>> f.clean('')
''

# If you want cleaning an empty value to return a different type, tell the field
>>> f = TypedChoiceField(choices=[(1, "+1"), (-1, "-1")], coerce=int, required=False, empty_value=None)
>>> print f.clean('')
None

# NullBooleanField ############################################################

>>> f = NullBooleanField()
>>> f.clean('')
>>> f.clean(True)
True
>>> f.clean(False)
False
>>> f.clean(None)
>>> f.clean('1')
>>> f.clean('2')
>>> f.clean('3')
>>> f.clean('hello')

# Make sure that the internal value is preserved if using HiddenInput (#7753)
>>> class HiddenNullBooleanForm(Form):
...     hidden_nullbool1 = NullBooleanField(widget=HiddenInput, initial=True)
...     hidden_nullbool2 = NullBooleanField(widget=HiddenInput, initial=False)
>>> f = HiddenNullBooleanForm()
>>> print f
<input type="hidden" name="hidden_nullbool1" value="True" id="id_hidden_nullbool1" /><input type="hidden" name="hidden_nullbool2" value="False" id="id_hidden_nullbool2" />
>>> f = HiddenNullBooleanForm({ 'hidden_nullbool1': 'True', 'hidden_nullbool2': 'False' })
>>> f.full_clean()
>>> f.cleaned_data['hidden_nullbool1']
True
>>> f.cleaned_data['hidden_nullbool2']
False

# MultipleChoiceField #########################################################

>>> f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two')])
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean([1])
[u'1']
>>> f.clean(['1'])
[u'1']
>>> f.clean(['1', '2'])
[u'1', u'2']
>>> f.clean([1, '2'])
[u'1', u'2']
>>> f.clean((1, '2'))
[u'1', u'2']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean([])
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(())
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(['3'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

>>> f = MultipleChoiceField(choices=[('1', 'One'), ('2', 'Two')], required=False)
>>> f.clean('')
[]
>>> f.clean(None)
[]
>>> f.clean([1])
[u'1']
>>> f.clean(['1'])
[u'1']
>>> f.clean(['1', '2'])
[u'1', u'2']
>>> f.clean([1, '2'])
[u'1', u'2']
>>> f.clean((1, '2'))
[u'1', u'2']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean([])
[]
>>> f.clean(())
[]
>>> f.clean(['3'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 3 is not one of the available choices.']

>>> f = MultipleChoiceField(choices=[('Numbers', (('1', 'One'), ('2', 'Two'))), ('Letters', (('3','A'),('4','B'))), ('5','Other')])
>>> f.clean([1])
[u'1']
>>> f.clean(['1'])
[u'1']
>>> f.clean([1, 5])
[u'1', u'5']
>>> f.clean([1, '5'])
[u'1', u'5']
>>> f.clean(['1', 5])
[u'1', u'5']
>>> f.clean(['1', '5'])
[u'1', u'5']
>>> f.clean(['6'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 6 is not one of the available choices.']
>>> f.clean(['1','6'])
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. 6 is not one of the available choices.']


# ComboField ##################################################################

ComboField takes a list of fields that should be used to validate a value,
in that order.
>>> f = ComboField(fields=[CharField(max_length=20), EmailField()])
>>> f.clean('test@example.com')
u'test@example.com'
>>> f.clean('longemailaddress@example.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 20 characters (it has 28).']
>>> f.clean('not an e-mail')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = ComboField(fields=[CharField(max_length=20), EmailField()], required=False)
>>> f.clean('test@example.com')
u'test@example.com'
>>> f.clean('longemailaddress@example.com')
Traceback (most recent call last):
...
ValidationError: [u'Ensure this value has at most 20 characters (it has 28).']
>>> f.clean('not an e-mail')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid e-mail address.']
>>> f.clean('')
u''
>>> f.clean(None)
u''

# FilePathField ###############################################################

>>> def fix_os_paths(x):
...     if isinstance(x, basestring):
...         return x.replace('\\', '/')
...     elif isinstance(x, tuple):
...         return tuple(fix_os_paths(list(x)))
...     elif isinstance(x, list):
...         return [fix_os_paths(y) for y in x]
...     else:
...         return x
...
>>> import os
>>> from django import forms
>>> path = forms.__file__
>>> path = os.path.dirname(path) + '/'
>>> fix_os_paths(path)
'.../django/forms/'
>>> f = forms.FilePathField(path=path)
>>> f.choices = [p for p in f.choices if p[0].endswith('.py')]
>>> f.choices.sort()
>>> fix_os_paths(f.choices)
[('.../django/forms/__init__.py', '__init__.py'), ('.../django/forms/fields.py', 'fields.py'), ('.../django/forms/forms.py', 'forms.py'), ('.../django/forms/models.py', 'models.py'), ('.../django/forms/util.py', 'util.py'), ('.../django/forms/widgets.py', 'widgets.py')]
>>> f.clean('fields.py')
Traceback (most recent call last):
...
ValidationError: [u'Select a valid choice. fields.py is not one of the available choices.']
>>> fix_os_paths(f.clean(path + 'fields.py'))
u'.../django/forms/fields.py'
>>> f = forms.FilePathField(path=path, match='^.*?\.py$')
>>> f.choices.sort()
>>> fix_os_paths(f.choices)
[('.../django/forms/__init__.py', '__init__.py'), ('.../django/forms/fields.py', 'fields.py'), ('.../django/forms/forms.py', 'forms.py'), ('.../django/forms/models.py', 'models.py'), ('.../django/forms/util.py', 'util.py'), ('.../django/forms/widgets.py', 'widgets.py')]
>>> f = forms.FilePathField(path=path, recursive=True, match='^.*?\.py$')
>>> f.choices.sort()
>>> fix_os_paths(f.choices)
[('.../django/forms/__init__.py', '__init__.py'), ('.../django/forms/extras/__init__.py', 'extras/__init__.py'), ('.../django/forms/extras/widgets.py', 'extras/widgets.py'), ('.../django/forms/fields.py', 'fields.py'), ('.../django/forms/forms.py', 'forms.py'), ('.../django/forms/models.py', 'models.py'), ('.../django/forms/util.py', 'util.py'), ('.../django/forms/widgets.py', 'widgets.py')]

# SplitDateTimeField ##########################################################

>>> f = SplitDateTimeField()
>>> f.widget
<django.forms.widgets.SplitDateTimeWidget object ...
>>> f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)])
datetime.datetime(2006, 1, 10, 7, 30)
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean(['hello', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.', u'Enter a valid time.']
>>> f.clean(['2006-01-10', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean(['hello', '07:30'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']

>>> f = SplitDateTimeField(required=False)
>>> f.clean([datetime.date(2006, 1, 10), datetime.time(7, 30)])
datetime.datetime(2006, 1, 10, 7, 30)
>>> f.clean(['2006-01-10', '07:30'])
datetime.datetime(2006, 1, 10, 7, 30)
>>> f.clean(None)
>>> f.clean('')
>>> f.clean([''])
>>> f.clean(['', ''])
>>> f.clean('hello')
Traceback (most recent call last):
...
ValidationError: [u'Enter a list of values.']
>>> f.clean(['hello', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.', u'Enter a valid time.']
>>> f.clean(['2006-01-10', 'there'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean(['hello', '07:30'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
>>> f.clean(['2006-01-10', ''])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean(['2006-01-10'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid time.']
>>> f.clean(['', '07:30'])
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid date.']
"""
