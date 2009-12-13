"""
Canada-specific Form helpers
"""

from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.forms.util import smart_unicode
from django.utils.translation import ugettext_lazy as _
import re

phone_digits_re = re.compile(r'^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')
sin_re = re.compile(r"^(\d{3})-(\d{3})-(\d{3})$")

class CAPostalCodeField(RegexField):
    """
    Canadian postal code field.

    Validates against known invalid characters: D, F, I, O, Q, U
    Additionally the first character cannot be Z or W.
    For more info see:
    http://www.canadapost.ca/tools/pg/manual/PGaddress-e.asp#1402170
    """
    default_error_messages = {
        'invalid': _(u'Enter a postal code in the format XXX XXX.'),
    }

    def __init__(self, *args, **kwargs):
        super(CAPostalCodeField, self).__init__(r'^[ABCEGHJKLMNPRSTVXY]\d[ABCEGHJKLMNPRSTVWXYZ] \d[ABCEGHJKLMNPRSTVWXYZ]\d$',
            max_length=None, min_length=None, *args, **kwargs)

class CAPhoneNumberField(Field):
    """Canadian phone number field."""
    default_error_messages = {
        'invalid': u'Phone numbers must be in XXX-XXX-XXXX format.',
    }

    def clean(self, value):
        """Validate a phone number.
        """
        super(CAPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(self.error_messages['invalid'])

class CAProvinceField(Field):
    """
    A form field that validates its input is a Canadian province name or abbreviation.
    It normalizes the input to the standard two-leter postal service
    abbreviation for the given province.
    """
    default_error_messages = {
        'invalid': u'Enter a Canadian province or territory.',
    }

    def clean(self, value):
        from ca_provinces import PROVINCES_NORMALIZED
        super(CAProvinceField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        try:
            value = value.strip().lower()
        except AttributeError:
            pass
        else:
            try:
                return PROVINCES_NORMALIZED[value.strip().lower()].decode('ascii')
            except KeyError:
                pass
        raise ValidationError(self.error_messages['invalid'])

class CAProvinceSelect(Select):
    """
    A Select widget that uses a list of Canadian provinces and
    territories as its choices.
    """
    def __init__(self, attrs=None):
        from ca_provinces import PROVINCE_CHOICES # relative import
        super(CAProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)

class CASocialInsuranceNumberField(Field):
    """
    A Canadian Social Insurance Number (SIN).

    Checks the following rules to determine whether the number is valid:

        * Conforms to the XXX-XXX-XXX format.
        * Passes the check digit process "Luhn Algorithm"
             See: http://en.wikipedia.org/wiki/Social_Insurance_Number
    """
    default_error_messages = {
        'invalid': _('Enter a valid Canadian Social Insurance number in XXX-XXX-XXX format.'),
    }

    def clean(self, value):
        super(CASocialInsuranceNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        match = re.match(sin_re, value)
        if not match:
            raise ValidationError(self.error_messages['invalid'])

        number = u'%s-%s-%s' % (match.group(1), match.group(2), match.group(3))
        check_number = u'%s%s%s' % (match.group(1), match.group(2), match.group(3))
        if not self.luhn_checksum_is_valid(check_number):
            raise ValidationError(self.error_messages['invalid'])
        return number

    def luhn_checksum_is_valid(self, number):
        """
        Checks to make sure that the SIN passes a luhn mod-10 checksum
        See: http://en.wikipedia.org/wiki/Luhn_algorithm
        """

        sum = 0
        num_digits = len(number)
        oddeven = num_digits & 1

        for count in range(0, num_digits):
            digit = int(number[count])

            if not (( count & 1 ) ^ oddeven ):
                digit = digit * 2
            if digit > 9:
                digit = digit - 9

            sum = sum + digit

        return ( (sum % 10) == 0 )
