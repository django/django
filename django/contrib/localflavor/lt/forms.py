from __future__ import unicode_literals

from django.contrib.localflavor.lt.lt_choices import COUNTY_CHOICES, \
                                                     MUNICIPALITY_CHOICES
from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Select, RegexField
from django.utils.translation import ugettext_lazy as _


class LTCountySelect(Select):

    def __init__(self, attrs=None):
        super(LTCountySelect, self).__init__(attrs, choices=COUNTY_CHOICES)


class LTMunicipalitySelect(Select):

    def __init__(self, attrs=None):
        super(LTMunicipalitySelect, self).__init__(attrs,
                                                   choices=MUNICIPALITY_CHOICES)


class LTIDCodeField(RegexField):
    """
    A form field that validates as Lithuanian ID Code.

    Checks:
        * Made of exactly 11 decimal numbers.
        * Checksum is correct.
    """
    default_error_messages = {
        'invalid': _('ID Code consists of exactly 11 decimal digits.'),
        'checksum': _('Wrong ID Code checksum.')
    }

    def __init__(self, *args, **kwargs):
        super(LTIDCodeField, self).__init__(r'^\d{11}$', *args, **kwargs)

    def clean(self, value):
        super(LTIDCodeField, self).clean(value)

        if value in EMPTY_VALUES:
            return ''

        if not self.valid_checksum(value):
            raise ValidationError(self.error_messages['checksum'])
        return value

    def valid_checksum(self, value):
        first_sum = 0
        second_sum = 0

        for i in range(10):
            first_sum += int(value[i]) * (i % 9 + 1)
            second_sum += int(value[i]) * ((i + 2) % 9 + 1)

        k = first_sum % 11
        if k == 10:
            print(value)
            k = second_sum % 11
            k = 0 if k == 10 else k

        return True if k == int(value[-1]) else False

