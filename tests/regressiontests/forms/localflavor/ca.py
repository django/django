# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ CA form fields.

tests = r"""
# CAPostalCodeField ##############################################################

CAPostalCodeField validates that the data is a six-character Canadian postal code.
>>> from django.contrib.localflavor.ca.forms import CAPostalCodeField
>>> f = CAPostalCodeField()
>>> f.clean('T2S 2H7')
u'T2S 2H7'
>>> f.clean('T2S 2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('2T6 H8I')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2S2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(90210)
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f = CAPostalCodeField(required=False)
>>> f.clean('T2S 2H7')
u'T2S 2H7'
>>> f.clean('T2S2H7')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2S 2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('2T6 H8I')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2S2H')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(90210)
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''
>>> f.clean('W2S 2H3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2W 2H7')
u'T2W 2H7'
>>> f.clean('T2S 2W7')
u'T2S 2W7'
>>> f.clean('Z2S 2H3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('T2Z 2H7')
u'T2Z 2H7'
>>> f.clean('T2S 2Z7')
u'T2S 2Z7'
>>> f.clean('F2S 2H3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('A2S 2D3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('A2I 2R3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('A2I 2R3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('A2Q 2R3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('U2B 2R3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']
>>> f.clean('O2B 2R3')
Traceback (most recent call last):
...
ValidationError: [u'Enter a postal code in the format XXX XXX.']

# CAPhoneNumberField ##########################################################

CAPhoneNumberField validates that the data is a valid Canadian phone number,
including the area code. It's normalized to XXX-XXX-XXXX format.
Note: This test is exactly the same as the USPhoneNumberField except using a real
Candian area code

>>> from django.contrib.localflavor.ca.forms import CAPhoneNumberField
>>> f = CAPhoneNumberField()
>>> f.clean('403-555-1212')
u'403-555-1212'
>>> f.clean('4035551212')
u'403-555-1212'
>>> f.clean('403 555-1212')
u'403-555-1212'
>>> f.clean('(403) 555-1212')
u'403-555-1212'
>>> f.clean('403 555 1212')
u'403-555-1212'
>>> f.clean('403.555.1212')
u'403-555-1212'
>>> f.clean('403.555-1212')
u'403-555-1212'
>>> f.clean(' (403) 555.1212 ')
u'403-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('403-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = CAPhoneNumberField(required=False)
>>> f.clean('403-555-1212')
u'403-555-1212'
>>> f.clean('4035551212')
u'403-555-1212'
>>> f.clean('403 555-1212')
u'403-555-1212'
>>> f.clean('(403) 555-1212')
u'403-555-1212'
>>> f.clean('403 555 1212')
u'403-555-1212'
>>> f.clean('403.555.1212')
u'403-555-1212'
>>> f.clean('403.555-1212')
u'403-555-1212'
>>> f.clean(' (403) 555.1212 ')
u'403-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('403-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# CAProvinceField ################################################################

CAProvinceField validates that the data is either an abbreviation or name of a
Canadian province.
>>> from django.contrib.localflavor.ca.forms import CAProvinceField
>>> f = CAProvinceField()
>>> f.clean('ab')
u'AB'
>>> f.clean('BC')
u'BC'
>>> f.clean('nova scotia')
u'NS'
>>> f.clean('  manitoba ')
u'MB'
>>> f.clean(' new brunswick ')
u'NB'
>>> f.clean('NB')
u'NB'
>>> f.clean('T2S 2H7')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Canadian province or territory.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = CAProvinceField(required=False)
>>> f.clean('ab')
u'AB'
>>> f.clean('BC')
u'BC'
>>> f.clean('nova scotia')
u'NS'
>>> f.clean('  manitoba ')
u'MB'
>>> f.clean('T2S 2H7')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Canadian province or territory.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# CAProvinceSelect ###############################################################

CAProvinceSelect is a Select widget that uses a list of Canadian provinces/territories
as its choices.
>>> from django.contrib.localflavor.ca.forms import CAProvinceSelect
>>> w = CAProvinceSelect()
>>> print w.render('province', 'AB')
<select name="province">
<option value="AB" selected="selected">Alberta</option>
<option value="BC">British Columbia</option>
<option value="MB">Manitoba</option>
<option value="NB">New Brunswick</option>
<option value="NF">Newfoundland and Labrador</option>
<option value="NT">Northwest Territories</option>
<option value="NS">Nova Scotia</option>
<option value="NU">Nunavut</option>
<option value="ON">Ontario</option>
<option value="PE">Prince Edward Island</option>
<option value="QC">Quebec</option>
<option value="SK">Saskatchewan</option>
<option value="YK">Yukon</option>
</select>

# CASocialInsuranceNumberField #################################################
>>> from django.contrib.localflavor.ca.forms import CASocialInsuranceNumberField
>>> f = CASocialInsuranceNumberField()
>>> f.clean('046-454-286')
u'046-454-286'
>>> f.clean('046-454-287')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXX format.']
>>> f.clean('046 454 286')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXX format.']
>>> f.clean('046-44-286')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Canadian Social Insurance number in XXX-XXX-XXX format.']
"""
