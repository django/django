"""
FI-specific Form helpers
"""

import re
from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import ugettext

class FIZipCodeField(RegexField):
    default_error_messages = {
        'invalid': ugettext('Enter a zip code in the format XXXXX.'),
    }
    def __init__(self, *args, **kwargs):
        super(FIZipCodeField, self).__init__(r'^\d{5}$',
            max_length=None, min_length=None, *args, **kwargs)

class FIMunicipalitySelect(Select):
    """
    A Select widget that uses a list of Finnish municipalities as its choices.
    """
    def __init__(self, attrs=None):
        from fi_municipalities import MUNICIPALITY_CHOICES
        super(FIMunicipalitySelect, self).__init__(attrs, choices=MUNICIPALITY_CHOICES)

class FISocialSecurityNumber(Field):
    default_error_messages = {
        'invalid': ugettext('Enter a valid Finnish social security number.'),
    }

    def clean(self, value):
        super(FISocialSecurityNumber, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        checkmarks = "0123456789ABCDEFHJKLMNPRSTUVWXY"
        result = re.match(r"""^
            (?P<date>([0-2]\d|3[01])
            (0\d|1[012])
            (\d{2}))
            [A+-]
            (?P<serial>(\d{3}))
            (?P<checksum>[%s])$""" % checkmarks, value, re.VERBOSE | re.IGNORECASE)
        if not result:
            raise ValidationError(self.error_messages['invalid'])
        gd = result.groupdict()
        checksum = int(gd['date'] + gd['serial'])
        if checkmarks[checksum % len(checkmarks)] == gd['checksum'].upper():
            return u'%s' % value.upper()
        raise ValidationError(self.error_messages['invalid'])
