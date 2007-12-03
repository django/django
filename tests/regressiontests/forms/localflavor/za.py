tests = r"""
# ZAIDField #################################################################

ZAIDField validates that the date is a valid birthdate and that the value
has a valid checksum. It allows spaces and dashes, and returns a plain 
string of digits.
>>> from django.contrib.localflavor.za.forms import ZAIDField
>>> f = ZAIDField()
>>> f.clean('0002290001003')
'0002290001003'
>>> f.clean('000229 0001 003')
'0002290001003'
>>> f.clean('0102290001001')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid South African ID number']
>>> f.clean('811208')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid South African ID number']
>>> f.clean('0002290001004')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid South African ID number']

# ZAPostCodeField ###########################################################
>>> from django.contrib.localflavor.za.forms import ZAPostCodeField
>>> f = ZAPostCodeField()
>>> f.clean('abcd')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid South African postal code']
>>> f.clean('0000')
u'0000'
>>> f.clean(' 7530')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid South African postal code']

"""
