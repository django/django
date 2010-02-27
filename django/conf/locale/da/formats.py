# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'j. F Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'j. F Y H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j. F'
SHORT_DATE_FORMAT = 'd.m.Y'
SHORT_DATETIME_FORMAT = 'd.m.Y H:i'
FIRST_DAY_OF_WEEK = 1
DATE_INPUT_FORMATS = (
    '%d.%m.%Y',                         # '25.10.2006'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',                         # '14:30:59'
    '%H:%M',                            # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%d.%m.%Y %H:%M:%S',                # '25.10.2006 14:30:59'
    '%d.%m.%Y %H:%M',                   # '25.10.2006 14:30'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
