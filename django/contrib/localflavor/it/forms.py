"""
IT-specific Form helpers
"""

from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode
from django.contrib.localflavor.it.util import ssn_check_digit, vat_number_check_digit
import re

class ITZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _('Enter a valid zip code.'),
    }
    def __init__(self, *args, **kwargs):
        super(ITZipCodeField, self).__init__(r'^\d{5}$',
        max_length=None, min_length=None, *args, **kwargs)

class ITRegionSelect(Select):
    """
    A Select widget that uses a list of IT regions as its choices.
    """
    def __init__(self, attrs=None):
        from it_region import REGION_CHOICES
        super(ITRegionSelect, self).__init__(attrs, choices=REGION_CHOICES)

class ITProvinceSelect(Select):
    """
    A Select widget that uses a list of IT provinces as its choices.
    """
    def __init__(self, attrs=None):
        from it_province import PROVINCE_CHOICES
        super(ITProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)

class ITSocialSecurityNumberField(RegexField):
    """
    A form field that validates Italian Social Security numbers (codice fiscale).
    For reference see http://www.agenziaentrate.it/ and search for
    'Informazioni sulla codificazione delle persone fisiche'.
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid Social Security number.'),
    }

    def __init__(self, *args, **kwargs):
        super(ITSocialSecurityNumberField, self).__init__(r'^\w{3}\s*\w{3}\s*\w{5}\s*\w{5}$',
        max_length=None, min_length=None, *args, **kwargs)

    def clean(self, value):
        value = super(ITSocialSecurityNumberField, self).clean(value)
        if value == u'':
            return value
        value = re.sub('\s', u'', value).upper()
        try:
            check_digit = ssn_check_digit(value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])
        if not value[15] == check_digit:
            raise ValidationError(self.error_messages['invalid'])
        return value

class ITVatNumberField(Field):
    """
    A form field that validates Italian VAT numbers (partita IVA).
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid VAT number.'),
    }

    def clean(self, value):
        value = super(ITVatNumberField, self).clean(value)
        if value == u'':
            return value
        try:
            vat_number = int(value)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])
        vat_number = str(vat_number).zfill(11)
        check_digit = vat_number_check_digit(vat_number[0:10])
        if not vat_number[10] == check_digit:
            raise ValidationError(self.error_messages['invalid'])
        return smart_unicode(vat_number)
