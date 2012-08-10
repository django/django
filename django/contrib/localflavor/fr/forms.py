"""
FR-specific Form helpers
"""
from __future__ import absolute_import, unicode_literals

import re

from django.contrib.localflavor.fr.fr_department import DEPARTMENT_CHOICES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import CharField, RegexField, Select
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _


phone_digits_re = re.compile(r'^0\d(\s|\.)?(\d{2}(\s|\.)?){3}\d{2}$')

class FRZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXXX.'),
    }

    def __init__(self, max_length=5, min_length=5, *args, **kwargs):
        super(FRZipCodeField, self).__init__(r'^\d{5}$',
            max_length, min_length, *args, **kwargs)

class FRPhoneNumberField(CharField):
    """
    Validate local French phone number (not international ones)
    The correct format is '0X XX XX XX XX'.
    '0X.XX.XX.XX.XX' and '0XXXXXXXXX' validate but are corrected to
    '0X XX XX XX XX'.
    """
    default_error_messages = {
        'invalid': _('Phone numbers must be in 0X XX XX XX XX format.'),
    }

    def __init__(self, max_length=14, min_length=10, *args, **kwargs):
        super(FRPhoneNumberField, self).__init__(
            max_length, min_length, *args, **kwargs)

    def clean(self, value):
        super(FRPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        value = re.sub('(\.|\s)', '', smart_text(value))
        m = phone_digits_re.search(value)
        if m:
            return '%s %s %s %s %s' % (value[0:2], value[2:4], value[4:6], value[6:8], value[8:10])
        raise ValidationError(self.error_messages['invalid'])

class FRDepartmentSelect(Select):
    """
    A Select widget that uses a list of FR departments as its choices.
    """
    def __init__(self, attrs=None):
        super(FRDepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_CHOICES)
