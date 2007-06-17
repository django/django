"""
USA-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.encoding import smart_unicode
from django.utils.translation import gettext
import re

phone_digits_re = re.compile(r'^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')
ssn_re = re.compile(r"^(?P<area>\d{3})[-\ ]?(?P<group>\d{2})[-\ ]?(?P<serial>\d{4})$")

class USZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(USZipCodeField, self).__init__(r'^\d{5}(?:-\d{4})?$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX or XXXXX-XXXX.'),
            *args, **kwargs)

class USPhoneNumberField(Field):
    def clean(self, value):
        super(USPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(u'Phone numbers must be in XXX-XXX-XXXX format.')

class USSocialSecurityNumberField(Field):
    """
    A United States Social Security number.

    Checks the following rules to determine whether the number is valid:

        * Conforms to the XXX-XX-XXXX format.
        * No group consists entirely of zeroes.
        * The leading group is not "666" (block "666" will never be allocated).
        * The number is not in the promotional block 987-65-4320 through 987-65-4329,
          which are permanently invalid.
        * The number is not one known to be invalid due to otherwise widespread
          promotional use or distribution (e.g., the Woolworth's number or the 1962
          promotional number).
    """
    def clean(self, value):
        super(USSocialSecurityNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        msg = gettext(u'Enter a valid U.S. Social Security number in XXX-XX-XXXX format.')
        match = re.match(ssn_re, value)
        if not match:
            raise ValidationError(msg)
        area, group, serial = match.groupdict()['area'], match.groupdict()['group'], match.groupdict()['serial']

        # First pass: no blocks of all zeroes.
        if area == '000' or \
           group == '00' or \
           serial == '0000':
            raise ValidationError(msg)

        # Second pass: promotional and otherwise permanently invalid numbers.
        if area == '666' or \
           (area == '987' and group == '65' and 4320 <= int(serial) <= 4329) or \
           value == '078-05-1120' or \
           value == '219-09-9999':
            raise ValidationError(msg)
        return u'%s-%s-%s' % (area, group, serial)

class USStateField(Field):
    """
    A form field that validates its input is a U.S. state name or abbreviation.
    It normalizes the input to the standard two-leter postal service
    abbreviation for the given state.
    """
    def clean(self, value):
        from us_states import STATES_NORMALIZED # relative import
        super(USStateField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        try:
            value = value.strip().lower()
        except AttributeError:
            pass
        else:
            try:
                return STATES_NORMALIZED[value.strip().lower()].decode('ascii')
            except KeyError:
                pass
        raise ValidationError(u'Enter a U.S. state or territory.')

class USStateSelect(Select):
    """
    A Select widget that uses a list of U.S. states/territories as its choices.
    """
    def __init__(self, attrs=None):
        from us_states import STATE_CHOICES # relative import
        super(USStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
