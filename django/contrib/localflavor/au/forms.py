"""
Australian-specific Form helpers
"""

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _
import re

PHONE_DIGITS_RE = re.compile(r'^(\d{10})$')

class AUPostCodeField(RegexField):
    """Australian post code field."""
    default_error_messages = {
        'invalid': _('Enter a 4 digit post code.'),
    }

    def __init__(self, *args, **kwargs):
        super(AUPostCodeField, self).__init__(r'^\d{4}$',
            max_length=None, min_length=None, *args, **kwargs)

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
        from au_states import STATE_CHOICES
        super(AUStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
