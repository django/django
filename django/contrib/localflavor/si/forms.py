"""
Slovenian specific form helpers.
"""

from __future__ import absolute_import, unicode_literals

import datetime
import re

from django.contrib.localflavor.si.si_postalcodes import SI_POSTALCODES_CHOICES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import CharField, Select, ChoiceField
from django.utils.translation import ugettext_lazy as _


class SIEMSOField(CharField):
    """A form for validating Slovenian personal identification number.

    Additionally stores gender, nationality and birthday to self.info dictionary.
    """

    default_error_messages = {
        'invalid': _('This field should contain exactly 13 digits.'),
        'date': _('The first 7 digits of the EMSO must represent a valid past date.'),
        'checksum': _('The EMSO is not valid.'),
    }
    emso_regex = re.compile('^(\d{2})(\d{2})(\d{3})(\d{2})(\d{3})(\d)$')

    def clean(self, value):
        super(SIEMSOField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''

        value = value.strip()

        m = self.emso_regex.match(value)
        if m is None:
            raise ValidationError(self.default_error_messages['invalid'])

        # Validate EMSO
        s = 0
        int_values = [int(i) for i in value]
        for a, b in zip(int_values, list(range(7, 1, -1)) * 2):
            s += a * b
        chk = s % 11
        if chk == 0:
            K = 0
        else:
            K = 11 - chk

        if K == 10 or int_values[-1] != K:
            raise ValidationError(self.default_error_messages['checksum'])

        # Extract extra info in the identification number
        day, month, year, nationality, gender, chksum = [int(i) for i in m.groups()]

        if year < 890:
            year += 2000
        else:
            year += 1000

        # validate birthday
        try:
            birthday = datetime.date(year, month, day)
        except ValueError:
            raise ValidationError(self.error_messages['date'])
        if datetime.date.today() < birthday:
            raise ValidationError(self.error_messages['date'])

        self.info = {
            'gender': gender < 500 and 'male' or 'female',
            'birthdate': birthday,
            'nationality': nationality,
        }
        return value


class SITaxNumberField(CharField):
    """Slovenian tax number field.

    Valid input is SIXXXXXXXX or XXXXXXXX where X is a number.
    """

    default_error_messages = {
        'invalid': _('Enter a valid tax number in form SIXXXXXXXX'),
    }
    sitax_regex = re.compile('^(?:SI)?([1-9]\d{7})$')

    def clean(self, value):
        super(SITaxNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''

        value = value.strip()

        m = self.sitax_regex.match(value)
        if m is None:
            raise ValidationError(self.default_error_messages['invalid'])
        value = m.groups()[0]

        # Validate Tax number
        s = 0
        int_values = [int(i) for i in value]
        for a, b in zip(int_values, range(8, 1, -1)):
            s += a * b
        chk = 11 - (s % 11)
        if chk == 10:
            chk = 0

        if int_values[-1] != chk:
            raise ValidationError(self.default_error_messages['invalid'])

        return value


class SIPostalCodeField(ChoiceField):
    """Slovenian post codes field.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('choices', SI_POSTALCODES_CHOICES)
        super(SIPostalCodeField, self).__init__(*args, **kwargs)


class SIPostalCodeSelect(Select):
    """A Select widget that uses Slovenian postal codes as its choices.
    """
    def __init__(self, attrs=None):
        super(SIPostalCodeSelect, self).__init__(attrs,
            choices=SI_POSTALCODES_CHOICES)


class SIPhoneNumberField(CharField):
    """Slovenian phone number field.

    Phone number must contain at least local area code.
    Country code can be present.

    Examples:

    * +38640XXXXXX
    * 0038640XXXXXX
    * 040XXXXXX
    * 01XXXXXX
    * 0590XXXXX

    """

    default_error_messages = {
        'invalid': _('Enter phone number in form +386XXXXXXXX or 0XXXXXXXX.'),
    }
    phone_regex = re.compile('^(?:(?:00|\+)386|0)(\d{7,8})$')

    def clean(self, value):
        super(SIPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''

        value = value.replace(' ', '').replace('-', '').replace('/', '')
        m = self.phone_regex.match(value)

        if m is None:
            raise ValidationError(self.default_error_messages['invalid'])
        return m.groups()[0]
