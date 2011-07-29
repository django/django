"""
Ecuador-specific form helpers.
"""

from django.forms.fields import Select

class ECProvinceSelect(Select):
    """
    A Select widget that uses a list of Ecuador provinces as its choices.
    """
    def __init__(self, attrs=None):
        from ec_provinces import PROVINCE_CHOICES
        super(ECProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)
