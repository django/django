"""
NL-specific Form helpers
"""

import re

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, Select
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

pc_re = re.compile('^\d{4}[A-Z]{2}$')
sofi_re = re.compile('^\d{9}$')
numeric_re = re.compile('^\d+$')

class NLZipCodeField(Field):
    """
    A Dutch postal code field.
    """
    default_error_messages = {
        'invalid': _('Enter a valid postal code'),
    }

    def clean(self, value):
        super(NLZipCodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        value = value.strip().upper().replace(' ', '')
        if not pc_re.search(value):
            raise ValidationError(self.error_messages['invalid'])

        if int(value[:4]) < 1000:
            raise ValidationError(self.error_messages['invalid'])

        return u'%s %s' % (value[:4], value[4:])

class NLProvinceSelect(Select):
    """
    A Select widget that uses a list of provinces of the Netherlands as its
    choices.
    """
    def __init__(self, attrs=None):
        from nl_provinces import PROVINCE_CHOICES
        super(NLProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)

class NLPhoneNumberField(Field):
    """
    A Dutch telephone number field.
    """
    default_error_messages = {
        'invalid': _('Enter a valid phone number'),
    }

    def clean(self, value):
        super(NLPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        phone_nr = re.sub('[\-\s\(\)]', '', smart_unicode(value))

        if len(phone_nr) == 10 and numeric_re.search(phone_nr):
            return value

        if phone_nr[:3] == '+31' and len(phone_nr) == 12 and \
           numeric_re.search(phone_nr[3:]):
            return value

        raise ValidationError(self.error_messages['invalid'])

class NLSoFiNumberField(Field):
    """
    A Dutch social security number (SoFi/BSN) field.

    http://nl.wikipedia.org/wiki/Sofinummer
    """
    default_error_messages = {
        'invalid': _('Enter a valid SoFi number'),
    }

    def clean(self, value):
        super(NLSoFiNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        if not sofi_re.search(value):
            raise ValidationError(self.error_messages['invalid'])

        if int(value) == 0:
            raise ValidationError(self.error_messages['invalid'])

        checksum = 0
        for i in range(9, 1, -1):
            checksum += int(value[9-i]) * i
        checksum -= int(value[-1])

        if checksum % 11 != 0:
            raise ValidationError(self.error_messages['invalid'])

        return value
