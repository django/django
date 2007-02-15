"""
USA-specific Form helpers
"""

from django.newforms.fields import RegexField
from django.utils.translation import gettext

class USZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(USZipCodeField, self).__init__(r'^\d{5}(?:-\d{4})?$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX or XXXXX-XXXX.'),
            *args, **kwargs)
