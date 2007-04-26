# -*- coding: utf-8 -*-
"""
BR-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, CharField, Select, EMPTY_VALUES
from django.utils.encoding import smart_unicode
from django.utils.translation import gettext
import re

phone_digits_re = re.compile(r'^(\d{2})[-\.]?(\d{4})[-\.]?(\d{4})$')

class BRZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(BRZipCodeField, self).__init__(r'^\d{5}-\d{3}$',
            max_length=None, min_length=None,
            error_message=gettext('Enter a zip code in the format XXXXX-XXX.'),
            *args, **kwargs)

class BRPhoneNumberField(Field):
    def clean(self, value):
        super(BRPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(gettext(u'Phone numbers must be in XX-XXXX-XXXX format.'))

class BRStateSelect(Select):
    """
    A Select widget that uses a list of brazilian states/territories
    as its choices.
    """
    def __init__(self, attrs=None):
        from br_states import STATE_CHOICES # relative import
        super(BRStateSelect, self).__init__(attrs, choices=STATE_CHOICES)


def DV_maker(v):
    if v >= 2:
        return 11 - v
    return 0

class BRCPFField(CharField):
    """
    This field validate a CPF number or a CPF string. A CPF number is
    compounded by XXX.XXX.XXX-VD, the two last digits are check digits.

    More information:
    http://en.wikipedia.org/wiki/Cadastro_de_Pessoas_F%C3%ADsicas
    """
    def __init__(self, *args, **kwargs):
        super(BRCPFField, self).__init__(max_length=14, min_length=11, *args, **kwargs)

    def clean(self, value):
        """
        Value can be either a string in the format XXX.XXX.XXX-XX or an
        11-digit number.
        """
        value = super(BRCPFField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        orig_value = value[:]
        if not value.isdigit():
            value = re.sub("[-\.]", "", value)
        try:
            int(value)
        except ValueError:
            raise ValidationError(gettext("This field requires only numbers"))
        if len(value) != 11:
            raise ValidationError(gettext("This field requires at most 11 digits or 14 characters."))
        orig_dv = value[-2:]

        new_1dv = sum([i * int(value[idx]) for idx, i in enumerate(range(10, 1, -1))])
        new_1dv = DV_maker(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum([i * int(value[idx]) for idx, i in enumerate(range(11, 1, -1))])
        new_2dv = DV_maker(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise ValidationError(gettext("Invalid CPF number."))

        return orig_value

class BRCNPJField(Field):
    def clean(self, value):
        """
        Value can be either a string in the format XX.XXX.XXX/XXXX-XX or a
        group of 14 characters.
        """
        value = super(BRCNPJField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        orig_value = value[:]
        if not value.isdigit():
            value = re.sub("[-/\.]", "", value)
        try:
            int(value)
        except ValueError:
            raise ValidationError("This field requires only numbers")
        if len(value) != 14:
            raise ValidationError(
                gettext("This field requires at least 14 digits"))
        orig_dv = value[-2:]

        new_1dv = sum([i * int(value[idx]) for idx, i in enumerate(range(5, 1, -1) + range(9, 1, -1))])
        new_1dv = DV_maker(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum([i * int(value[idx]) for idx, i in enumerate(range(6, 1, -1) + range(9, 1, -1))])
        new_2dv = DV_maker(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise ValidationError(gettext("Invalid CNPJ number"))

        return orig_value

