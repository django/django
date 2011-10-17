"""
USA-specific Form helpers
"""

from __future__ import absolute_import

import re

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select, CharField
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _


phone_digits_re = re.compile(r'^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')
ssn_re = re.compile(r"^(?P<area>\d{3})[-\ ]?(?P<group>\d{2})[-\ ]?(?P<serial>\d{4})$")

class USZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXXX or XXXXX-XXXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(USZipCodeField, self).__init__(r'^\d{5}(?:-\d{4})?$',
            max_length, min_length, *args, **kwargs)

class USPhoneNumberField(CharField):
    default_error_messages = {
        'invalid': _('Phone numbers must be in XXX-XXX-XXXX format.'),
    }

    def clean(self, value):
        super(USPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(self.error_messages['invalid'])

class USSocialSecurityNumberField(Field):
    """
    A United States Social Security number.

    Checks the following rules to determine whether the number is valid:

        * Conforms to the XXX-XX-XXXX format.
        * No group consists entirely of zeroes.
        * The leading group is not "666" (block "666" will never be allocated).
        * The number is not in the promotional block 987-65-4320 through
          987-65-4329, which are permanently invalid.
        * The number is not one known to be invalid due to otherwise widespread
          promotional use or distribution (e.g., the Woolworth's number or the
          1962 promotional number).
    """
    default_error_messages = {
        'invalid': _('Enter a valid U.S. Social Security number in XXX-XX-XXXX format.'),
    }

    def clean(self, value):
        super(USSocialSecurityNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        match = re.match(ssn_re, value)
        if not match:
            raise ValidationError(self.error_messages['invalid'])
        area, group, serial = match.groupdict()['area'], match.groupdict()['group'], match.groupdict()['serial']

        # First pass: no blocks of all zeroes.
        if area == '000' or \
           group == '00' or \
           serial == '0000':
            raise ValidationError(self.error_messages['invalid'])

        # Second pass: promotional and otherwise permanently invalid numbers.
        if area == '666' or \
           (area == '987' and group == '65' and 4320 <= int(serial) <= 4329) or \
           value == '078-05-1120' or \
           value == '219-09-9999':
            raise ValidationError(self.error_messages['invalid'])
        return u'%s-%s-%s' % (area, group, serial)

class USStateField(Field):
    """
    A form field that validates its input is a U.S. state name or abbreviation.
    It normalizes the input to the standard two-leter postal service
    abbreviation for the given state.
    """
    default_error_messages = {
        'invalid': _('Enter a U.S. state or territory.'),
    }

    def clean(self, value):
        from django.contrib.localflavor.us.us_states import STATES_NORMALIZED
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
        raise ValidationError(self.error_messages['invalid'])

class USStateSelect(Select):
    """
    A Select widget that uses a list of U.S. states/territories as its choices.
    """
    def __init__(self, attrs=None):
        from django.contrib.localflavor.us.us_states import STATE_CHOICES
        super(USStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

class USPSSelect(Select):
    """
    A Select widget that uses a list of US Postal Service codes as its
    choices.
    """
    def __init__(self, attrs=None):
        from django.contrib.localflavor.us.us_states import USPS_CHOICES
        super(USPSSelect, self).__init__(attrs, choices=USPS_CHOICES)
