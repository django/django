# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#
from __future__ import unicode_literals

DATE_FORMAT = r'j \d\e F \d\e Y'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = r'j \d\e F \d\e Y \a \l\a\s H:i'
YEAR_MONTH_FORMAT = r'F \d\e Y'
MONTH_DAY_FORMAT = r'j \d\e F'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'
FIRST_DAY_OF_WEEK = 1  # Monday: ISO 8601
DATE_INPUT_FORMATS = (
    '%d/%m/%Y', '%d/%m/%y',             # '25/10/2006', '25/10/06'
    '%Y%m%d',                           # '20061025'
)
DATETIME_INPUT_FORMATS = (
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M:%S.%f',
    '%d/%m/%Y %H:%M',
    '%d/%m/%y %H:%M:%S',
    '%d/%m/%y %H:%M:%S.%f',
    '%d/%m/%y %H:%M',
)
DECIMAL_SEPARATOR = '.'   # ',' is also official (less common): NOM-008-SCFI-2002
THOUSAND_SEPARATOR = '\xa0'  # non-breaking space
NUMBER_GROUPING = 3
