# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j F, Y'
TIME_FORMAT = 'g:i A'
# DATETIME_FORMAT =
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j F'
SHORT_DATE_FORMAT = 'j M, Y'
# SHORT_DATETIME_FORMAT =
FIRST_DAY_OF_WEEK = 6  # Saturday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    '%d/%m/%Y',  # 25/10/2016
    '%d/%m/%y',  # 25/10/16
    '%d-%m-%Y',  # 25-10-2016
    '%d-%m-%y',  # 25-10-16
]
TIME_INPUT_FORMATS = [
    '%H:%M:%S',  # 14:30:59
    '%H:%M',  # 14:30
]
DATETIME_INPUT_FORMATS = [
    '%d/%m/%Y %H:%M:%S',  # 25/10/2006 14:30:59
    '%d/%m/%Y %H:%M',  # 25/10/2006 14:30
]
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
# NUMBER_GROUPING =
