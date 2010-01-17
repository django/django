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
u'BT32 4PX'
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postcode.']
>>> f.clean('1NV4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postcode.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean(' so11aa ')
u'SO1 1AA'
>>> f.clean(' so1  1aa ')
u'SO1 1AA'
>>> f.clean('G2 3wt')
u'G2 3WT'
>>> f.clean('EC1A 1BB')
u'EC1A 1BB'
>>> f.clean('Ec1a1BB')
u'EC1A 1BB'
>>> f.clean(' b0gUS')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postcode.']
>>> f = UKPostcodeField(required=False)
>>> f.clean('BT32 4PX')
u'BT32 4PX'
>>> f.clean('GIR 0AA')
u'GIR 0AA'
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid postcode.']
>>> f.clean('BT324PX')
u'BT32 4PX'
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f = UKPostcodeField(error_messages={'invalid': 'Enter a bloody postcode!'})
>>> f.clean('1NV 4L1D')
Traceback (most recent call last):
...
ValidationError: [u'Enter a bloody postcode!']
"""
