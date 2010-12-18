"""
Polish-specific form helpers
"""

import re

from django.forms import ValidationError
from django.forms.fields import Select, RegexField
from django.utils.translation import ugettext_lazy as _
from django.core.validators import EMPTY_VALUES

class PLProvinceSelect(Select):
    """
    A select widget with list of Polish administrative provinces as choices.
    """
    def __init__(self, attrs=None):
        from pl_voivodeships import VOIVODESHIP_CHOICES
        super(PLProvinceSelect, self).__init__(attrs, choices=VOIVODESHIP_CHOICES)

class PLCountySelect(Select):
    """
    A select widget with list of Polish administrative units as choices.
    """
    def __init__(self, attrs=None):
        from pl_administrativeunits import ADMINISTRATIVE_UNIT_CHOICES
        super(PLCountySelect, self).__init__(attrs, choices=ADMINISTRATIVE_UNIT_CHOICES)

class PLPESELField(RegexField):
    """
    A form field that validates as Polish Identification Number (PESEL).

    Checks the following rules:
        * the length consist of 11 digits
        * has a valid checksum

    The algorithm is documented at http://en.wikipedia.org/wiki/PESEL.
    """
    default_error_messages = {
        'invalid': _(u'National Identification Number consists of 11 digits.'),
        'checksum': _(u'Wrong checksum for the National Identification Number.'),
    }

    def __init__(self, *args, **kwargs):
        super(PLPESELField, self).__init__(r'^\d{11}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self,value):
        super(PLPESELField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        if not self.has_valid_checksum(value):
            raise ValidationError(self.error_messages['checksum'])
        return u'%s' % value

    def has_valid_checksum(self, number):
        """
        Calculates a checksum with the provided algorithm.
        """
        multiple_table = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3, 1)
        result = 0
        for i in range(len(number)):
            result += int(number[i]) * multiple_table[i]
        return result % 10 == 0

class PLNIPField(RegexField):
    """
    A form field that validates as Polish Tax Number (NIP).
    Valid forms are: XXX-XXX-YY-YY or XX-XX-YYY-YYY.

    Checksum algorithm based on documentation at
    http://wipos.p.lodz.pl/zylla/ut/nip-rego.html
    """
    default_error_messages = {
        'invalid': _(u'Enter a tax number field (NIP) in the format XXX-XXX-XX-XX or XX-XX-XXX-XXX.'),
        'checksum': _(u'Wrong checksum for the Tax Number (NIP).'),
    }

    def __init__(self, *args, **kwargs):
        super(PLNIPField, self).__init__(r'^\d{3}-\d{3}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{3}-\d{3}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self,value):
        super(PLNIPField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub("[-]", "", value)
        if not self.has_valid_checksum(value):
            raise ValidationError(self.error_messages['checksum'])
        return u'%s' % value

    def has_valid_checksum(self, number):
        """
        Calculates a checksum with the provided algorithm.
        """
        multiple_table = (6, 5, 7, 2, 3, 4, 5, 6, 7)
        result = 0
        for i in range(len(number)-1):
            result += int(number[i]) * multiple_table[i]

        result %= 11
        if result == int(number[-1]):
            return True
        else:
            return False

class PLREGONField(RegexField):
    """
    A form field that validates its input is a REGON number.

    Valid regon number consists of 9 or 14 digits.
    See http://www.stat.gov.pl/bip/regon_ENG_HTML.htm for more information.
    """
    default_error_messages = {
        'invalid': _(u'National Business Register Number (REGON) consists of 9 or 14 digits.'),
        'checksum': _(u'Wrong checksum for the National Business Register Number (REGON).'),
    }

    def __init__(self, *args, **kwargs):
        super(PLREGONField, self).__init__(r'^\d{9,14}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self,value):
        super(PLREGONField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        if not self.has_valid_checksum(value):
            raise ValidationError(self.error_messages['checksum'])
        return u'%s' % value

    def has_valid_checksum(self, number):
        """
        Calculates a checksum with the provided algorithm.
        """
        weights = (
            (8, 9, 2, 3, 4, 5, 6, 7, -1),
            (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8, -1),
            (8, 9, 2, 3, 4, 5, 6, 7, -1, 0, 0, 0, 0, 0),
        )

        weights = [table for table in weights if len(table) == len(number)]

        for table in weights:
            checksum = sum([int(n) * w for n, w in zip(number, table)])
            if checksum % 11 % 10:
                return False

        return bool(weights)

class PLPostalCodeField(RegexField):
    """
    A form field that validates as Polish postal code.
    Valid code is XX-XXX where X is digit.
    """
    default_error_messages = {
        'invalid': _(u'Enter a postal code in the format XX-XXX.'),
    }

    def __init__(self, *args, **kwargs):
        super(PLPostalCodeField, self).__init__(r'^\d{2}-\d{3}$',
            max_length=None, min_length=None, *args, **kwargs)
