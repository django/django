"""
USA-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.newforms.util import smart_unicode
from django.utils.translation import gettext
import re

phone_digits_re = re.compile(r'^(?:1-?)?(\d{3})[-\.]?(\d{3})[-\.]?(\d{4})$')

class USZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(USZipCodeField, self).__init__(r'^\d{5}(?:-\d{4})?$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX or XXXXX-XXXX.'),
            *args, **kwargs)

class USPhoneNumberField(Field):
    def __init__(self, allow_letters=True, *args, **kwargs):
        self.allow_letters = allow_letters
        super(USPhoneNumberField, self).__init__(*args, **kwargs)

    def clean(self, value):
        super(USPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(u'Phone numbers must be in XXX-XXX-XXXX format.')

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
