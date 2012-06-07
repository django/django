"""
GB-specific Form helpers
"""

from __future__ import absolute_import, unicode_literals

import re

from django.contrib.localflavor.gb.gb_regions import GB_NATIONS_CHOICES, GB_REGION_CHOICES
from django.forms.fields import CharField, Select
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _


class GBPostcodeField(CharField):
    """
    A form field that validates its input is a UK postcode.

    The regular expression used is sourced from the schema for British Standard
    BS7666 address types: http://www.govtalk.gov.uk/gdsc/schemas/bs7666-v2-0.xsd

    The value is uppercased and a space added in the correct place, if required.
    """
    default_error_messages = {
        'invalid': _('Enter a valid postcode.'),
    }
    outcode_pattern = '[A-PR-UWYZ]([0-9]{1,2}|([A-HIK-Y][0-9](|[0-9]|[ABEHMNPRVWXY]))|[0-9][A-HJKSTUW])'
    incode_pattern = '[0-9][ABD-HJLNP-UW-Z]{2}'
    postcode_regex = re.compile(r'^(GIR 0AA|%s %s)$' % (outcode_pattern, incode_pattern))
    space_regex = re.compile(r' *(%s)$' % incode_pattern)

    def clean(self, value):
        value = super(GBPostcodeField, self).clean(value)
        if value == '':
            return value
        postcode = value.upper().strip()
        # Put a single space before the incode (second part).
        postcode = self.space_regex.sub(r' \1', postcode)
        if not self.postcode_regex.search(postcode):
            raise ValidationError(self.error_messages['invalid'])
        return postcode

class GBCountySelect(Select):
    """
    A Select widget that uses a list of UK Counties/Regions as its choices.
    """
    def __init__(self, attrs=None):
        super(GBCountySelect, self).__init__(attrs, choices=GB_REGION_CHOICES)

class GBNationSelect(Select):
    """
    A Select widget that uses a list of UK Nations as its choices.
    """
    def __init__(self, attrs=None):
        super(GBNationSelect, self).__init__(attrs, choices=GB_NATIONS_CHOICES)
