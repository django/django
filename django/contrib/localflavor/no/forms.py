# -*- coding: iso-8859-1 -*-
"""
Norwegian-specific Form helpers
"""

import re, datetime
from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import gettext

class NOZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(NOZipCodeField, self).__init__(r'^\d{4}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXX.'),
            *args, **kwargs)

class NOMunicipalitySelect(Select):
    """
    A Select widget that uses a list of Norwegian municipalities (fylker)
    as its choices.
    """
    def __init__(self, attrs=None):
        from no_municipalities import MUNICIPALITY_CHOICES
        super(NOMunicipalitySelect, self).__init__(attrs, choices=MUNICIPALITY_CHOICES)

class NOSocialSecurityNumber(Field):
    """
    Algorithm is documented at http://no.wikipedia.org/wiki/Personnummer
    """
    def clean(self, value):
        super(NOSocialSecurityNumber, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        msg = gettext(u'Enter a valid Norwegian social security number.')
        if not re.match(r'^\d{11}$', value):
            raise ValidationError(msg)

        day = int(value[:2])
        month = int(value[2:4])
        year2 = int(value[4:6])

        inum = int(value[6:9])
        self.birthday = None
        try:
            if 000 <= inum < 500:
                self.birthday = datetime.date(1900+year2, month, day)
            if 500 <= inum < 750 and year2 > 54:
                self.birthday = datetime.date(1800+year2, month, day)
            if 500 <= inum < 1000 and year2 < 40:
                self.birthday = datetime.date(2000+year2, month, day)
            if 900 <= inum < 1000 and year2 > 39:
                self.birthday = datetime.date(1900+year2, month, day)
        except ValueError:
            raise ValidationError(msg)

        sexnum = int(value[8])
        if sexnum % 2 == 0:
            self.gender = 'F'
        else:
            self.gender = 'M'
        
        digits = map(int, list(value))
        weight_1 = [3, 7, 6, 1, 8, 9, 4, 5, 2, 1, 0]
        weight_2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2, 1]

        def multiply_reduce(aval, bval):
            return sum((a * b) for (a, b) in zip(aval, bval))

        if multiply_reduce(digits, weight_1) % 11 != 0:
            raise ValidationError(msg)
        if multiply_reduce(digits, weight_2) % 11 != 0:
            raise ValidationError(msg)

        return value
    
