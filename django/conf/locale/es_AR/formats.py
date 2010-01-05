# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'j \\de F \\de Y'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = 'j \\de F \\de Y \\a \\l\\a\s H:i'
YEAR_MONTH_FORMAT = 'F \\de Y'
MONTH_DAY_FORMAT = 'j \\de F'
SHORT_DATE_FORMAT = 'd/m/Y'
SHORT_DATETIME_FORMAT = 'd/m/Y H:i'
FIRST_DAY_OF_WEEK = 0 # 0: Sunday, 1: Monday
DATE_INPUT_FORMATS = (
    '%d/%m/%Y', # '31/12/2009'
    '%d/%m/%y', # '31/12/09'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S', # '14:30:59'
    '%H:%M',    # '14:30'
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
