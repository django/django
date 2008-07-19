# -*- coding: utf-8 -*-
"""
Romanian specific form helpers.
"""

import re

from django.forms import ValidationError, Field, RegexField, Select
from django.forms.fields import EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _

class ROCIFField(RegexField):
    """
    A Romanian fiscal identity code (CIF) field

    For CIF validation algorithm see http://www.validari.ro/cui.html
    """
    default_error_messages = {
        'invalid': _("Enter a valid CIF."),
    }

    def __init__(self, *args, **kwargs):
        super(ROCIFField, self).__init__(r'^[0-9]{2,10}', max_length=10,
                min_length=2, *args, **kwargs)

    def clean(self, value):
        """
        CIF validation
        """
        value = super(ROCIFField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        # strip RO part
        if value[0:2] == 'RO':
            value = value[2:]
        key = '753217532'[::-1]
        value = value[::-1]
        key_iter = iter(key)
        checksum = 0
        for digit in value[1:]:
            checksum += int(digit) * int(key_iter.next())
        checksum = checksum * 10 % 11
        if checksum == 10:
            checksum = 0
        if checksum != int(value[0]):
            raise ValidationError(self.error_messages['invalid'])
        return value[::-1]

class ROCNPField(RegexField):
    """
    A Romanian personal identity code (CNP) field

    For CNP validation algorithm see http://www.validari.ro/cnp.html
    """
    default_error_messages = {
        'invalid': _("Enter a valid CNP."),
    }

    def __init__(self, *args, **kwargs):
        super(ROCNPField, self).__init__(r'^[1-9][0-9]{12}', max_length=13,
            min_length=13, *args, **kwargs)

    def clean(self, value):
        """
        CNP validations
        """
        value = super(ROCNPField, self).clean(value)
        # check birthdate digits
        import datetime
        try:
            datetime.date(int(value[1:3]),int(value[3:5]),int(value[5:7]))
        except:
            raise ValidationError(self.error_messages['invalid'])
        # checksum
        key = '279146358279'
        checksum = 0
        value_iter = iter(value)
        for digit in key:
            checksum += int(digit) * int(value_iter.next())
        checksum %= 11
        if checksum == 10:
            checksum = 1
        if checksum != int(value[12]):
            raise ValidationError(self.error_messages['invalid'])
        return value

class ROCountyField(Field):
    """
    A form field that validates its input is a Romanian county name or
    abbreviation. It normalizes the input to the standard vehicle registration
    abbreviation for the given county

    WARNING: This field will only accept names written with diacritics; consider
    using ROCountySelect if this behavior is unnaceptable for you
    Example:
        Argeş => valid
        Arges => invalid
    """
    default_error_messages = {
        'invalid': u'Enter a Romanian county code or name.',
    }

    def clean(self, value):
        from ro_counties import COUNTIES_CHOICES
        super(ROCountyField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        try:
            value = value.strip().upper()
        except AttributeError:
            pass
        # search for county code
        for entry in COUNTIES_CHOICES:
            if value in entry:
                return value
        # search for county name
        normalized_CC = []
        for entry in COUNTIES_CHOICES:
            normalized_CC.append((entry[0],entry[1].upper()))
        for entry in normalized_CC:
            if entry[1] == value:
                return entry[0]
        raise ValidationError(self.error_messages['invalid'])

class ROCountySelect(Select):
    """
    A Select widget that uses a list of Romanian counties (judete) as its
    choices.
    """
    def __init__(self, attrs=None):
        from ro_counties import COUNTIES_CHOICES
        super(ROCountySelect, self).__init__(attrs, choices=COUNTIES_CHOICES)

class ROIBANField(RegexField):
    """
    Romanian International Bank Account Number (IBAN) field

    For Romanian IBAN validation algorithm see http://validari.ro/iban.html
    """
    default_error_messages = {
        'invalid': _('Enter a valid IBAN in ROXX-XXXX-XXXX-XXXX-XXXX-XXXX format'),
    }

    def __init__(self, *args, **kwargs):
        super(ROIBANField, self).__init__(r'^[0-9A-Za-z\-\s]{24,40}$',
                max_length=40, min_length=24, *args, **kwargs)

    def clean(self, value):
        """
        Strips - and spaces, performs country code and checksum validation
        """
        value = super(ROIBANField, self).clean(value)
        value = value.replace('-','')
        value = value.replace(' ','')
        value = value.upper()
        if value[0:2] != 'RO':
            raise ValidationError(self.error_messages['invalid'])
        numeric_format = ''
        for char in value[4:] + value[0:4]:
            if char.isalpha():
                numeric_format += str(ord(char) - 55)
            else:
                numeric_format += char
        if int(numeric_format) % 97 != 1:
            raise ValidationError(self.error_messages['invalid'])
        return value

class ROPhoneNumberField(RegexField):
    """Romanian phone number field"""
    default_error_messages = {
        'invalid': _('Phone numbers must be in XXXX-XXXXXX format.'),
    }

    def __init__(self, *args, **kwargs):
        super(ROPhoneNumberField, self).__init__(r'^[0-9\-\(\)\s]{10,20}$',
                max_length=20, min_length=10, *args, **kwargs)

    def clean(self, value):
        """
        Strips -, (, ) and spaces. Checks the final length.
        """
        value = super(ROPhoneNumberField, self).clean(value)
        value = value.replace('-','')
        value = value.replace('(','')
        value = value.replace(')','')
        value = value.replace(' ','')
        if len(value) != 10:
            raise ValidationError(self.error_messages['invalid'])
        return value

class ROPostalCodeField(RegexField):
    """Romanian postal code field."""
    default_error_messages = {
        'invalid': _('Enter a valid postal code in the format XXXXXX'),
    }

    def __init__(self, *args, **kwargs):
        super(ROPostalCodeField, self).__init__(r'^[0-9][0-8][0-9]{4}$',
                max_length=6, min_length=6, *args, **kwargs)

