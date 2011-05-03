"""
South Africa-specific Form helpers
"""

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import CharField, RegexField
from django.utils.checksums import luhn
from django.utils.translation import gettext as _
import re
from datetime import date

id_re = re.compile(r'^(?P<yy>\d\d)(?P<mm>\d\d)(?P<dd>\d\d)(?P<mid>\d{4})(?P<end>\d{3})')

class ZAIDField(CharField):
    """A form field for South African ID numbers -- the checksum is validated
    using the Luhn checksum, and uses a simlistic (read: not entirely accurate)
    check for the birthdate
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid South African ID number'),
    }

    def clean(self, value):
        super(ZAIDField, self).clean(value)

        if value in EMPTY_VALUES:
            return u''

        # strip spaces and dashes
        value = value.strip().replace(' ', '').replace('-', '')

        match = re.match(id_re, value)

        if not match:
            raise ValidationError(self.error_messages['invalid'])

        g = match.groupdict()

        try:
            # The year 2000 is conveniently a leapyear.
            # This algorithm will break in xx00 years which aren't leap years
            # There is no way to guess the century of a ZA ID number
            d = date(int(g['yy']) + 2000, int(g['mm']), int(g['dd']))
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])

        if not luhn(value):
            raise ValidationError(self.error_messages['invalid'])

        return value

class ZAPostCodeField(RegexField):
    default_error_messages = {
        'invalid': _(u'Enter a valid South African postal code'),
    }

    def __init__(self, max_length=None, min_length=None, *args, **kwargs):
        super(ZAPostCodeField, self).__init__(r'^\d{4}$',
            max_length, min_length, *args, **kwargs)
