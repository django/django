"""
UK-specific Form helpers
"""

from django.newforms.fields import RegexField
from django.utils.translation import gettext

class UKPostcodeField(RegexField):
    """
    A form field that validates its input is a UK postcode.

    The regular expression used is sourced from the schema for British Standard
    BS7666 address types: http://www.govtalk.gov.uk/gdsc/schemas/bs7666-v2-0.xsd
    """
    def __init__(self, *args, **kwargs):
        super(UKPostcodeField, self).__init__(r'^(GIR 0AA|[A-PR-UWYZ]([0-9]{1,2}|([A-HIK-Y][0-9](|[0-9]|[ABEHMNPRVWXY]))|[0-9][A-HJKSTUW]) [0-9][ABD-HJLNP-UW-Z]{2})$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a postcode. A space is required between the two postcode parts.'),
            *args, **kwargs)
