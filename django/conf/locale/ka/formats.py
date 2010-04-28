# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'l, j F, Y'
TIME_FORMAT = 'h:i:s a'
DATETIME_FORMAT = 'j F, Y h:i:s a'
YEAR_MONTH_FORMAT = 'F, Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'j.M.Y'
SHORT_DATETIME_FORMAT = 'j.M.Y H:i:s'
FIRST_DAY_OF_WEEK = 1 # (Monday)
DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y',     # '2006-10-25', '10/25/2006', '10/25/06'
    # '%d %b %Y', '%d %b, %Y', '%d %b. %Y',   # '25 Oct 2006', '25 Oct, 2006', '25 Oct. 2006'
    # '%d %B %Y', '%d %B, %Y',                # '25 October 2006', '25 October, 2006'
    # '%d.%m.%Y', '%d.%m.%y',                 # '25.10.2006', '25.10.06'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%d.%m.%Y %H:%M:%S',     # '25.10.2006 14:30:59'
    '%d.%m.%Y %H:%M',        # '25.10.2006 14:30'
    '%d.%m.%Y',              # '25.10.2006'
    '%d.%m.%y %H:%M:%S',     # '25.10.06 14:30:59'
    '%d.%m.%y %H:%M',        # '25.10.06 14:30'
    '%d.%m.%y',              # '25.10.06'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = " "
NUMBER_GROUPING = 3
