"""
Kuwait-specific Form helpers
"""
import re
from datetime import date

from django.core.validators import EMPTY_VALUES
from django.forms import ValidationError
from django.forms.fields import Field, RegexField
from django.utils.translation import gettext as _

id_re = re.compile(r'^(?P<initial>\d{1})(?P<yy>\d\d)(?P<mm>\d\d)(?P<dd>\d\d)(?P<mid>\d{4})(?P<checksum>\d{1})')

class KWCivilIDNumberField(Field):
    """
    Kuwaiti Civil ID numbers are 12 digits, second to seventh digits
    represents the person's birthdate.

    Checks the following rules to determine the validty of the number:
        * The number consist of 12 digits.
        * The birthdate of the person is a valid date.
        * The calculated checksum equals to the last digit of the Civil ID.
    """
    default_error_messages = {
        'invalid': _('Enter a valid Kuwaiti Civil ID number'),
    }

    def has_valid_checksum(self, value):
        weight = (2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2)
        calculated_checksum = 0
        for i in range(11):
            calculated_checksum += int(value[i]) * weight[i]

        remainder = calculated_checksum % 11
        checkdigit = 11 - remainder
        if checkdigit != int(value[11]):
            return False
        return True

    def clean(self, value):
        super(KWCivilIDNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        if not re.match(r'^\d{12}$', value):
            raise ValidationError(self.error_messages['invalid'])

        match = re.match(id_re, value)

        if not match:
            raise ValidationError(self.error_messages['invalid'])

        gd = match.groupdict()

        try:
            d = date(int(gd['yy']), int(gd['mm']), int(gd['dd']))
        except ValueError:
            raise ValidationError(self.error_messages['invalid'])

        if not self.has_valid_checksum(value):
            raise ValidationError(self.error_messages['invalid'])

        return value
