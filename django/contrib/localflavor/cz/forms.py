"""
Czech-specific form helpers
"""

from __future__ import absolute_import

import re

from django.contrib.localflavor.cz.cz_regions import REGION_CHOICES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Select, RegexField, Field
from django.utils.translation import ugettext_lazy as _


birth_number = re.compile(r'^(?P<birth>\d{6})/?(?P<id>\d{3,4})$')
ic_number = re.compile(r'^(?P<number>\d{7})(?P<check>\d)$')

class CZRegionSelect(Select):
    """
    A select widget widget with list of Czech regions as choices.
    """
    def __init__(self, attrs=None):
        super(CZRegionSelect, self).__init__(attrs, choices=REGION_CHOICES)

class CZPostalCodeField(RegexField):
    """
    A form field that validates its input as Czech postal code.
    Valid form is XXXXX or XXX XX, where X represents integer.
    """
    default_error_messages = {
        'invalid': _(u'Enter a postal code in the format XXXXX or XXX XX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(CZPostalCodeField, self).__init__(r'^\d{5}$|^\d{3} \d{2}$',
            max_length, min_length, *args, **kwargs)

    def clean(self, value):
        """
        Validates the input and returns a string that contains only numbers.
        Returns an empty string for empty values.
        """
        v = super(CZPostalCodeField, self).clean(value)
        return v.replace(' ', '')

class CZBirthNumberField(Field):
    """
    Czech birth number field.
    """
    default_error_messages = {
        'invalid_format': _(u'Enter a birth number in the format XXXXXX/XXXX or XXXXXXXXXX.'),
        'invalid_gender': _(u'Invalid optional parameter Gender, valid values are \'f\' and \'m\''),
        'invalid': _(u'Enter a valid birth number.'),
    }

    def clean(self, value, gender=None):
        super(CZBirthNumberField, self).clean(value)

        if value in EMPTY_VALUES:
            return u''

        match = re.match(birth_number, value)
        if not match:
            raise ValidationError(self.error_messages['invalid_format'])

        birth, id = match.groupdict()['birth'], match.groupdict()['id']

        # Three digits for verification number were used until 1. january 1954
        if len(id) == 3:
            return u'%s' % value

        # Birth number is in format YYMMDD. Females have month value raised by 50.
        # In case that all possible number are already used (for given date),
        # the month field is raised by 20.
        if gender is not None:
            import warnings
            warnings.warn(
                "Support for validating the gender of a CZ Birth number has been deprecated.",
                DeprecationWarning)
            if gender == 'f':
                female_const = 50
            elif gender == 'm':
                female_const = 0
            else:
                raise ValidationError(self.error_messages['invalid_gender'])

            month = int(birth[2:4]) - female_const
            if (not 1 <= month <= 12):
                if (not 1 <= (month - 20) <= 12):
                    raise ValidationError(self.error_messages['invalid'])

        day = int(birth[4:6])
        if not (1 <= day <= 31):
            raise ValidationError(self.error_messages['invalid'])

        # Fourth digit has been added since 1. January 1954.
        # It is modulo of dividing birth number and verification number by 11.
        # If the modulo were 10, the last number was 0 (and therefore, the whole
        # birth number wasn't divisable by 11. These number are no longer used (since 1985)
        # and the condition 'modulo == 10' can be removed in 2085.

        modulo = int(birth + id[:3]) % 11

        if (modulo == int(id[-1])) or (modulo == 10 and id[-1] == '0'):
            return u'%s' % value
        else:
            raise ValidationError(self.error_messages['invalid'])

class CZICNumberField(Field):
    """
    Czech IC number field.
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid IC number.'),
    }

    def clean(self, value):
        super(CZICNumberField, self).clean(value)

        if value in EMPTY_VALUES:
            return u''

        match = re.match(ic_number, value)
        if not match:
            raise ValidationError(self.error_messages['invalid'])

        number, check = match.groupdict()['number'], int(match.groupdict()['check'])

        sum = 0
        weight = 8
        for digit in number:
            sum += int(digit)*weight
            weight -= 1

        remainder = sum % 11

        # remainder is equal:
        #  0 or 10: last digit is 1
        #  1: last digit is 0
        # in other case, last digit is 11 - remainder

        if (not remainder % 10 and check == 1) or \
        (remainder == 1 and check == 0) or \
        (check == (11 - remainder)):
            return u'%s' % value

        raise ValidationError(self.error_messages['invalid'])

