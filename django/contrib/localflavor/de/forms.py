"""
DE-specific Form helpers
"""

from django.newforms import ValidationError
from django.newforms.fields import Field, RegexField, Select, EMPTY_VALUES
from django.utils.translation import gettext
import re

id_re = re.compile(r"^(?P<residence>\d{10})(?P<origin>\w{1,3})[-\ ]?(?P<birthday>\d{7})[-\ ]?(?P<validity>\d{7})[-\ ]?(?P<checksum>\d{1})$")

class DEZipCodeField(RegexField):
    def __init__(self, *args, **kwargs):
        super(DEZipCodeField, self).__init__(r'^\d{5}$',
            max_length=None, min_length=None,
            error_message=gettext(u'Enter a zip code in the format XXXXX.'),
            *args, **kwargs)

class DEStateSelect(Select):
    """
    A Select widget that uses a list of DE states as its choices.
    """
    def __init__(self, attrs=None):
        from de_states import STATE_CHOICES # relative import
        super(DEStateSelect, self).__init__(attrs, choices=STATE_CHOICES)

class DEIdentityCardNumberField(Field):
    """
    A German identity card number.

    Checks the following rules to determine whether the number is valid:

        * Conforms to the XXXXXXXXXXX-XXXXXXX-XXXXXXX-X format.
        * No group consists entirely of zeroes.
        * Included checksums match calculated checksums

    Algorithm is documented at http://de.wikipedia.org/wiki/Personalausweis
    """
    def has_valid_checksum(self, number):
        given_number, given_checksum = number[:-1], number[-1]
        calculated_checksum = 0
        fragment = ""
        parameter = 7

        for i in range(len(given_number)):
            fragment = str(int(given_number[i]) * parameter)
            if fragment.isalnum():
                calculated_checksum += int(fragment[-1])
            if parameter == 1:
                parameter = 7
            elif parameter == 3:
                parameter = 1
            elif parameter ==7:
                parameter = 3

        return str(calculated_checksum)[-1] == given_checksum

    def clean(self, value):
        super(DEIdentityCardNumberField, self).clean(value)
        error_msg = gettext(u'Enter a valid German identity card number in XXXXXXXXXXX-XXXXXXX-XXXXXXX-X format.')
        if value in EMPTY_VALUES:
            return u''
        match = re.match(id_re, value)
        if not match:
            raise ValidationError(error_msg)

        gd = match.groupdict()
        residence, origin = gd['residence'], gd['origin']
        birthday, validity, checksum = gd['birthday'], gd['validity'], gd['checksum']

        if residence == '0000000000' or birthday == '0000000' or validity == '0000000':
            raise ValidationError(error_msg)

        all_digits = "%s%s%s%s" % (residence, birthday, validity, checksum)
        if not self.has_valid_checksum(residence) or not self.has_valid_checksum(birthday) or \
            not self.has_valid_checksum(validity) or not self.has_valid_checksum(all_digits):
                raise ValidationError(error_msg)

        return u'%s%s-%s-%s-%s' % (residence, origin, birthday, validity, checksum)
