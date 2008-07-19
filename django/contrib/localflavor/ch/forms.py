"""
Swiss-specific Form helpers
"""

from django.forms import ValidationError
from django.forms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.encoding import smart_unicode
from django.utils.translation import ugettext_lazy as _
import re

id_re = re.compile(r"^(?P<idnumber>\w{8})(?P<pos9>(\d{1}|<))(?P<checksum>\d{1})$")
phone_digits_re = re.compile(r'^0([1-9]{1})\d{8}$')

class CHZipCodeField(RegexField):
    default_error_messages = {
        'invalid': _('Enter a zip code in the format XXXX.'),
    }

    def __init__(self, *args, **kwargs):
        super(CHZipCodeField, self).__init__(r'^\d{4}$',
        max_length=None, min_length=None, *args, **kwargs)

class CHPhoneNumberField(Field):
    """
    Validate local Swiss phone number (not international ones)
    The correct format is '0XX XXX XX XX'.
    '0XX.XXX.XX.XX' and '0XXXXXXXXX' validate but are corrected to
    '0XX XXX XX XX'.
    """
    default_error_messages = {
        'invalid': 'Phone numbers must be in 0XX XXX XX XX format.',
    }

    def clean(self, value):
        super(CHPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''
        value = re.sub('(\.|\s|/|-)', '', smart_unicode(value))
        m = phone_digits_re.search(value)
        if m:
            return u'%s %s %s %s' % (value[0:3], value[3:6], value[6:8], value[8:10])
        raise ValidationError(self.error_messages['invalid'])

class CHStateSelect(Select):
    """
    A Select widget that uses a list of CH states as its choices.
    """
    def __init__(self, attrs=None):
        from ch_states import STATE_CHOICES # relative import
        super(CHStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

class CHIdentityCardNumberField(Field):
    """
    A Swiss identity card number.

    Checks the following rules to determine whether the number is valid:

        * Conforms to the X1234567<0 or 1234567890 format.
        * Included checksums match calculated checksums

    Algorithm is documented at http://adi.kousz.ch/artikel/IDCHE.htm
    """
    default_error_messages = {
        'invalid': _('Enter a valid Swiss identity or passport card number in X1234567<0 or 1234567890 format.'),
    }

    def has_valid_checksum(self, number):
        given_number, given_checksum = number[:-1], number[-1]
        new_number = given_number
        calculated_checksum = 0
        fragment = ""
        parameter = 7

        first = str(number[:1])
        if first.isalpha():
            num = ord(first.upper()) - 65
            if num < 0 or num > 8:
                return False
            new_number = str(num) + new_number[1:]
            new_number = new_number[:8] + '0'

        if not new_number.isdigit():
            return False

        for i in range(len(new_number)):
          fragment = int(new_number[i])*parameter
          calculated_checksum += fragment

          if parameter == 1:
            parameter = 7
          elif parameter == 3:
            parameter = 1
          elif parameter ==7:
            parameter = 3

        return str(calculated_checksum)[-1] == given_checksum

    def clean(self, value):
        super(CHIdentityCardNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        match = re.match(id_re, value)
        if not match:
            raise ValidationError(self.error_messages['invalid'])

        idnumber, pos9, checksum = match.groupdict()['idnumber'], match.groupdict()['pos9'], match.groupdict()['checksum']

        if idnumber == '00000000' or \
           idnumber == 'A0000000':
            raise ValidationError(self.error_messages['invalid'])

        all_digits = "%s%s%s" % (idnumber, pos9, checksum)
        if not self.has_valid_checksum(all_digits):
            raise ValidationError(self.error_messages['invalid'])

        return u'%s%s%s' % (idnumber, pos9, checksum)

