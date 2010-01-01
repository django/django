"""
ID-specific Form helpers
"""

import re
import time

from django.forms import ValidationError
from django.forms.fields import Field, Select, EMPTY_VALUES
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_unicode

postcode_re = re.compile(r'^[1-9]\d{4}$')
phone_re = re.compile(r'^(\+62|0)[2-9]\d{7,10}$')
plate_re = re.compile(r'^(?P<prefix>[A-Z]{1,2}) ' + \
            r'(?P<number>\d{1,5})( (?P<suffix>([A-Z]{1,3}|[1-9][0-9]{,2})))?$')
nik_re = re.compile(r'^\d{16}$')


class IDPostCodeField(Field):
    """
    An Indonesian post code field.

    http://id.wikipedia.org/wiki/Kode_pos
    """
    default_error_messages = {
        'invalid': _('Enter a valid post code'),
    }

    def clean(self, value):
        super(IDPostCodeField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        value = value.strip()
        if not postcode_re.search(value):
            raise ValidationError(self.error_messages['invalid'])

        if int(value) < 10110:
            raise ValidationError(self.error_messages['invalid'])

        # 1xxx0
        if value[0] == '1' and value[4] != '0':
            raise ValidationError(self.error_messages['invalid'])

        return u'%s' % (value, )


class IDProvinceSelect(Select):
    """
    A Select widget that uses a list of provinces of Indonesia as its
    choices.
    """

    def __init__(self, attrs=None):
        from id_choices import PROVINCE_CHOICES
        super(IDProvinceSelect, self).__init__(attrs, choices=PROVINCE_CHOICES)


class IDPhoneNumberField(Field):
    """
    An Indonesian telephone number field.

    http://id.wikipedia.org/wiki/Daftar_kode_telepon_di_Indonesia
    """
    default_error_messages = {
        'invalid': _('Enter a valid phone number'),
    }

    def clean(self, value):
        super(IDPhoneNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        phone_number = re.sub(r'[\-\s\(\)]', '', smart_unicode(value))

        if phone_re.search(phone_number):
            return smart_unicode(value)

        raise ValidationError(self.error_messages['invalid'])


class IDLicensePlatePrefixSelect(Select):
    """
    A Select widget that uses a list of vehicle license plate prefix code
    of Indonesia as its choices.

    http://id.wikipedia.org/wiki/Tanda_Nomor_Kendaraan_Bermotor
    """

    def __init__(self, attrs=None):
        from id_choices import LICENSE_PLATE_PREFIX_CHOICES
        super(IDLicensePlatePrefixSelect, self).__init__(attrs,
            choices=LICENSE_PLATE_PREFIX_CHOICES)


class IDLicensePlateField(Field):
    """
    An Indonesian vehicle license plate field.

    http://id.wikipedia.org/wiki/Tanda_Nomor_Kendaraan_Bermotor

    Plus: "B 12345 12"
    """
    default_error_messages = {
        'invalid': _('Enter a valid vehicle license plate number'),
    }

    def clean(self, value):
        super(IDLicensePlateField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        plate_number = re.sub(r'\s+', ' ',
            smart_unicode(value.strip())).upper()

        matches = plate_re.search(plate_number)
        if matches is None:
            raise ValidationError(self.error_messages['invalid'])

        # Make sure prefix is in the list of known codes.
        from id_choices import LICENSE_PLATE_PREFIX_CHOICES
        prefix = matches.group('prefix')
        if prefix not in [choice[0] for choice in LICENSE_PLATE_PREFIX_CHOICES]:
            raise ValidationError(self.error_messages['invalid'])

        # Only Jakarta (prefix B) can have 3 letter suffix.
        suffix = matches.group('suffix')
        if suffix is not None and len(suffix) == 3 and prefix != 'B':
            raise ValidationError(self.error_messages['invalid'])

        # RI plates don't have suffix.
        if prefix == 'RI' and suffix is not None and suffix != '':
            raise ValidationError(self.error_messages['invalid'])

        # Number can't be zero.
        number = matches.group('number')
        if number == '0':
            raise ValidationError(self.error_messages['invalid'])

        # CD, CC and B 12345 12
        if len(number) == 5 or prefix in ('CD', 'CC'):
            # suffix must be numeric and non-empty
            if re.match(r'^\d+$', suffix) is None:
                raise ValidationError(self.error_messages['invalid'])

            # Known codes range is 12-124
            if prefix in ('CD', 'CC') and not (12 <= int(number) <= 124):
                raise ValidationError(self.error_messages['invalid'])
            if len(number) == 5 and not (12 <= int(suffix) <= 124):
                raise ValidationError(self.error_messages['invalid'])
        else:
            # suffix must be non-numeric
            if suffix is not None and re.match(r'^[A-Z]{,3}$', suffix) is None:
                raise ValidationError(self.error_messages['invalid'])

        return plate_number


class IDNationalIdentityNumberField(Field):
    """
    An Indonesian national identity number (NIK/KTP#) field.

    http://id.wikipedia.org/wiki/Nomor_Induk_Kependudukan

    xx.xxxx.ddmmyy.xxxx - 16 digits (excl. dots)
    """
    default_error_messages = {
        'invalid': _('Enter a valid NIK/KTP number'),
    }

    def clean(self, value):
        super(IDNationalIdentityNumberField, self).clean(value)
        if value in EMPTY_VALUES:
            return u''

        value = re.sub(r'[\s.]', '', smart_unicode(value))

        if not nik_re.search(value):
            raise ValidationError(self.error_messages['invalid'])

        if int(value) == 0:
            raise ValidationError(self.error_messages['invalid'])

        def valid_nik_date(year, month, day):
            try:
                t1 = (int(year), int(month), int(day), 0, 0, 0, 0, 0, -1)
                d = time.mktime(t1)
                t2 = time.localtime(d)
                if t1[:3] != t2[:3]:
                    return False
                else:
                    return True
            except (OverflowError, ValueError):
                return False

        year = int(value[10:12])
        month = int(value[8:10])
        day = int(value[6:8])
        current_year = time.localtime().tm_year
        if year < int(str(current_year)[-2:]):
            if not valid_nik_date(2000 + int(year), month, day):
                raise ValidationError(self.error_messages['invalid'])
        elif not valid_nik_date(1900 + int(year), month, day):
            raise ValidationError(self.error_messages['invalid'])

        if value[:6] == '000000' or value[12:] == '0000':
            raise ValidationError(self.error_messages['invalid'])

        return '%s.%s.%s.%s' % (value[:2], value[2:6], value[6:12], value[12:])
