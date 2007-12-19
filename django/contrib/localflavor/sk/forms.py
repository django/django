"""
Slovak-specific form helpers
"""

from django.newforms.fields import Select, RegexField
from django.utils.translation import ugettext

class SKRegionSelect(Select):
    """
    A select widget widget with list of Slovak regions as choices.
    """
    def __init__(self, attrs=None):
        from sk_regions import REGION_CHOICES
        super(SKRegionSelect, self).__init__(attrs, choices=REGION_CHOICES)

class SKDistrictSelect(Select):
    """
    A select widget with list of Slovak districts as choices.
    """
    def __init__(self, attrs=None):
        from sk_districts import DISTRICT_CHOICES
        super(SKDistrictSelect, self).__init__(attrs, choices=DISTRICT_CHOICES)

class SKPostalCodeField(RegexField):
    """
    A form field that validates its input as Slovak postal code.
    Valid form is XXXXX or XXX XX, where X represents integer.
    """
    default_error_messages = {
        'invalid': ugettext(u'Enter a postal code in the format XXXXX or XXX XX.'),
    }

    def __init__(self, *args, **kwargs):
        super(SKPostalCodeField, self).__init__(r'^\d{5}$|^\d{3} \d{2}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self, value):
        """
        Validates the input and returns a string that contains only numbers.
        Returns an empty string for empty values.
        """
        v = super(SKPostalCodeField, self).clean(value)
        return v.replace(' ', '')
