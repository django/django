"""
UK-specific Form helpers
"""

from django.newforms.fields import RegexField, Select
from django.utils.translation import ugettext

class UKPostcodeField(RegexField):
    """
    A form field that validates its input is a UK postcode.

    The regular expression used is sourced from the schema for British Standard
    BS7666 address types: http://www.govtalk.gov.uk/gdsc/schemas/bs7666-v2-0.xsd
    """
    def __init__(self, *args, **kwargs):
        super(UKPostcodeField, self).__init__(r'^(GIR 0AA|[A-PR-UWYZ]([0-9]{1,2}|([A-HIK-Y][0-9](|[0-9]|[ABEHMNPRVWXY]))|[0-9][A-HJKSTUW]) [0-9][ABD-HJLNP-UW-Z]{2})$',
            max_length=None, min_length=None,
            error_message=ugettext(u'Enter a postcode. A space is required between the two postcode parts.'),
            *args, **kwargs)

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
