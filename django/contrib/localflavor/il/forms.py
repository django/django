"""
Israeli-specific form helpers
"""
from __future__ import unicode_literals
import re

from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.forms.fields import RegexField, Field, EMPTY_VALUES
from django.utils.checksums import luhn
from django.utils.translation import ugettext_lazy as _

# Israeli ID numbers consist of up to 8 digits followed by a checksum digit.
# Numbers which are shorter than 8 digits are effectively left-zero-padded.
# The checksum digit is occasionally separated from the number by a hyphen,
# and is calculated using the luhn algorithm.
#
# Relevant references:
#
# (hebrew) http://he.wikipedia.org/wiki/%D7%9E%D7%A1%D7%A4%D7%A8_%D7%96%D7%94%D7%95%D7%AA_(%D7%99%D7%A9%D7%A8%D7%90%D7%9C)
# (hebrew) http://he.wikipedia.org/wiki/%D7%A1%D7%A4%D7%A8%D7%AA_%D7%91%D7%99%D7%A7%D7%95%D7%A8%D7%AA

id_number_re = re.compile(r'^(?P<number>\d{1,8})-?(?P<check>\d)$')

class ILPostalCodeField(RegexField):
    """
    A form field that validates its input as an Israeli postal code.
    Valid form is XXXXX where X represents integer.
    """

    default_error_messages = {
        'invalid': _('Enter a postal code in the format XXXXX'),
    }

    def __init__(self, *args, **kwargs):
        super(ILPostalCodeField, self).__init__(r'^\d{5}$', *args, **kwargs)

    def clean(self, value):
        if value not in EMPTY_VALUES:
            value = value.replace(" ", "")
        return super(ILPostalCodeField, self).clean(value)


class ILIDNumberField(Field):
    """
    A form field that validates its input as an Israeli identification number.
    Valid form is per the Israeli ID specification.
    """

    default_error_messages = {
        'invalid': _('Enter a valid ID number.'),
    }

    def clean(self, value):
        value = super(ILIDNumberField, self).clean(value)

        if value in EMPTY_VALUES:
            return ''

        match = id_number_re.match(value)
        if not match:
            raise ValidationError(self.error_messages['invalid'])

        value = match.group('number') + match.group('check')
        if not luhn(value):
            raise ValidationError(self.error_messages['invalid'])
        return value
