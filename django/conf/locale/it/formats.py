# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'd F Y' # 25 Ottobre 2006
TIME_FORMAT = 'H:i:s' # 14:30:59
DATETIME_FORMAT = 'l d F Y H:i:s' # Mercoledì 25 Ottobre 2006 14:30:59
YEAR_MONTH_FORMAT = 'F Y' # Ottobre 2006
MONTH_DAY_FORMAT = 'j/F' # 10/2006
SHORT_DATE_FORMAT = 'd/m/Y' # 25/12/2009
SHORT_DATETIME_FORMAT = 'd/m/Y H:i:s' # 25/10/2009 14:30:59
FIRST_DAY_OF_WEEK = 1 # Lunedì

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = (
    '%d/%m/%Y', '%Y/%m/%d',  # '25/10/2006', '2008/10/25'
    '%d-%m-%Y', '%Y-%m-%d',  # '25-10-2006', '2008-10-25'
    '%d-%m-%y', '%d/%m/%y',  # '25-10-06', '25/10/06'
)
DATETIME_INPUT_FORMATS = (
    '%d/%m/%Y %H:%M:%S',     # '25/10/2006 14:30:59'
    '%d/%m/%Y %H:%M',        # '25/10/2006 14:30'
    '%d/%m/%Y',              # '25/10/2006'
    '%d/%m/%y %H:%M:%S',     # '25/10/06 14:30:59'
    '%d/%m/%y %H:%M',        # '25/10/06 14:30'
    '%d/%m/%y',              # '25/10/06'
    '%Y-%m-%d %H:%M:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%d-%m-%Y %H:%M:%S',     # '25-10-2006 14:30:59'
    '%d-%m-%Y %H:%M',        # '25-10-2006 14:30'
    '%d-%m-%Y',              # '25-10-2006'
    '%d-%m-%y %H:%M:%S',     # '25-10-06 14:30:59'
    '%d-%m-%y %H:%M',        # '25-10-06 14:30'
    '%d-%m-%y',              # '25-10-06'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
