# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ PT form fields.

tests = r"""
# PTZipCodeField #############################################################

PTZipCodeField validates that the data is a valid PT zipcode.
>>> from django.contrib.localflavor.pt.forms import PTZipCodeField
>>> f = PTZipCodeField()
>>> f.clean('3030-034')
u'3030-034'
>>> f.clean('1003456')
u'1003-456'
>>> f.clean('2A200')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX-XXX.']
>>> f.clean('980001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX-XXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = PTZipCodeField(required=False)
>>> f.clean('3030-034')
u'3030-034'
>>> f.clean('1003456')
u'1003-456'
>>> f.clean('2A200')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX-XXX.']
>>> f.clean('980001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXX-XXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# PTPhoneNumberField ##########################################################

PTPhoneNumberField validates that the data is a valid Portuguese phone number.
It's normalized to XXXXXXXXX format  or +X(X) for international numbers. Dots are valid too.
>>> from django.contrib.localflavor.pt.forms import PTPhoneNumberField
>>> f = PTPhoneNumberField()
>>> f.clean('917845189')
u'917845189'
>>> f.clean('91 784 5189')
u'917845189'
>>> f.clean('91 784 5189')
u'917845189'
>>> f.clean('+351 91 111')
u'+35191111'
>>> f.clean('00351873')
u'00351873'
>>> f.clean('91 784 51 8')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must have 9 digits, or start by + or 00.']
>>> f.clean('091 456 987 1')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must have 9 digits, or start by + or 00.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = PTPhoneNumberField(required=False)
>>> f.clean('917845189')
u'917845189'
>>> f.clean('91 784 5189')
u'917845189'
>>> f.clean('91 784 5189')
u'917845189'
>>> f.clean('+351 91 111')
u'+35191111'
>>> f.clean('00351873')
u'00351873'
>>> f.clean('91 784 51 8')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must have 9 digits, or start by + or 00.']
>>> f.clean('091 456 987 1')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must have 9 digits, or start by + or 00.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

"""
