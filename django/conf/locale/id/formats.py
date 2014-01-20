# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#
from __future__ import unicode_literals

# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j N Y'
DATETIME_FORMAT = "j N Y, G.i.s"
TIME_FORMAT = 'G.i.s'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'd-m-Y'
SHORT_DATETIME_FORMAT = 'd-m-Y G.i.s'
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = (
    '%d-%m-%y', '%d/%m/%y',             # '25-10-09', 25/10/09'
    '%d-%m-%Y', '%d/%m/%Y',             # '25-10-2009', 25/10/2009'
    '%d %b %Y',                         # '25 Oct 2006',
    '%d %B %Y',                         # '25 October 2006'
)

TIME_INPUT_FORMATS = (
    '%H.%M.%S',                         # '14.30.59'
    '%H.%M',                            # '14.30'
)

DATETIME_INPUT_FORMATS = (
    '%d-%m-%Y %H.%M.%S',                # '25-10-2009 14.30.59'
    '%d-%m-%Y %H.%M.%S.%f',             # '25-10-2009 14.30.59.000200'
    '%d-%m-%Y %H.%M',                   # '25-10-2009 14.30'
    '%d-%m-%Y',                         # '25-10-2009'
    '%d-%m-%y %H.%M.%S',                # '25-10-09' 14.30.59'
    '%d-%m-%y %H.%M.%S.%f',             # '25-10-09' 14.30.59.000200'
    '%d-%m-%y %H.%M',                   # '25-10-09' 14.30'
    '%d-%m-%y',                         # '25-10-09''
    '%m/%d/%y %H.%M.%S',                # '10/25/06 14.30.59'
    '%m/%d/%y %H.%M.%S.%f',             # '10/25/06 14.30.59.000200'
    '%m/%d/%y %H.%M',                   # '10/25/06 14.30'
    '%m/%d/%y',                         # '10/25/06'
    '%m/%d/%Y %H.%M.%S',                # '25/10/2009 14.30.59'
    '%m/%d/%Y %H.%M.%S.%f',             # '25/10/2009 14.30.59.000200'
    '%m/%d/%Y %H.%M',                   # '25/10/2009 14.30'
    '%m/%d/%Y',                         # '10/25/2009'
)

DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
