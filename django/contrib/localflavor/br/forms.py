# -*- coding: utf-8 -*-
"""
BR-specific Form helpers
"""

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, CharField, Select
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _
import re

phone_digits_re = re.compile(r'^(\d{2})[-\.]?(\d{4})[-\.]?(\d{4})$')

class BRZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXXX-XXX.'),
    }

    def __init__(self, *args, **kwargs):
        super(BRZipCodeField, self).__init__(r'^\d{5}-\d{3}$',
            max_length=None, min_length=None, *args, **kwargs)

class BRPhoneNumberField(Field):
    default_error_messages = {
        'invalid': _('Phone numbers must be in XX-XXXX-XXXX format.'),
    }

    def clean(self, value):
        super(BRPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(self.error_messages['invalid'])

class BRStateSelect(Select):
    """
    A Select widget that uses a list of Brazilian states/territories
    as its choices.
    """
    def __init__(self, attrs=None):
        from br_states import STATE_CHOICES
        super(BRStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

class BRStateChoiceField(Field):
    """
    A choice field that uses a list of Brazilian states as its choices.
    """
    widget = Select
    default_error_messages = {
        'invalid': _(u'Select a valid brazilian state. That state is not one of the available states.'),
    }

    def __init__(self, required=True, widget=None, label=None,
                 initial=None, help_text=None):
        super(BRStateChoiceField, self).__init__(required, widget, label,
                                                 initial, help_text)
        from br_states import STATE_CHOICES
        self.widget.choices = STATE_CHOICES

    def clean(self, value):
        value = super(BRStateChoiceField, self).clean(value)
        if value in EMPTY_VALUES:
            value = u''
        value = smart_unicode(value)
        if value == u'':
            return value
        valid_values = set([smart_unicode(k) for k, v in self.widget.choices])
        if value not in valid_values:
            raise ValidationError(self.error_messages['invalid'])
        return value

def DV_maker(v):
    if v >= 2:
        return 11 - v
    return 0

class BRCPFField(CharField):
    """
    This field validate a CPF number or a CPF string. A CPF number is
    compounded by XXX.XXX.XXX-VD. The two last digits are check digits.

    More information:
    http://en.wikipedia.org/wiki/Cadastro_de_Pessoas_F%C3%ADsicas
    """
    default_error_messages = {
        'invalid': _("Invalid CPF number."),
        'max_digits': _("This field requires at most 11 digits or 14 characters."),
        'digits_only': _("This field requires only numbers."),
    }

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
            raise ValidationError(self.error_messages['digits_only'])
        if len(value) != 11:
            raise ValidationError(self.error_messages['max_digits'])
        orig_dv = value[-2:]

        new_1dv = sum([i * int(value[idx]) for idx, i in enumerate(range(10, 1, -1))])
        new_1dv = DV_maker(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum([i * int(value[idx]) for idx, i in enumerate(range(11, 1, -1))])
        new_2dv = DV_maker(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise ValidationError(self.error_messages['invalid'])

        return orig_value

class BRCNPJField(Field):
    default_error_messages = {
        'invalid': _("Invalid CNPJ number."),
        'digits_only': _("This field requires only numbers."),
        'max_digits': _("This field requires at least 14 digits"),
    }

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
            raise ValidationError(self.error_messages['digits_only'])
        if len(value) != 14:
            raise ValidationError(self.error_messages['max_digits'])
        orig_dv = value[-2:]

        new_1dv = sum([i * int(value[idx]) for idx, i in enumerate(range(5, 1, -1) + range(9, 1, -1))])
        new_1dv = DV_maker(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum([i * int(value[idx]) for idx, i in enumerate(range(6, 1, -1) + range(9, 1, -1))])
        new_2dv = DV_maker(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise ValidationError(self.error_messages['invalid'])

        return orig_value
