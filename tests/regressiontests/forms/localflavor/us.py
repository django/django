# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/ US form fields.

tests = r"""
# USZipCodeField ##############################################################

USZipCodeField validates that the data is either a five-digit U.S. zip code or
a zip+4.
>>> from django.contrib.localflavor.us.forms import USZipCodeField
>>> f = USZipCodeField()
>>> f.clean('60606')
u'60606'
>>> f.clean(60606)
u'60606'
>>> f.clean('04000')
u'04000'
>>> f.clean('4000')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-1234')
u'60606-1234'
>>> f.clean('6060-1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USZipCodeField(required=False)
>>> f.clean('60606')
u'60606'
>>> f.clean(60606)
u'60606'
>>> f.clean('04000')
u'04000'
>>> f.clean('4000')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-1234')
u'60606-1234'
>>> f.clean('6060-1234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean('60606-')
Traceback (most recent call last):
...
ValidationError: [u'Enter a zip code in the format XXXXX or XXXXX-XXXX.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USPhoneNumberField ##########################################################

USPhoneNumberField validates that the data is a valid U.S. phone number,
including the area code. It's normalized to XXX-XXX-XXXX format.
>>> from django.contrib.localflavor.us.forms import USPhoneNumberField
>>> f = USPhoneNumberField()
>>> f.clean('312-555-1212')
u'312-555-1212'
>>> f.clean('3125551212')
u'312-555-1212'
>>> f.clean('312 555-1212')
u'312-555-1212'
>>> f.clean('(312) 555-1212')
u'312-555-1212'
>>> f.clean('312 555 1212')
u'312-555-1212'
>>> f.clean('312.555.1212')
u'312-555-1212'
>>> f.clean('312.555-1212')
u'312-555-1212'
>>> f.clean(' (312) 555.1212 ')
u'312-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('312-55-1212')
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

>>> f = USPhoneNumberField(required=False)
>>> f.clean('312-555-1212')
u'312-555-1212'
>>> f.clean('3125551212')
u'312-555-1212'
>>> f.clean('312 555-1212')
u'312-555-1212'
>>> f.clean('(312) 555-1212')
u'312-555-1212'
>>> f.clean('312 555 1212')
u'312-555-1212'
>>> f.clean('312.555.1212')
u'312-555-1212'
>>> f.clean('312.555-1212')
u'312-555-1212'
>>> f.clean(' (312) 555.1212 ')
u'312-555-1212'
>>> f.clean('555-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean('312-55-1212')
Traceback (most recent call last):
...
ValidationError: [u'Phone numbers must be in XXX-XXX-XXXX format.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USStateField ################################################################

USStateField validates that the data is either an abbreviation or name of a
U.S. state.
>>> from django.contrib.localflavor.us.forms import USStateField
>>> f = USStateField()
>>> f.clean('il')
u'IL'
>>> f.clean('IL')
u'IL'
>>> f.clean('illinois')
u'IL'
>>> f.clean('  illinois ')
u'IL'
>>> f.clean(60606)
Traceback (most recent call last):
...
ValidationError: [u'Enter a U.S. state or territory.']
>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f = USStateField(required=False)
>>> f.clean('il')
u'IL'
>>> f.clean('IL')
u'IL'
>>> f.clean('illinois')
u'IL'
>>> f.clean('  illinois ')
u'IL'
>>> f.clean(60606)
Traceback (most recent call last):
...
ValidationError: [u'Enter a U.S. state or territory.']
>>> f.clean(None)
u''
>>> f.clean('')
u''

# USStateSelect ###############################################################

USStateSelect is a Select widget that uses a list of U.S. states/territories
as its choices.
>>> from django.contrib.localflavor.us.forms import USStateSelect
>>> w = USStateSelect()
>>> print w.render('state', 'IL')
<select name="state">
<option value="AL">Alabama</option>
<option value="AK">Alaska</option>
<option value="AS">American Samoa</option>
<option value="AZ">Arizona</option>
<option value="AR">Arkansas</option>
<option value="CA">California</option>
<option value="CO">Colorado</option>
<option value="CT">Connecticut</option>
<option value="DE">Delaware</option>
<option value="DC">District of Columbia</option>
<option value="FL">Florida</option>
<option value="GA">Georgia</option>
<option value="GU">Guam</option>
<option value="HI">Hawaii</option>
<option value="ID">Idaho</option>
<option value="IL" selected="selected">Illinois</option>
<option value="IN">Indiana</option>
<option value="IA">Iowa</option>
<option value="KS">Kansas</option>
<option value="KY">Kentucky</option>
<option value="LA">Louisiana</option>
<option value="ME">Maine</option>
<option value="MD">Maryland</option>
<option value="MA">Massachusetts</option>
<option value="MI">Michigan</option>
<option value="MN">Minnesota</option>
<option value="MS">Mississippi</option>
<option value="MO">Missouri</option>
<option value="MT">Montana</option>
<option value="NE">Nebraska</option>
<option value="NV">Nevada</option>
<option value="NH">New Hampshire</option>
<option value="NJ">New Jersey</option>
<option value="NM">New Mexico</option>
<option value="NY">New York</option>
<option value="NC">North Carolina</option>
<option value="ND">North Dakota</option>
<option value="MP">Northern Mariana Islands</option>
<option value="OH">Ohio</option>
<option value="OK">Oklahoma</option>
<option value="OR">Oregon</option>
<option value="PA">Pennsylvania</option>
<option value="PR">Puerto Rico</option>
<option value="RI">Rhode Island</option>
<option value="SC">South Carolina</option>
<option value="SD">South Dakota</option>
<option value="TN">Tennessee</option>
<option value="TX">Texas</option>
<option value="UT">Utah</option>
<option value="VT">Vermont</option>
<option value="VI">Virgin Islands</option>
<option value="VA">Virginia</option>
<option value="WA">Washington</option>
<option value="WV">West Virginia</option>
<option value="WI">Wisconsin</option>
<option value="WY">Wyoming</option>
</select>

# USSocialSecurityNumberField #################################################
>>> from django.contrib.localflavor.us.forms import USSocialSecurityNumberField
>>> f = USSocialSecurityNumberField()
>>> f.clean('987-65-4330')
u'987-65-4330'
>>> f.clean('987654330')
u'987-65-4330'
>>> f.clean('078-05-1120')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid U.S. Social Security number in XXX-XX-XXXX format.']
"""
