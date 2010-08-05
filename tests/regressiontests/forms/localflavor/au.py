# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ AU form fields.

tests = r"""
## AUPostCodeField ##########################################################

A field that accepts a four digit Australian post code.

>>> from django.contrib.localflavor.au.forms import AUPostCodeField
>>> f = AUPostCodeField()
>>> f.clean('1234')
u'1234'
>>> f.clean('2000')
u'2000'
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean('20001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = AUPostCodeField(required=False)
>>> f.clean('1234')
u'1234'
>>> f.clean('2000')
u'2000'
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean('20001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a 4 digit post code.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

## AUPhoneNumberField ########################################################

A field that accepts a 10 digit Australian phone number.
Allows spaces and parentheses around area code.

>>> from django.contrib.localflavor.au.forms import AUPhoneNumberField
>>> f = AUPhoneNumberField()
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('0213456789')
u'0213456789'
>>> f.clean('02 13 45 67 89')
u'0213456789'
>>> f.clean('(02) 1345 6789')
u'0213456789'
>>> f.clean('(02) 1345-6789')
u'0213456789'
>>> f.clean('(02)1345-6789')
u'0213456789'
>>> f.clean('0408 123 456')
u'0408123456'
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean('1800DJANGO')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = AUPhoneNumberField(required=False)
>>> f.clean('1234567890')
u'1234567890'
>>> f.clean('0213456789')
u'0213456789'
>>> f.clean('02 13 45 67 89')
u'0213456789'
>>> f.clean('(02) 1345 6789')
u'0213456789'
>>> f.clean('(02) 1345-6789')
u'0213456789'
>>> f.clean('(02)1345-6789')
u'0213456789'
>>> f.clean('0408 123 456')
u'0408123456'
>>> f.clean('123')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean('1800DJANGO')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must contain 10 digits.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

## AUStateSelect #############################################################

AUStateSelect is a Select widget that uses a list of Australian
states/territories as its choices.

>>> from django.contrib.localflavor.au.forms import AUStateSelect
>>> f = AUStateSelect()
>>> print f.render('state', 'NSW')
<select name="state">
<option value="ACT">Australian Capital Territory</option>
<option value="NSW" selected="selected">New South Wales</option>
<option value="NT">Northern Territory</option>
<option value="QLD">Queensland</option>
<option value="SA">South Australia</option>
<option value="TAS">Tasmania</option>
<option value="VIC">Victoria</option>
<option value="WA">Western Australia</option>
</select>
"""
