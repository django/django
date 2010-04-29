# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'N j, Y'                  # 'Oct. 25, 2006'
TIME_FORMAT = 'P'                       # '2:30 pm'
DATETIME_FORMAT = 'N j, Y, P'           # 'Oct. 25, 2006, 2:30 pm'
YEAR_MONTH_FORMAT = 'F Y'               # 'October 2006'
MONTH_DAY_FORMAT = 'F j'                # 'October 25'
SHORT_DATE_FORMAT = 'd/m/Y'             # '25/10/2006'
SHORT_DATETIME_FORMAT = 'd/m/Y P'       # '25/10/2006 2:30 pm'
FIRST_DAY_OF_WEEK = 0                   # Sunday
DATE_INPUT_FORMATS = (
    '%d/%m/%Y', '%d/%m/%y',             # '25/10/2006', '25/10/06'
    '%Y-%m-%d',                         # '2006-10-25'
    # '%b %d %Y', '%b %d, %Y',          # 'Oct 25 2006', 'Oct 25, 2006'
    # '%d %b %Y', '%d %b, %Y',          # '25 Oct 2006', '25 Oct, 2006'
    # '%B %d %Y', '%B %d, %Y',          # 'October 25 2006', 'October 25, 2006'
    # '%d %B %Y', '%d %B, %Y',          # '25 October 2006', '25 October, 2006'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',                         # '14:30:59'
    '%H:%M',                            # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',                # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',                   # '2006-10-25 14:30'
    '%Y-%m-%d',                         # '2006-10-25'
    '%d/%m/%Y %H:%M:%S',                # '25/10/2006 14:30:59'
    '%d/%m/%Y %H:%M',                   # '25/10/2006 14:30'
    '%d/%m/%Y',                         # '25/10/2006'
    '%d/%m/%y %H:%M:%S',                # '25/10/06 14:30:59'
    '%d/%m/%y %H:%M',                   # '25/10/06 14:30'
    '%d/%m/%y',                         # '25/10/06'
)
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3

