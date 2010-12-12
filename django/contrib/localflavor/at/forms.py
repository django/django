"""
AT-specific Form helpers
"""

import re

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select
from django.utils.translation import ugettext_lazy as _

re_ssn = re.compile(r'^\d{4} \d{6}')


class ATZipCodeField(RegexField):
    """
    A form field that validates its input is an Austrian postcode.

    Accepts 4 digits.
    """
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXX.'),
    }
    def __init__(self, *args, **kwargs):
        super(ATZipCodeField, self).__init__(r'^\d{4}$',
                max_length=None, min_length=None, *args, **kwargs)

class ATStateSelect(Select):
    """
    A Select widget that uses a list of AT states as its choices.
    """
    def __init__(self, attrs=None):
        from django.contrib.localflavor.at.at_states import STATE_CHOICES
        super(ATStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

class ATSocialSecurityNumberField(Field):
    """
    Austrian Social Security numbers are composed of a 4 digits and 6 digits
    field. The latter represents in most cases the person's birthdate while
    the first 4 digits represent a 3-digits counter and a one-digit checksum.

    The 6-digits field can also differ from the person's birthdate if the
    3-digits counter suffered an overflow.

    This code is based on information available on
    http://de.wikipedia.org/wiki/Sozialversicherungsnummer#.C3.96sterreich
    """

    default_error_messages = {
        'invalid': _(u'Enter a valid Austrian Social Security Number in XXXX XXXXXX format.'),
    }

    def clean(self, value):
        value = super(ATSocialSecurityNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u""
        if not re_ssn.search(value):
            raise ValidationError(self.error_messages['invalid'])
        sqnr, date = value.split(" ")
        sqnr, check = (sqnr[:3], (sqnr[3]))
        if int(sqnr) < 100:
           raise ValidationError(self.error_messages['invalid'])
        res = int(sqnr[0])*3 + int(sqnr[1])*7 + int(sqnr[2])*9 \
           + int(date[0])*5 + int(date[1])*8 + int(date[2])*4 \
           + int(date[3])*2 + int(date[4])*1 + int(date[5])*6
        res = res % 11
        if res != int(check):
           raise ValidationError(self.error_messages['invalid'])
        return u'%s%s %s'%(sqnr, check, date,)
