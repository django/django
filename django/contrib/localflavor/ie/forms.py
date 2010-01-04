"""
UK-specific Form helpers
"""

from django.forms.fields import Select

class IECountySelect(Select):
    """
    A Select widget that uses a list of Irish Counties as its choices.
    """
    def __init__(self, attrs=None):
        from ie_counties import IE_COUNTY_CHOICES
        super(IECountySelect, self).__init__(attrs, choices=IE_COUNTY_CHOICES)
