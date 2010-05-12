# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = r'Y. \g\a\d\a j. F'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = r'Y. \g\a\d\a j. F, H:i:s'
YEAR_MONTH_FORMAT = r'Y. \g. F'
MONTH_DAY_FORMAT = 'j. F'
SHORT_DATE_FORMAT = r'j.m.Y'
SHORT_DATETIME_FORMAT = 'j.m.Y H:i:s'
FIRST_DAY_OF_WEEK = 1 #Monday
DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%d.%m.%Y', '%d.%m.%y', # '2006-10-25', '25.10.2006', '25.10.06'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',     # '14:30'
    '%H.%M.%S', # '14.30.59'
    '%H.%M', # '14.30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%d.%m.%Y %H:%M:%S',     # '25.10.2006 14:30:59'
    '%d.%m.%Y %H:%M',        # '25.10.2006 14:30'
    '%d.%m.%Y',              # '25.10.2006'
    '%d.%m.%y %H:%M:%S',     # '25.10.06 14:30:59'
    '%d.%m.%y %H:%M',        # '25.10.06 14:30'
    '%d.%m.%y %H.%M.%S',     # '25.10.06 14.30.59'
    '%d.%m.%y %H.%M',        # '25.10.06 14.30'
    '%d.%m.%y',              # '25.10.06'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = ' '
NUMBER_GROUPING = 3
