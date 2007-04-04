# -*- coding: utf-8 -*-
"""
BR-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.encoding import smart_unicode
from django.utils.translation import gettext
import re

phone_digits_re = re.compile(r'^(\d{2})[-\.]?(\d{4})[-\.]?(\d{4})$')

class BRZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(BRZipCodeField, self).__init__(r'^\d{5}-\d{3}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX-XXX.'),
            *args, **kwargs)

class BRPhoneNumberField(Field):
    def clean(self, value):
        super(BRPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\(|\)|\s+)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise ValidationError(gettext(u'Phone numbers must be in XX-XXXX-XXXX format.'))

class BRStateSelect(Select):
    """
    A Select widget that uses a list of brazilian states/territories
    as its choices.
    """
    def __init__(self, attrs=None):
        from br_states import STATE_CHOICES # relative import
        super(BRStateSelect, self).__init__(attrs, choices=STATE_CHOICES)
