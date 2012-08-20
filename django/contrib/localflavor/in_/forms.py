"""
India-specific Form helpers.
"""

from __future__ import absolute_import, unicode_literals

import re

from django.contrib.localflavor.in_.in_states import STATES_NORMALIZED, STATE_CHOICES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, CharField, Select
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _


phone_digits_re = re.compile(r"""
(
    (?P<std_code>                   # the std-code group
        ^0                          # all std-codes start with 0
        (
            (?P<twodigit>\d{2})   | # either two, three or four digits
            (?P<threedigit>\d{3}) | # following the 0
            (?P<fourdigit>\d{4})
        )
    )
    [-\s]                           # space or -
    (?P<phone_no>                   # the phone number group
        [1-6]                       # first digit of phone number
        (
            (?(twodigit)\d{7})   |  # 7 more phone digits for 3 digit stdcode
            (?(threedigit)\d{6}) |  # 6 more phone digits for 4 digit stdcode
            (?(fourdigit)\d{5})     # 5 more phone digits for 5 digit stdcode
        )
    )
)$""", re.VERBOSE)


class INZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXXXX or XXX XXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(INZipCodeField, self).__init__(r'^\d{3}\s?\d{3}$',
            max_length, min_length, *args, **kwargs)

    def clean(self, value):
        super(INZipCodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        # Convert to "NNNNNN" if "NNN NNN" given
        value = re.sub(r'^(\d{3})\s(\d{3})$', r'\1\2', value)
        return value


class INStateField(Field):
    """
    A form field that validates its input is a Indian state name or
    abbreviation. It normalizes the input to the standard two-letter vehicle
    registration abbreviation for the given state or union territory
    """
    default_error_messages = {
        'invalid': _('Enter an Indian state or territory.'),
    }

    def clean(self, value):
        super(INStateField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        try:
            value = value.strip().lower()
        except AttributeError:
            pass
        else:
            try:
                return smart_text(STATES_NORMALIZED[value.strip().lower()])
            except KeyError:
                pass
        raise ValidationError(self.error_messages['invalid'])


class INStateSelect(Select):
    """
    A Select widget that uses a list of Indian states/territories as its
    choices.
    """
    def __init__(self, attrs=None):
        super(INStateSelect, self).__init__(attrs, choices=STATE_CHOICES)


class INPhoneNumberField(CharField):
    """
    INPhoneNumberField validates that the data is a valid Indian phone number,
    including the STD code. It's normalised to 0XXX-XXXXXXX or 0XXX XXXXXXX
    format. The first string is the STD code which is a '0' followed by 2-4
    digits. The second string is 8 digits if the STD code is 3 digits, 7
    digits if the STD code is 4 digits and 6 digits if the STD code is 5
    digits. The second string will start with numbers between 1 and 6. The
    separator is either a space or a hyphen.
    """
    default_error_messages = {
        'invalid': _('Phone numbers must be in 02X-8X or 03X-7X or 04X-6X format.'),
    }

    def clean(self, value):
        super(INPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        value = smart_text(value)
        m = phone_digits_re.match(value)
        if m:
            return '%s' % (value)
        raise ValidationError(self.error_messages['invalid'])

