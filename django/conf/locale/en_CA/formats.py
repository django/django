# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date

DATE_FORMAT = "j M Y"  # 25 Oct 2006
TIME_FORMAT = "P"  # 2:30 p.m.
DATETIME_FORMAT = "j M Y, P"  # 25 Oct 2006, 2:30 p.m.
YEAR_MONTH_FORMAT = "F Y"  # October 2006
MONTH_DAY_FORMAT = "j F"  # 25 October
SHORT_DATE_FORMAT = "Y-m-d"
SHORT_DATETIME_FORMAT = "Y-m-d P"
FIRST_DAY_OF_WEEK = 0  # Sunday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    "%Y-%m-%d",  # '2006-05-15'
    "%y-%m-%d",  # '06-05-15'
]
DATETIME_INPUT_FORMATS = [
    "%Y-%m-%d %H:%M:%S",  # '2006-05-15 14:30:57'
    "%y-%m-%d %H:%M:%S",  # '06-05-15 14:30:57'
    "%Y-%m-%d %H:%M:%S.%f",  # '2006-05-15 14:30:57.000200'
    "%y-%m-%d %H:%M:%S.%f",  # '06-05-15 14:30:57.000200'
    "%Y-%m-%d %H:%M",  # '2006-05-15 14:30'
    "%y-%m-%d %H:%M",  # '06-05-15 14:30'
]
DECIMAL_SEPARATOR = "."
THOUSAND_SEPARATOR = "\xa0"  # non-breaking space
NUMBER_GROUPING = 3
