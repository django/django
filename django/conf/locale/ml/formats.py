# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#
from __future__ import unicode_literals

# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'N j, Y'
TIME_FORMAT = 'P'
DATETIME_FORMAT = 'N j, Y, P'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'F j'
SHORT_DATE_FORMAT = 'm/d/Y'
SHORT_DATETIME_FORMAT = 'm/d/Y P'
FIRST_DAY_OF_WEEK = 0 # Sunday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
# Kept ISO formats as they are in first position
DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', # '2006-10-25', '10/25/2006', '10/25/06'
    # '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    # '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    # '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    # '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M:%S.%f',  # '2006-10-25 14:30:59.000200'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%m/%d/%Y %H:%M:%S',     # '10/25/2006 14:30:59'
    '%m/%d/%Y %H:%M:%S.%f',  # '10/25/2006 14:30:59.000200'
    '%m/%d/%Y %H:%M',        # '10/25/2006 14:30'
    '%m/%d/%Y',              # '10/25/2006'
    '%m/%d/%y %H:%M:%S',     # '10/25/06 14:30:59'
    '%m/%d/%y %H:%M:%S.%f',  # '10/25/06 14:30:59.000200'
    '%m/%d/%y %H:%M',        # '10/25/06 14:30'
    '%m/%d/%y',              # '10/25/06'
)
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3

