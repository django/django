# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'j F Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'j F Y H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'Y-m-d'
SHORT_DATETIME_FORMAT = 'Y-m-d H:i'
FIRST_DAY_OF_WEEK = 1
DATE_INPUT_FORMATS = (
    '%Y-%m-%d',                     # '2006-10-25'
)
TIME_INPUT_FORMATS = (
    '%H:%i',                        # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%i',               # '2006-10-25 14:30'
)
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ' '
NUMBER_GROUPING = 3
