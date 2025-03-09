# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = r"j-E, Y-\y\i\l"
TIME_FORMAT = "G:i"
DATETIME_FORMAT = r"j-E, Y-\y\i\l G:i"
YEAR_MONTH_FORMAT = r"F Y-\y\i\l"
MONTH_DAY_FORMAT = "j-E"
SHORT_DATE_FORMAT = "d.m.Y"
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    "%d.%m.%Y",  # '25.10.2006'
    "%d-%B, %Y-yil",  # '25-Oktabr, 2006-yil'
]
DATETIME_INPUT_FORMATS = [
    "%d.%m.%Y %H:%M:%S",  # '25.10.2006 14:30:59'
    "%d.%m.%Y %H:%M:%S.%f",  # '25.10.2006 14:30:59.000200'
    "%d.%m.%Y %H:%M",  # '25.10.2006 14:30'
    "%d-%B, %Y-yil %H:%M:%S",  # '25-Oktabr, 2006-yil 14:30:59'
    "%d-%B, %Y-yil %H:%M:%S.%f",  # '25-Oktabr, 2006-yil 14:30:59.000200'
    "%d-%B, %Y-yil %H:%M",  # '25-Oktabr, 2006-yil 14:30'
]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "\xa0"  # non-breaking space
NUMBER_GROUPING = 3
