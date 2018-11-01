# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j M Y'                   # '25 Oct 2006'
TIME_FORMAT = 'P'                       # '2:30 p.m.'
DATETIME_FORMAT = 'j M Y, P'            # '25 Oct 2006, 2:30 p.m.'
YEAR_MONTH_FORMAT = 'F Y'               # 'October 2006'
MONTH_DAY_FORMAT = 'j F'                # '25 October'
SHORT_DATE_FORMAT = 'd/m/Y'             # '25/10/2006'
SHORT_DATETIME_FORMAT = 'd/m/Y P'       # '25/10/2006 2:30 p.m.'
FIRST_DAY_OF_WEEK = 0                   # Sunday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    '%d/%m/%Y', '%d/%m/%y',             # '25/10/2006', '25/10/06'
    # '%b %d %Y', '%b %d, %Y',          # 'Oct 25 2006', 'Oct 25, 2006'
    # '%d %b %Y', '%d %b, %Y',          # '25 Oct 2006', '25 Oct, 2006'
    # '%B %d %Y', '%B %d, %Y',          # 'October 25 2006', 'October 25, 2006'
    # '%d %B %Y', '%d %B, %Y',          # '25 October 2006', '25 October, 2006'
]
DATETIME_INPUT_FORMATS = [
    '%Y-%m-%d %H:%M:%S',                # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M:%S.%f',             # '2006-10-25 14:30:59.000200'
    '%Y-%m-%d %H:%M',                   # '2006-10-25 14:30'
    '%Y-%m-%d',                         # '2006-10-25'
    '%d/%m/%Y %H:%M:%S',                # '25/10/2006 14:30:59'
    '%d/%m/%Y %H:%M:%S.%f',             # '25/10/2006 14:30:59.000200'
    '%d/%m/%Y %H:%M',                   # '25/10/2006 14:30'
    '%d/%m/%Y',                         # '25/10/2006'
    '%d/%m/%y %H:%M:%S',                # '25/10/06 14:30:59'
    '%d/%m/%y %H:%M:%S.%f',             # '25/10/06 14:30:59.000200'
    '%d/%m/%y %H:%M',                   # '25/10/06 14:30'
    '%d/%m/%y',                         # '25/10/06'
]
DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3
