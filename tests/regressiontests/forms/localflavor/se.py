# -*- coding: utf-8 -*-
# Tests for the contrib/localflavor/se form fields.

tests = r"""
# Monkey-patch datetime.date
>>> import datetime
>>> class MockDate(datetime.date):
...     def today(cls):
...         return datetime.date(2008, 5, 14)
...     today = classmethod(today)
... 
>>> olddate = datetime.date
>>> datetime.date = MockDate
>>> datetime.date.today()
...MockDate(2008, 5, 14)


# SECountySelect #####################################################
>>> from django.contrib.localflavor.se.forms import SECountySelect

>>> w = SECountySelect()
>>> w.render('swedish_county', 'E')
u'<select name="swedish_county">\n<option value="AB">Stockholm</option>\n<option value="AC">V\xe4sterbotten</option>\n<option value="BD">Norrbotten</option>\n<option value="C">Uppsala</option>\n<option value="D">S\xf6dermanland</option>\n<option value="E" selected="selected">\xd6sterg\xf6tland</option>\n<option value="F">J\xf6nk\xf6ping</option>\n<option value="G">Kronoberg</option>\n<option value="H">Kalmar</option>\n<option value="I">Gotland</option>\n<option value="K">Blekinge</option>\n<option value="M">Sk\xe5ne</option>\n<option value="N">Halland</option>\n<option value="O">V\xe4stra G\xf6taland</option>\n<option value="S">V\xe4rmland</option>\n<option value="T">\xd6rebro</option>\n<option value="U">V\xe4stmanland</option>\n<option value="W">Dalarna</option>\n<option value="X">G\xe4vleborg</option>\n<option value="Y">V\xe4sternorrland</option>\n<option value="Z">J\xe4mtland</option>\n</select>'

# SEOrganisationNumberField #######################################

>>> from django.contrib.localflavor.se.forms import SEOrganisationNumberField

>>> f = SEOrganisationNumberField()

# Ordinary personal identity numbers for sole proprietors
# The same rules as for SEPersonalIdentityField applies here
>>> f.clean('870512-1989')
u'198705121989'
>>> f.clean('19870512-1989')
u'198705121989'
>>> f.clean('870512-2128')
u'198705122128'
>>> f.clean('081015-6315')
u'190810156315'
>>> f.clean('081015+6315')
u'180810156315'
>>> f.clean('0810156315')
u'190810156315'

>>> f.clean('081015 6315')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']
>>> f.clean('950231-4496')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']
>>> f.clean('6914104499')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']
>>> f.clean('950d314496')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']
>>> f.clean('invalid!!!')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']
>>> f.clean('870514-1111')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']


# Empty values
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

# Co-ordination number checking
# Co-ordination numbers are not valid organisation numbers
>>> f.clean('870574-1315')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']

>>> f.clean('870573-1311')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']

# Test some different organisation numbers
>>> f.clean('556074-7569') # IKEA Linköping
u'5560747569'

>>> f.clean('556074-3089') # Volvo Personvagnar
u'5560743089'

>>> f.clean('822001-5476') # LJS (organisation)
u'8220015476'

>>> f.clean('8220015476') # LJS (organisation)
u'8220015476'

>>> f.clean('2120000449') # Katedralskolan Linköping (school)
u'2120000449'

# Faux organisation number, which tests that the checksum can be 0
>>> f.clean('232518-5060')
u'2325185060'

>>> f.clean('556074+3089') # Volvo Personvagnar, bad format
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']


# Invalid checksum
>>> f.clean('2120000441')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']

# Valid checksum but invalid organisation type
f.clean('1120000441')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish organisation number.']

# Empty values with required=False
>>> f = SEOrganisationNumberField(required=False)

>>> f.clean(None)
u''

>>> f.clean('')
u''


# SEPersonalIdentityNumberField #######################################

>>> from django.contrib.localflavor.se.forms import SEPersonalIdentityNumberField

>>> f = SEPersonalIdentityNumberField()

# Valid id numbers
>>> f.clean('870512-1989')
u'198705121989'

>>> f.clean('870512-2128')
u'198705122128'

>>> f.clean('19870512-1989')
u'198705121989'

>>> f.clean('198705121989')
u'198705121989'

>>> f.clean('081015-6315')
u'190810156315'

>>> f.clean('0810156315')
u'190810156315'

# This is a "special-case" in the checksum calculation,
# where the sum is divisible by 10 (the checksum digit == 0)
>>> f.clean('8705141060')
u'198705141060'

# + means that the person is older than 100 years
>>> f.clean('081015+6315')
u'180810156315'

# Bogus values
>>> f.clean('081015 6315')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

>>> f.clean('950d314496')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

>>> f.clean('invalid!!!')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']


# Invalid dates

# February 31st does not exist
>>> f.clean('950231-4496')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

# Month 14 does not exist
>>> f.clean('6914104499')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

# There are no Swedish personal id numbers where year < 1800
>>> f.clean('17430309-7135')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

# Invalid checksum
>>> f.clean('870514-1111')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

# Empty values
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

# Co-ordination number checking
>>> f.clean('870574-1315')
u'198705741315'

>>> f.clean('870574+1315')
u'188705741315'

>>> f.clean('198705741315')
u'198705741315'

# Co-ordination number with bad checksum
>>> f.clean('870573-1311')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']


# Check valid co-ordination numbers, that should not be accepted 
# because of coordination_number=False
>>> f = SEPersonalIdentityNumberField(coordination_number=False)

>>> f.clean('870574-1315')
Traceback (most recent call last):
...
ValidationError: [u'Co-ordination numbers are not allowed.']

>>> f.clean('870574+1315')
Traceback (most recent call last):
...
ValidationError: [u'Co-ordination numbers are not allowed.']

>>> f.clean('8705741315')
Traceback (most recent call last):
...
ValidationError: [u'Co-ordination numbers are not allowed.']

# Invalid co-ordination numbers should be treated as invalid, and not
# as co-ordination numbers
>>> f.clean('870573-1311')
Traceback (most recent call last):
...
ValidationError: [u'Enter a valid Swedish personal identity number.']

# Empty values with required=False
>>> f = SEPersonalIdentityNumberField(required=False)

>>> f.clean(None)
u''

>>> f.clean('')
u''

# SEPostalCodeField ###############################################
>>> from django.contrib.localflavor.se.forms import SEPostalCodeField
>>> f = SEPostalCodeField()
>>>
Postal codes can have spaces
>>> f.clean('589 37')
u'58937'

... but the dont have to
>>> f.clean('58937')
u'58937'
>>> f.clean('abcasfassadf')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Swedish postal code in the format XXXXX.']

# Only one space is allowed for separation
>>> f.clean('589  37')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Swedish postal code in the format XXXXX.']

# The postal code must not start with 0
>>> f.clean('01234')
Traceback (most recent call last):
...
ValidationError: [u'Enter a Swedish postal code in the format XXXXX.']

# Empty values
>>> f.clean('')
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

>>> f.clean(None)
Traceback (most recent call last):
...
ValidationError: [u'This field is required.']

# Empty values, required=False
>>> f = SEPostalCodeField(required=False)
>>> f.clean('')
u''
>>> f.clean(None)
u''

# Revert the monkey patching
>>> datetime.date = olddate

"""
