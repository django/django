# -*- coding: utf-8 -*-
"""
AR-specific Form helpers.
"""

from django.forms import ValidationError
from django.forms.fields import RegexField, CharField, Select, EMPTY_VALUES
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _

class ARProvinceSelect(Select):
    """
    A Select widget that uses a list of Argentinean provinces/autonomous cities
    as its choices.
    """
    def __init__(self, attrs=None):
        from ar_provinces import PROVINCE_CHOICES
        super(ARProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)

class ARPostalCodeField(RegexField):
    """
    A field that accepts a 'classic' NNNN Postal Code or a CPA.

    See http://www.correoargentino.com.ar/consulta_cpa/home.php
    """
    default_error_messages = {
        'invalid': _("Enter a postal code in the format NNNN or ANNNNAAA."),
    }

    def __init__(self, *args, **kwargs):
        super(ARPostalCodeField, self).__init__(r'^\d{4}$|^[A-HJ-NP-Za-hj-np-z]\d{4}\D{3}$',
            min_length=4, max_length=8, *args, **kwargs)

    def clean(self, value):
        value = super(ARPostalCodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        if len(value) not in (4, 8):
            raise ValidationError(self.error_messages['invalid'])
        if len(value) == 8:
            return u'%s%s%s' % (value[0].upper(), value[1:5], value[5:].upper())
        return value

class ARDNIField(CharField):
    """
    A field that validates 'Documento Nacional de Identidad' (DNI) numbers.
    """
    default_error_messages = {
        'invalid': _("This field requires only numbers."),
        'max_digits': _("This field requires 7 or 8 digits."),
    }

    def __init__(self, *args, **kwargs):
        super(ARDNIField, self).__init__(max_length=10, min_length=7, *args,
                **kwargs)

    def clean(self, value):
        """
        Value can be a string either in the [X]X.XXX.XXX or [X]XXXXXXX formats.
        """
        value = super(ARDNIField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        if not value.isdigit():
            value = value.replace('.', '')
        if not value.isdigit():
            raise ValidationError(self.error_messages['invalid'])
        if len(value) not in (7, 8):
            raise ValidationError(self.error_messages['max_digits'])

        return value

class ARCUITField(RegexField):
    """
    This field validates a CUIT (Código Único de Identificación Tributaria). A
    CUIT is of the form XX-XXXXXXXX-V. The last digit is a check digit.
    """
    default_error_messages = {
        'invalid': _('Enter a valid CUIT in XX-XXXXXXXX-X or XXXXXXXXXXXX format.'),
        'checksum': _("Invalid CUIT."),
    }

    def __init__(self, *args, **kwargs):
        super(ARCUITField, self).__init__(r'^\d{2}-?\d{8}-?\d$',
            *args, **kwargs)

    def clean(self, value):
        """
        Value can be either a string in the format XX-XXXXXXXX-X or an
        11-digit number.
        """
        value = super(ARCUITField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value, cd = self._canon(value)
        if self._calc_cd(value) != cd:
            raise ValidationError(self.error_messages['checksum'])
        return self._format(value, cd)

    def _canon(self, cuit):
        cuit = cuit.replace('-', '')
        return cuit[:-1], cuit[-1]

    def _calc_cd(self, cuit):
        mults = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
        tmp = sum([m * int(cuit[idx]) for idx, m in enumerate(mults)])
        return str(11 - tmp % 11)

    def _format(self, cuit, check_digit=None):
        if check_digit == None:
            check_digit = cuit[-1]
            cuit = cuit[:-1]
        return u'%s-%s-%s' % (cuit[:2], cuit[2:], check_digit)

