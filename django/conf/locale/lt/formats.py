# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = r'Y \m. E j \d.'          # '2006 m. spalio 25 d.'
TIME_FORMAT = 'H:i'                     # '14:30'
DATETIME_FORMAT = r'Y \m. E j \d. H:i'  # '2006 m. spalio 25 d. 14:30'
YEAR_MONTH_FORMAT = r'Y F'              # '2006 spalis'
MONTH_DAY_FORMAT = r'E j'               # 'spalio 25'
SHORT_DATE_FORMAT = 'Y-m-d'             # '2006-10-25'
SHORT_DATETIME_FORMAT = 'Y-m-d H:i'     # '2006-10-25 14:30'
FIRST_DAY_OF_WEEK = 1                   # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = (
    '%Y-%m-%d',                         # '2006-10-25'
    '%Y %m %d',                         # '2006 10 25'
    '%Y.%m.%d',                         # '2006.10.25'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',                         # '14:30:59'
    '%H:%M',                            # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%M:%S',                # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',                   # '2006-10-25 14:30'
    '%Y-%m-%d',                         # '2006-10-25'
    '%Y %m %d %H:%M:%S',                # '2006 10 25 14:30:59'
    '%Y %m %d %H:%M',                   # '2006 10 25 14:30'
    '%Y %m %d',                         # '2006 10 25'
    '%Y.%m.%d %H:%M:%S',                # '2006.10.25 14:30:59'
    '%Y.%m.%d %H:%M',                   # '2006.10.25 14:30'
    '%Y.%m.%d',                         # '2006.10.25'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = ' '
# NUMBER_GROUPING = 
