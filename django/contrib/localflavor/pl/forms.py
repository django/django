"""
Polish-specific form helpers
"""

import re

from django.newforms import ValidationError
from django.newforms.fields import Select, RegexField
from django.utils.translation import ugettext as _

class PLVoivodeshipSelect(Select):
    """
    A select widget with list of Polish voivodeships (administrative provinces)
    as choices.
    """
    def __init__(self, attrs=None):
        from pl_voivodeships import VOIVODESHIP_CHOICES
        super(PLVoivodeshipSelect, self).__init__(attrs, choices=VOIVODESHIP_CHOICES)

class PLAdministrativeUnitSelect(Select):
    """
    A select widget with list of Polish administrative units as choices.
    """
    def __init__(self, attrs=None):
        from pl_administrativeunits import ADMINISTRATIVE_UNIT_CHOICES
        super(PLAdministrativeUnitSelect, self).__init__(attrs, choices=ADMINISTRATIVE_UNIT_CHOICES)

class PLNationalIdentificationNumberField(RegexField):
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
        super(PLNationalIdentificationNumberField, self).__init__(r'^\d{11}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self,value):
        super(PLNationalIdentificationNumberField, self).clean(value)
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

class PLTaxNumberField(RegexField):
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
        super(PLTaxNumberField, self).__init__(r'^\d{3}-\d{3}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{3}-\d{3}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self,value):
        super(PLTaxNumberField, self).clean(value)
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

class PLNationalBusinessRegisterField(RegexField):
    """
    A form field that validated as Polish National Official Business Register Number (REGON)
    Valid forms are: 7 or 9 digits number

    More on the field: http://www.stat.gov.pl/bip/regon_ENG_HTML.htm

    The checksum algorithm is documented at http://wipos.p.lodz.pl/zylla/ut/nip-rego.html
    """
    default_error_messages = {
        'invalid': _(u'National Business Register Number (REGON) consists of 7 or 9 digits.'),
        'checksum': _(u'Wrong checksum for the National Business Register Number (REGON).'),
    }

    def __init__(self, *args, **kwargs):
        super(PLNationalBusinessRegisterField, self).__init__(r'^\d{7,9}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self,value):
        super(PLNationalBusinessRegisterField, self).clean(value)
        if not self.has_valid_checksum(value):
            raise ValidationError(self.error_messages['checksum'])
        return u'%s' % value

    def has_valid_checksum(self, number):
        """
        Calculates a checksum with the provided algorithm.
        """
        multiple_table_7 = (2, 3, 4, 5, 6, 7)
        multiple_table_9 = (8, 9, 2, 3, 4, 5, 6, 7)
        result = 0

        if len(number) == 7:
            multiple_table = multiple_table_7
        else:
            multiple_table = multiple_table_9

        for i in range(len(number)-1):
            result += int(number[i]) * multiple_table[i]

        result %= 11
        if result == 10:
            result = 0
        if result  == int(number[-1]):
            return True
        else:
            return False

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
