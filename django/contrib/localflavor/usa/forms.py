"""
USA-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import gettext

class USZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(USZipCodeField, self).__init__(r'^\d{5}(?:-\d{4})?$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX or XXXXX-XXXX.'),
            *args, **kwargs)

class USStateField(Field):
    """
    A form field that validates its input is a U.S. state name or abbreviation.
    It normalizes the input to the standard two-leter postal service
    abbreviation for the given state.
    """
    def clean(self, value):
        from us_states import STATES_NORMALIZED # relative import
        super(USStateField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        try:
            value = value.strip().lower()
        except AttributeError:
            pass
        else:
            try:
                return STATES_NORMALIZED[value.strip().lower()].decode('ascii')
            except KeyError:
                pass
        raise ValidationError(u'Enter a U.S. state or territory.')

class USStateSelect(Select):
    """
    A Select widget that uses a list of U.S. states/territories as its choices.
    """
    def __init__(self, attrs=None):
        from us_states import STATE_CHOICES # relative import
        super(USStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
