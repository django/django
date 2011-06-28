"""
India-specific Form helpers.
"""
import re

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _


class INZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _(u'Enter a zip code in the format XXXXXX or XXX XXX.'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(INZipCodeField, self).__init__(r'^\d{3}\s?\d{3}$',
            max_length, min_length, *args, **kwargs)

    def clean(self, value):
        super(INZipCodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        # Convert to "NNNNNN" if "NNN NNN" given
        value = re.sub(r'^(\d{3})\s(\d{3})$', r'\1\2', value)
        return value

class INStateField(Field):
    """
    A form field that validates its input is a Indian state name or
    abbreviation. It normalizes the input to the standard two-letter vehicle
    registration abbreviation for the given state or union territory
    """
    default_error_messages = {
        'invalid': _(u'Enter an Indian state or territory.'),
    }

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
        raise ValidationError(self.error_messages['invalid'])

class INStateSelect(Select):
    """
    A Select widget that uses a list of Indian states/territories as its
    choices.
    """
    def __init__(self, attrs=None):
        from in_states import STATE_CHOICES
        super(INStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

