"""
India-specific Form helpers.
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.encoding import smart_unicode
from django.utils.translation import gettext
import re


class INZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(INZipCodeField, self).__init__(r'^\d{6}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXXXX.'),
            *args, **kwargs)

class INStateField(Field):
    """
    A form field that validates its input is a Indian state name or
    abbreviation. It normalizes the input to the standard two-letter vehicle
    registration abbreviation for the given state or union territory
    """
    def clean(self, value):
        from in_states import STATES_NORMALIZED
        super(INStateField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        try:
            value = value.strip().lower()
        except AttributeError:
            pass
        else:
            try:
                return smart_unicode(STATES_NORMALIZED[value.strip().lower()])
            except KeyError:
                pass
        raise ValidationError(u'Enter a Indian state or territory.')

class INStateSelect(Select):
    """
    A Select widget that uses a list of Indian states/territories as its
    choices.
    """
    def __init__(self, attrs=None):
        from in_states import STATE_CHOICES
        super(INStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

