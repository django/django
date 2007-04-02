"""
FI-specific Form helpers
"""

import re
from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import gettext

class FIZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(FIZipCodeField, self).__init__(r'^\d{5}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX.'),
            *args, **kwargs)

class FIMunicipalitySelect(Select):
    """
    A Select widget that uses a list of Finnish municipalities as its choices.
    """
    def __init__(self, attrs=None):
        from fi_municipalities import MUNICIPALITY_CHOICES # relative import
        super(FIMunicipalitySelect, self).__init__(attrs, choices=MUNICIPALITY_CHOICES)

class FISocialSecurityNumber(Field):
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
            (?P<chechsum>[%s])$""" % checkmarks, value, re.VERBOSE | re.IGNORECASE)
        if not result:
            raise ValidationError(gettext(u'Enter a valid Finnish social security number.'))
        checksum = int(result.groupdict()['date'] + result.groupdict()['serial'])

        if checkmarks[checksum % len(checkmarks)] == result.groupdict()['chechsum'].upper():
            return u'%s' % value.upper()
        
        raise ValidationError(gettext(u'Enter a valid Finnish social security number.'))

