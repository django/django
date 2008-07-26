"""
AT-specific Form helpers
"""

import re

from django.utils.translation import ugettext_lazy as _
from django.forms.fields import Field, RegexField, Select

class ATZipCodeField(RegexField):
    """
    A form field that validates its input is an Austrian postcode.
    
    Accepts 4 digits.
    """
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXX.'),
    }
    def __init__(self, *args, **kwargs):
        super(ATZipCodeField, self).__init__(r'^\d{4}$',
                max_length=None, min_length=None, *args, **kwargs)

class ATStateSelect(Select):
    """
    A Select widget that uses a list of AT states as its choices.
    """
    def __init__(self, attrs=None):
        from at_states import STATE_CHOICES
        super(ATStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
