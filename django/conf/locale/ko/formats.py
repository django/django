# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see http://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'Y년 n월 j일'
TIME_FORMAT = 'A g:i'
DATETIME_FORMAT = 'Y년 n월 j일 g:i A'
YEAR_MONTH_FORMAT = 'Y년 n월'
MONTH_DAY_FORMAT = 'n월 j일'
SHORT_DATE_FORMAT = 'Y-n-j.'
SHORT_DATETIME_FORMAT = 'Y-n-j H:i'
# FIRST_DAY_OF_WEEK =

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see http://docs.python.org/library/datetime.html#strftime-strptime-behavior
# Kept ISO formats as they are in first position
DATE_INPUT_FORMATS = [
    '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y',  # '2006-10-25', '10/25/2006', '10/25/06'
    # '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    # '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    # '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    # '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
    '%Y년 %m월 %d일',                   # '2006년 10월 25일', with localized suffix.
]
TIME_INPUT_FORMATS = [
    '%H:%M:%S',     # '14:30:59'
    '%H:%M:%S.%f',  # '14:30:59.000200'
    '%H:%M',        # '14:30'
    '%H시 %M분 %S초',   # '14시 30분 59초'
    '%H시 %M분',        # '14시 30분'
]
DATETIME_INPUT_FORMATS = [
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

    '%Y년 %m월 %d일 %H시 %M분 %S초',  # '2006년 10월 25일 14시 30분 59초'
    '%Y년 %m월 %d일 %H시 %M분',       # '2006년 10월 25일 14시 30분'
]

DECIMAL_SEPARATOR = '.'
THOUSAND_SEPARATOR = ','
NUMBER_GROUPING = 3
