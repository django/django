# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j F Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'j F Y H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'j F Y'
SHORT_DATETIME_FORMAT = 'j F Y H:i'
FIRST_DAY_OF_WEEK = 0  # Sunday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    '%Y/%m/%d',  # '2006/10/25'
]
TIME_INPUT_FORMATS = [
    '%H:%M',     # '14:30
    '%H:%M:%S',  # '14:30:59'
]
DATETIME_INPUT_FORMATS = [
    '%Y/%m/%d %H:%M',     # '2006/10/25 14:30'
    '%Y/%m/%d %H:%M:%S',  # '2006/10/25 14:30:59'
]
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
