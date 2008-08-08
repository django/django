# -*- coding: utf-8 -*-
"""
PE-specific Form helpers.
"""

from django.forms import ValidationError
from django.forms.fields import RegexField, CharField, Select, EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _

class PERegionSelect(Select):
    """
    A Select widget that uses a list of Peruvian Regions as its choices.
    """
    def __init__(self, attrs=None):
        from pe_region import REGION_CHOICES
        super(PERegionSelect, self).__init__(attrs, choices=REGION_CHOICES)

class PEDNIField(CharField):
    """
    A field that validates `Documento Nacional de IdentidadŽ (DNI) numbers.
    """
    default_error_messages = {
        'invalid': _("This field requires only numbers."),
        'max_digits': _("This field requires 8 digits."),
    }

    def __init__(self, *args, **kwargs):
        super(PEDNIField, self).__init__(max_length=8, min_length=8, *args,
                **kwargs)

    def clean(self, value):
        """
        Value must be a string in the XXXXXXXX formats.
        """
        value = super(PEDNIField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        if not value.isdigit():
            raise ValidationError(self.error_messages['invalid'])
        if len(value) != 8:
            raise ValidationError(self.error_messages['max_digits'])

        return value

class PERUCField(RegexField):
    """
    This field validates a RUC (Registro Unico de Contribuyentes). A RUC is of
    the form XXXXXXXXXXX.
    """
    default_error_messages = {
        'invalid': _("This field requires only numbers."),
        'max_digits': _("This field requires 11 digits."),
    }

    def __init__(self, *args, **kwargs):
        super(PERUCField, self).__init__(max_length=11, min_length=11, *args,
            **kwargs)

    def clean(self, value):
        """
        Value must be an 11-digit number.
        """
        value = super(PERUCField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        if not value.isdigit():
            raise ValidationError(self.error_messages['invalid'])
        if len(value) != 11:
            raise ValidationError(self.error_messages['max_digits'])
        return value

