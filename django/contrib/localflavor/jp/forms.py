"""
JP-specific Form helpers
"""

from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.forms.fields import RegexField, Select

class JPPostalCodeField(RegexField):
    """
    A form field that validates its input is a Japanese postcode.

    Accepts 7 digits, with or without a hyphen.
    """
    default_error_messages = {
        'invalid': _('Enter a postal code in the format XXXXXXX or XXX-XXXX.'),
    }

    def __init__(self, *args, **kwargs):
        super(JPPostalCodeField, self).__init__(r'^\d{3}-\d{4}$|^\d{7}$',
            max_length=None, min_length=None, *args, **kwargs)

    def clean(self, value):
        """
        Validates the input and returns a string that contains only numbers.
        Returns an empty string for empty values.
        """
        v = super(JPPostalCodeField, self).clean(value)
        return v.replace('-', '')

class JPPrefectureSelect(Select):
    """
    A Select widget that uses a list of Japanese prefectures as its choices.
    """
    def __init__(self, attrs=None):
        from jp_prefectures import JP_PREFECTURES
        super(JPPrefectureSelect, self).__init__(attrs, choices=JP_PREFECTURES)
