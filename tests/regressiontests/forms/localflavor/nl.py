# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ NL form fields.

tests = r"""
# NLPhoneNumberField ########################################################

>>> from django.contrib.localflavor.nl.forms import NLPhoneNumberField
>>> f = NLPhoneNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean('012-3456789')
'012-3456789'
>>> f.clean('0123456789')
'0123456789'
>>> f.clean('+31-12-3456789')
'+31-12-3456789'
>>> f.clean('(0123) 456789')
'(0123) 456789'
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid phone number']

# NLZipCodeField ############################################################

>>> from django.contrib.localflavor.nl.forms import NLZipCodeField
>>> f = NLZipCodeField(required=False)
>>> f.clean('')
u''
>>> f.clean('1234ab')
u'1234 AB'
>>> f.clean('1234 ab')
u'1234 AB'
>>> f.clean('1234 AB')
u'1234 AB'
>>> f.clean('0123AB')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid postal code']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid postal code']

# NLSoFiNumberField #########################################################

>>> from django.contrib.localflavor.nl.forms import NLSoFiNumberField
>>> f = NLSoFiNumberField(required=False)
>>> f.clean('')
u''
>>> f.clean('123456782')
'123456782'
>>> f.clean('000000000')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid SoFi number']
>>> f.clean('123456789')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid SoFi number']
>>> f.clean('foo')
Traceback (most recent call last):
    ...
ValidationError: [u'Enter a valid SoFi number']

# NLProvinceSelect ##########################################################

>>> from django.contrib.localflavor.nl.forms import NLProvinceSelect
>>> s = NLProvinceSelect()
>>> s.render('provinces', 'OV')
u'<select name="provinces">\n<option value="DR">Drenthe</option>\n<option value="FL">Flevoland</option>\n<option value="FR">Friesland</option>\n<option value="GL">Gelderland</option>\n<option value="GR">Groningen</option>\n<option value="LB">Limburg</option>\n<option value="NB">Noord-Brabant</option>\n<option value="NH">Noord-Holland</option>\n<option value="OV" selected="selected">Overijssel</option>\n<option value="UT">Utrecht</option>\n<option value="ZE">Zeeland</option>\n<option value="ZH">Zuid-Holland</option>\n</select>'
"""
