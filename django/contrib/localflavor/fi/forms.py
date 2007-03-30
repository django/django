"""
FI-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import RegexField, Select
from django.utils.translation import gettext

class FIZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(FIZipCodeField, self).__init__(r'^\d{5}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX.'),
            *args, **kwargs)

class FIMunicipalitySelect(Select):
    """
    A Select widget that uses a list of Finnish municipalities as its choices.
    """
    def __init__(self, attrs=None):
        from fi_municipalities import MUNICIPALITY_CHOICES # relative import
        super(FIMunicipalitySelect, self).__init__(attrs, choices=MUNICIPALITY_CHOICES)
