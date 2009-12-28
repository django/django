# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'd F Y' # 25 Ottobre 2006
TIME_FORMAT = 'H:i:s' # 14:30:59
DATETIME_FORMAT = 'w d F Y H:i:s' # Mercoledì 25 Ottobre 2006 14:30:59
YEAR_MONTH_FORMAT = 'F Y' # Ottobre 2006
MONTH_DAY_FORMAT = 'j/F' # 10/2006
SHORT_DATE_FORMAT = 'd/M/Y' # 25/12/2009
SHORT_DATETIME_FORMAT = 'd/M/Y H:i:s' # 25/10/2009 14:30:59
FIRST_DAY_OF_WEEK = 1 # Lunedì
DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%Y/%m/%d',  # '2008-10-25', '2008/10/25'
    '%d-%m-%Y', '%d/%m/%Y',  # '25-10-2006', '25/10/2006'
    '%d-%m-%y', '%d/%m/%y',  # '25-10-06', '25/10/06'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%d-%m-%Y %H:%M:%S',     # '25-10-2006 14:30:59'
    '%d-%m-%Y %H:%M',        # '25-10-2006 14:30'
    '%d-%m-%Y',              # '25-10-2006'
    '%d-%m-%y %H:%M:%S',     # '25-10-06 14:30:59'
    '%d-%m-%y %H:%M',        # '25-10-06 14:30'
    '%d-%m-%y',              # '25-10-06'
    '%d/%m/%Y %H:%M:%S',     # '25/10/2006 14:30:59'
    '%d/%m/%Y %H:%M',        # '25/10/2006 14:30'
    '%d/%m/%Y',              # '25/10/2006'
    '%d/%m/%y %H:%M:%S',     # '25/10/06 14:30:59'
    '%d/%m/%y %H:%M',        # '25/10/06 14:30'
    '%d/%m/%y',              # '25/10/06'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
