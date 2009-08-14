# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'j \de F \de Y'
TIME_FORMAT = 'G:i:s'
DATETIME_FORMAT = 'j \de F \de Y \\a \le\s G:i'
YEAR_MONTH_FORMAT = 'F \de\l Y'
MONTH_DAY_FORMAT = 'j \de F'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y G:i'
FIRST_DAY_OF_WEEK = 1 # Monday
DATE_INPUT_FORMATS = (
    # '31/12/2009', '31/12/09'
    '%d/%m/%Y', '%d/%m/%y'
)
TIME_INPUT_FORMATS = (
    # '14:30:59', '14:30'
    '%H:%M:%S', '%H:%M'
)
DATETIME_INPUT_FORMATS = (
    '%d/%m/%Y %H:%M:%S',
    '%d/%m/%Y %H:%M',
    '%d/%m/%y %H:%M:%S',
    '%d/%m/%y %H:%M',
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3

