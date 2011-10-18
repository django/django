# -*- coding: utf-8 -*-

"""
Chinese-specific form helpers
"""
from __future__ import absolute_import

import re

from django.contrib.localflavor.cn.cn_provinces import CN_PROVINCE_CHOICES
from django.forms import ValidationError
from django.forms.fields import CharField, RegexField, Select
from django.utils.translation import ugettext_lazy as _


__all__ = (
    'CNProvinceSelect',
    'CNPostCodeField',
    'CNIDCardField',
    'CNPhoneNumberField',
    'CNCellNumberField',
)


ID_CARD_RE = r'^\d{15}(\d{2}[0-9xX])?$'
POST_CODE_RE = r'^\d{6}$'
PHONE_RE = r'^\d{3,4}-\d{7,8}(-\d+)?$'
CELL_RE = r'^1[358]\d{9}$'

# Valid location code used in id card checking algorithm
CN_LOCATION_CODES = (
     11,  # Beijing
     12,  # Tianjin
     13,  # Hebei
     14,  # Shanxi
     15,  # Nei Mongol
     21,  # Liaoning
     22,  # Jilin
     23,  # Heilongjiang
     31,  # Shanghai
     32,  # Jiangsu
     33,  # Zhejiang
     34,  # Anhui
     35,  # Fujian
     36,  # Jiangxi
     37,  # Shandong
     41,  # Henan
     42,  # Hubei
     43,  # Hunan
     44,  # Guangdong
     45,  # Guangxi
     46,  # Hainan
     50,  # Chongqing
     51,  # Sichuan
     52,  # Guizhou
     53,  # Yunnan
     54,  # Xizang
     61,  # Shaanxi
     62,  # Gansu
     63,  # Qinghai
     64,  # Ningxia
     65,  # Xinjiang
     71,  # Taiwan
     81,  # Hong Kong
     91,  # Macao
)

class CNProvinceSelect(Select):
    """
    A select widget with list of Chinese provinces as choices.
    """
    def __init__(self, attrs=None):
        super(CNProvinceSelect, self).__init__(
            attrs, choices=CN_PROVINCE_CHOICES,
        )


class CNPostCodeField(RegexField):
    """
    A form field that validates as Chinese post code.
    Valid code is XXXXXX where X is digit.
    """
    default_error_messages = {
        'invalid': _(u'Enter a post code in the format XXXXXX.'),
    }

    def __init__(self, *args, **kwargs):
        super(CNPostCodeField, self).__init__(POST_CODE_RE, *args, **kwargs)


class CNIDCardField(CharField):
    """
    A form field that validates as Chinese Identification Card Number.

    This field would check the following restrictions:
        * the length could only be 15 or 18.
        * if the length is 18, the last digit could be x or X.
        * has a valid checksum.(length 18 only)
        * has a valid birthdate.
        * has a valid location.

    The checksum algorithm is described in GB11643-1999.
    """
    default_error_messages = {
        'invalid': _(u'ID Card Number consists of 15 or 18 digits.'),
        'checksum': _(u'Invalid ID Card Number: Wrong checksum'),
        'birthday': _(u'Invalid ID Card Number: Wrong birthdate'),
        'location': _(u'Invalid ID Card Number: Wrong location code'),
    }

    def __init__(self, max_length=18, min_length=15, *args, **kwargs):
        super(CNIDCardField, self).__init__(max_length, min_length, *args,
                                         **kwargs)

    def clean(self, value):
        """
        Check whether the input is a valid ID Card Number.
        """
        # Check the length of the ID card number.
        super(CNIDCardField, self).clean(value)
        if not value:
            return u""
        # Check whether this ID card number has valid format
        if not re.match(ID_CARD_RE, value):
            raise ValidationError(self.error_messages['invalid'])
        # Check the birthday of the ID card number.
        if not self.has_valid_birthday(value):
            raise ValidationError(self.error_messages['birthday'])
        # Check the location of the ID card number.
        if not self.has_valid_location(value):
            raise ValidationError(self.error_messages['location'])
        # Check the checksum of the ID card number.
        value = value.upper()
        if not self.has_valid_checksum(value):
            raise ValidationError(self.error_messages['checksum'])
        return u'%s' % value

    def has_valid_birthday(self, value):
        """
        This function would grab the birthdate from the ID card number and test
        whether it is a valid date.
        """
        from datetime import datetime
        if len(value) == 15:
            # 1st generation ID card
            time_string = value[6:12]
            format_string = "%y%m%d"
        else:
            # 2nd generation ID card
            time_string = value[6:14]
            format_string = "%Y%m%d"
        try:
            datetime.strptime(time_string, format_string)
            return True
        except ValueError:
            # invalid date
            return False

    def has_valid_location(self, value):
        """
        This method checks if the first two digits in the ID Card are valid.
        """
        return int(value[:2]) in CN_LOCATION_CODES

    def has_valid_checksum(self, value):
        """
        This method checks if the last letter/digit in value is valid
        according to the algorithm the ID Card follows.
        """
        # If the length of the number is not 18, then the number is a 1st
        # generation ID card number, and there is no checksum to be checked.
        if len(value) != 18:
            return True
        checksum_index = sum(
            map(
                lambda a,b:a*(ord(b)-ord('0')),
                (7,9,10,5,8,4,2,1,6,3,7,9,10,5,8,4,2),
                value[:17],
            ),
        ) % 11
        return '10X98765432'[checksum_index] == value[-1]


class CNPhoneNumberField(RegexField):
    """
    A form field that validates as Chinese phone number
    A valid phone number could be like:
        010-55555555
    Considering there might be extension phone numbers, so this could also be:
        010-55555555-35
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid phone number.'),
    }

    def __init__(self, *args, **kwargs):
        super(CNPhoneNumberField, self).__init__(PHONE_RE, *args, **kwargs)


class CNCellNumberField(RegexField):
    """
    A form field that validates as Chinese cell number
    A valid cell number could be like:
        13012345678
    We used a rough rule here, the first digit should be 1, the second could be
    3, 5 and 8, the rest could be what so ever.
    The length of the cell number should be 11.
    """
    default_error_messages = {
        'invalid': _(u'Enter a valid cell number.'),
    }

    def __init__(self, *args, **kwargs):
        super(CNCellNumberField, self).__init__(CELL_RE, *args, **kwargs)
