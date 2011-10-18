"""
Ecuador-specific form helpers.
"""

from __future__ import absolute_import

from django.contrib.localflavor.ec.ec_provinces import PROVINCE_CHOICES
from django.forms.fields import Select

class ECProvinceSelect(Select):
    """
    A Select widget that uses a list of Ecuador provinces as its choices.
    """
    def __init__(self, attrs=None):
        super(ECProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)
