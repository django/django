"""
IT-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import gettext
import re

class ITZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(ITZipCodeField, self).__init__(r'^\d{5}$',
        max_length=None, min_length=None,
        error_message=gettext(u'Enter a zip code in the format XXXXX.'),
        *args, **kwargs)

class ITRegionSelect(Select):
    """
    A Select widget that uses a list of IT regions as its choices.
    """
    def __init__(self, attrs=None):
        from it_region import REGION_CHOICES # relative import
        super(ITRegionSelect, self).__init__(attrs, choices=REGION_CHOICES)

class ITProvinceSelect(Select):
    """
    A Select widget that uses a list of IT regions as its choices.
    """
    def __init__(self, attrs=None):
        from it_province import PROVINCE_CHOICES # relative import
        super(ITProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)
