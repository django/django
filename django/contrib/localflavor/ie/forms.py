"""
UK-specific Form helpers
"""

from __future__ import absolute_import

from django.contrib.localflavor.ie.ie_counties import IE_COUNTY_CHOICES
from django.forms.fields import Select


class IECountySelect(Select):
    """
    A Select widget that uses a list of Irish Counties as its choices.
    """
    def __init__(self, attrs=None):
        super(IECountySelect, self).__init__(attrs, choices=IE_COUNTY_CHOICES)
