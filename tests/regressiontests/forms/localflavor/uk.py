# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ UK form fields.

tests = r"""
# UKPostcodeField #############################################################

UKPostcodeField validates that the data is a valid UK postcode.
>>> from django.contrib.localflavor.uk.forms import UKPostcodeField
>>> f = UKPostcodeField()
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('BT324PX')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = UKPostcodeField(required=False)
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean('BT324PX')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postcode. A space is required between the two postcode parts.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
"""
