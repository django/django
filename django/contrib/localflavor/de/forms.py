"""
DE-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import gettext
import re

class DEZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(DEZipCodeField, self).__init__(r'^\d{5}$',
        max_length=None, min_length=None,
        error_message=gettext(u'Enter a zip code in the format XXXXX.'),
        *args, **kwargs)

class DEStateSelect(Select):
    """
    A Select widget that uses a list of DE states as its choices.
    """
    def __init__(self, attrs=None):
        from de_states import STATE_CHOICES # relative import
        super(DEStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
