"""
UK-specific Form helpers
"""

import re

from django.newforms.fields import CharField, Select
from django.newforms import ValidationError
from django.utils.translation import ugettext

class UKPostcodeField(CharField):
    """
    A form field that validates its input is a UK postcode.

    The regular expression used is sourced from the schema for British Standard
    BS7666 address types: http://www.govtalk.gov.uk/gdsc/schemas/bs7666-v2-0.xsd

    The value is uppercased and a space added in the correct place, if required.
    """
    default_error_messages = {
        'invalid': ugettext(u'Enter a valid postcode.'),
    }
    outcode_pattern = '[A-PR-UWYZ]([0-9]{1,2}|([A-HIK-Y][0-9](|[0-9]|[ABEHMNPRVWXY]))|[0-9][A-HJKSTUW])'
    incode_pattern = '[0-9][ABD-HJLNP-UW-Z]{2}'
    postcode_regex = re.compile(r'^(GIR 0AA|%s %s)$' % (outcode_pattern, incode_pattern))
    space_regex = re.compile(r' *(%s)$' % incode_pattern)

    def clean(self, value):
        value = super(UKPostcodeField, self).clean(value)
        if value == u'':
            return value
        postcode = value.upper().strip()
        # Put a single space before the incode (second part).
        postcode = self.space_regex.sub(r' \1', postcode)
        if not self.postcode_regex.search(postcode):
            raise ValidationError(self.default_error_messages['invalid'])
        return postcode

class UKCountySelect(Select):
    """
    A Select widget that uses a list of UK Counties/Regions as its choices.
    """
    def __init__(self, attrs=None):
        from uk_regions import UK_REGION_CHOICES
        super(UKCountySelect, self).__init__(attrs, choices=UK_REGION_CHOICES)

class UKNationSelect(Select):
    """
    A Select widget that uses a list of UK Nations as its choices.
    """
    def __init__(self, attrs=None):
        from uk_regions import UK_NATIONS_CHOICES
        super(UKNationSelect, self).__init__(attrs, choices=UK_NATIONS_CHOICES)
