# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ CZ Form Fields

tests = r"""
# CZPostalCodeField #########################################################

>>> from django.contrib.localflavor.cz.forms import CZPostalCodeField
>>> f = CZPostalCodeField()
>>> f.clean('84545x')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXX or XXX XX.']
>>> f.clean('91909')
u'91909'
>>> f.clean('917 01')
u'91701'
>>> f.clean('12345')
u'12345'
>>> f.clean('123456')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXX or XXX XX.']
>>> f.clean('1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXX or XXX XX.']
>>> f.clean('123 4')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXXXX or XXX XX.']

# CZRegionSelect ############################################################

>>> from django.contrib.localflavor.cz.forms import CZRegionSelect
>>> w = CZRegionSelect()
>>> w.render('regions', 'TT')
u'<select name="regions">\n<option value="PR">Prague</option>\n<option value="CE">Central Bohemian Region</option>\n<option value="SO">South Bohemian Region</option>\n<option value="PI">Pilsen Region</option>\n<option value="CA">Carlsbad Region</option>\n<option value="US">Usti Region</option>\n<option value="LB">Liberec Region</option>\n<option value="HK">Hradec Region</option>\n<option value="PA">Pardubice Region</option>\n<option value="VY">Vysocina Region</option>\n<option value="SM">South Moravian Region</option>\n<option value="OL">Olomouc Region</option>\n<option value="ZL">Zlin Region</option>\n<option value="MS">Moravian-Silesian Region</option>\n</select>'

# CZBirthNumberField ########################################################

>>> from django.contrib.localflavor.cz.forms import CZBirthNumberField
>>> f = CZBirthNumberField()
>>> f.clean('880523/1237')
u'880523/1237'
>>> f.clean('8805231237')
u'8805231237'
>>> f.clean('880523/000')
u'880523/000'
>>> f.clean('880523000')
u'880523000'
>>> f.clean('882101/0011')
u'882101/0011'
>>> f.clean('880523/1237', 'm')
u'880523/1237'
>>> f.clean('885523/1231', 'f')
u'885523/1231'
>>> f.clean('123456/12')
Traceback (most recent call last):
...
ValidationError: [u'Enter a birth number in the format XXXXXX/XXXX or XXXXXXXXXX.']
>>> f.clean('123456/12345')
Traceback (most recent call last):
...
ValidationError: [u'Enter a birth number in the format XXXXXX/XXXX or XXXXXXXXXX.']
>>> f.clean('12345612')
Traceback (most recent call last):
...
ValidationError: [u'Enter a birth number in the format XXXXXX/XXXX or XXXXXXXXXX.']
>>> f.clean('12345612345')
Traceback (most recent call last):
...
ValidationError: [u'Enter a birth number in the format XXXXXX/XXXX or XXXXXXXXXX.']
>>> f.clean('881523/0000', 'm')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']
>>> f.clean('885223/0000', 'm')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']
>>> f.clean('881223/0000', 'f')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']
>>> f.clean('886523/0000', 'f')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']
>>> f.clean('880523/1239')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']
>>> f.clean('8805231239')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']
>>> f.clean('990101/0011')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid birth number.']

# CZICNumberField ########################################################

>>> from django.contrib.localflavor.cz.forms import CZICNumberField
>>> f = CZICNumberField()
>>> f.clean('12345679')
u'12345679'
>>> f.clean('12345601')
u'12345601'
>>> f.clean('12345661')
u'12345661'
>>> f.clean('12345610')
u'12345610'
>>> f.clean('1234567')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid IC number.']
>>> f.clean('12345660')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid IC number.']
>>> f.clean('12345600')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid IC number.']
"""
