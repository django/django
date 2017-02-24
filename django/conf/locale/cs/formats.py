# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j. E Y'
TIME_FORMAT = 'G:i'
DATETIME_FORMAT = 'j. E Y G:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j. F'
SHORT_DATE_FORMAT = 'd.m.Y'
SHORT_DATETIME_FORMAT = 'd.m.Y G:i'
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    '%d.%m.%Y', '%d.%m.%y',     # '05.01.2006', '05.01.06'
    '%d. %m. %Y', '%d. %m. %y',  # '5. 1. 2006', '5. 1. 06'
    # '%d. %B %Y', '%d. %b. %Y',  # '25. October 2006', '25. Oct. 2006'
]
# Kept ISO formats as one is in first position
TIME_INPUT_FORMATS = [
    '%H:%M:%S',  # '04:30:59'
    '%H.%M',    # '04.30'
    '%H:%M',    # '04:30'
]
DATETIME_INPUT_FORMATS = [
    '%d.%m.%Y %H:%M:%S',    # '05.01.2006 04:30:59'
    '%d.%m.%Y %H:%M:%S.%f',  # '05.01.2006 04:30:59.000200'
    '%d.%m.%Y %H.%M',       # '05.01.2006 04.30'
    '%d.%m.%Y %H:%M',       # '05.01.2006 04:30'
    '%d.%m.%Y',             # '05.01.2006'
    '%d. %m. %Y %H:%M:%S',  # '05. 01. 2006 04:30:59'
    '%d. %m. %Y %H:%M:%S.%f',  # '05. 01. 2006 04:30:59.000200'
    '%d. %m. %Y %H.%M',     # '05. 01. 2006 04.30'
    '%d. %m. %Y %H:%M',     # '05. 01. 2006 04:30'
    '%d. %m. %Y',           # '05. 01. 2006'
    '%Y-%m-%d %H.%M',       # '2006-01-05 04.30'
]
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '\xa0'  # non-breaking space
NUMBER_GROUPING = 3
