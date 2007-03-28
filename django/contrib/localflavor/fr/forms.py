"""
FR-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.newforms.util import smart_unicode
from django.utils.translation import gettext
import re

phone_digits_re = re.compile(r'^0\d(\s|\.)?(\d{2}(\s|\.)?){3}\d{2}$')

class FRZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(FRZipCodeField, self).__init__(r'^\d{5}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX.'),
            *args, **kwargs)

class FRPhoneNumberField(Field):
    """
    Validate local French phone number (not international ones)
    The correct format is '0X XX XX XX XX'.
    '0X.XX.XX.XX.XX' and '0XXXXXXXXX' validate but are corrected to
    '0X XX XX XX XX'.
    """
    def clean(self, value):
        super(FRPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\.|\s)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s %s %s %s %s' % (value[0:2], value[2:4], value[4:6], value[6:8], value[8:10])
        raise ValidationError(u'Phone numbers must be in 0X XX XX XX XX format.')

class FRDepartmentSelect(Select):
    """
    A Select widget that uses a list of FR departments as its choices.
    """
    def __init__(self, attrs=None):
        from fr_department import DEPARTMENT_ASCII_CHOICES # relative import
        super(FRDepartmentSelect, self).__init__(attrs, choices=DEPARTMENT_ASCII_CHOICES)

