# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j F Y'
TIME_FORMAT = 'H:i:s'
DATETIME_FORMAT = 'j F Y H:i:s'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'j N Y'
SHORT_DATETIME_FORMAT = 'j N Y H:i:s'
FIRST_DAY_OF_WEEK = 1 # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = (
    '%d/%m/%Y', '%d/%m/%y', # '25/10/2006', '25/10/06'
    '%d.%m.%Y', '%d.%m.%y', # Swiss (fr_CH), '25.10.2006', '25.10.06'
    '%Y-%m-%d', '%y-%m-%d', # '2006-10-25', '06-10-25'
    # '%d %B %Y', '%d %b %Y', # '25 octobre 2006', '25 oct. 2006'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S', # '14:30:59'
    '%H:%M',    # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%d/%m/%Y %H:%M:%S',    # '25/10/2006 14:30:59'
    '%d/%m/%Y %H:%M',       # '25/10/2006 14:30'
    '%d/%m/%Y',             # '25/10/2006'
    '%d.%m.%Y %H:%M:%S',    # Swiss (fr_CH), '25.10.2006 14:30:59'
    '%d.%m.%Y %H:%M',       # Swiss (fr_CH), '25.10.2006 14:30'
    '%d.%m.%Y',             # Swiss (fr_CH), '25.10.2006'
    '%Y-%m-%d %H:%M:%S',    # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',       # '2006-10-25 14:30'
    '%Y-%m-%d',             # '2006-10-25'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = u'\xa0' # non-breaking space
NUMBER_GROUPING = 3
