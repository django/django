# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = "j. F Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = "j. F Y H:i"
YEAR_MONTH_FORMAT = "F Y"
MONTH_DAY_FORMAT = "j. F"
SHORT_DATE_FORMAT = "d.m.Y"
SHORT_DATETIME_FORMAT = "d.m.Y H:i"
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
# Kept ISO formats as they are in first position
DATE_INPUT_FORMATS = [
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d.%m.%y",  # '2006-10-25', '25.10.2006', '25.10.06'
    # '%d. %b %Y', '%d %b %Y',            # '25. okt 2006', '25 okt 2006'
    # '%d. %b. %Y', '%d %b. %Y',          # '25. okt. 2006', '25 okt. 2006'
    # '%d. %B %Y', '%d %B %Y',            # '25. oktober 2006', '25 oktober 2006'
]
DATETIME_INPUT_FORMATS = [
    "%Y-%m-%d %H:%M:%S",  # '2006-10-25 14:30:59'
    "%Y-%m-%d %H:%M:%S.%f",  # '2006-10-25 14:30:59.000200'
    "%Y-%m-%d %H:%M",  # '2006-10-25 14:30'
    "%d.%m.%Y %H:%M:%S",  # '25.10.2006 14:30:59'
    "%d.%m.%Y %H:%M:%S.%f",  # '25.10.2006 14:30:59.000200'
    "%d.%m.%Y %H:%M",  # '25.10.2006 14:30'
    "%d.%m.%y %H:%M:%S",  # '25.10.06 14:30:59'
    "%d.%m.%y %H:%M:%S.%f",  # '25.10.06 14:30:59.000200'
    "%d.%m.%y %H:%M",  # '25.10.06 14:30'
]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "\xa0"  # non-breaking space
NUMBER_GROUPING = 3
