"""
Polish-specific form helpers
"""

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

    def has_valid_checksum(self, number):
        """
        Calculates a checksum with the provided algorithm.
        """
        multiple_table = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3, 1)
        result = 0
        for i in range(len(number)):
            result += int(number[i])*multiple_table[i]

        if result % 10 == 0:
            return True
        else:
            return False

    def __init__(self, *args, **kwargs):
        super(PLNationalIdentificationNumberField, self).__init__(r'^\d{11}$',
            max_length=None, min_length=None, error_message=_(u'National Identification Number consists of 11 digits.'),
            *args, **kwargs)

    def clean(self,value):
        super(PLNationalIdentificationNumberField, self).clean(value)
        if not self.has_valid_checksum(value):
            raise ValidationError(_(u'Wrong checksum for the National Identification Number.'))
        return u'%s' % value


class PLTaxNumberField(RegexField):
    """
    A form field that validates as Polish Tax Number (NIP).
    Valid forms are: XXX-XXX-YY-YY or XX-XX-YYY-YYY.
    """
    def __init__(self, *args, **kwargs):
        super(PLTaxNumberField, self).__init__(r'^\d{3}-\d{3}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{3}-\d{3}$',
            max_length=None, min_length=None,
            error_message=_(u'Enter a tax number field (NIP) in the format XXX-XXX-XX-XX or XX-XX-XXX-XXX.'),  *args, **kwargs)


class PLPostalCodeField(RegexField):
    """
    A form field that validates as Polish postal code.
    Valid code is XX-XXX where X is digit.
    """
    def __init__(self, *args, **kwargs):
        super(PLPostalCodeField, self).__init__(r'^\d{2}-\d{3}$',
            max_length=None, min_length=None,
            error_message=_(u'Enter a postal code in the format XX-XXX.'),
            *args, **kwargs)

