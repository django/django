"""
Australian-specific Form helpers
"""

from __future__ import absolute_import

import re

from django.contrib.localflavor.au.au_states import STATE_CHOICES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _


PHONE_DIGITS_RE = re.compile(r'^(\d{10})$')

class AUPostCodeField(RegexField):
    """ Australian post code field.

    Assumed to be 4 digits.
    Northern Territory 3-digit postcodes should have leading zero.
    """
    default_error_messages = {
        'invalid': _('Enter a 4 digit postcode.'),
    }

    def __init__(self, max_length=4, min_length=None, *args, **kwargs):
        super(AUPostCodeField, self).__init__(r'^\d{4}$',
            max_length, min_length, *args, **kwargs)


class AUPhoneNumberField(Field):
    """Australian phone number field."""
    default_error_messages = {
        'invalid': u'Phone numbers must contain 10 digits.',
    }

    def clean(self, value):
        """
        Validate a phone number. Strips parentheses, whitespace and hyphens.
        """
        super(AUPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+|-)', '', smart_unicode(value))
        phone_match = PHONE_DIGITS_RE.search(value)
        if phone_match:
            return u'%s' % phone_match.group(1)
        raise ValidationError(self.error_messages['invalid'])


class AUStateSelect(Select):
    """
    A Select widget that uses a list of Australian states/territories as its
    choices.
    """
    def __init__(self, attrs=None):
        super(AUStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
