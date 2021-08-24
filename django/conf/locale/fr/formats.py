# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = "j F Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = "j F Y H:i"
YEAR_MONTH_FORMAT = "F Y"
MONTH_DAY_FORMAT = "j F"
SHORT_DATE_FORMAT = "j N Y"
SHORT_DATETIME_FORMAT = "j N Y H:i"
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    "%d/%m/%Y",
    "%d/%m/%y",  # '25/10/2006', '25/10/06'
    "%d.%m.%Y",
    "%d.%m.%y",  # Swiss [fr_CH), '25.10.2006', '25.10.06'
    # '%d %B %Y', '%d %b %Y', # '25 octobre 2006', '25 oct. 2006'
]
DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M:%S",  # '25/10/2006 14:30:59'
    "%d/%m/%Y %H:%M:%S.%f",  # '25/10/2006 14:30:59.000200'
    "%d/%m/%Y %H:%M",  # '25/10/2006 14:30'
    "%d.%m.%Y %H:%M:%S",  # Swiss [fr_CH), '25.10.2006 14:30:59'
    "%d.%m.%Y %H:%M:%S.%f",  # Swiss (fr_CH), '25.10.2006 14:30:59.000200'
    "%d.%m.%Y %H:%M",  # Swiss (fr_CH), '25.10.2006 14:30'
]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "\xa0"  # non-breaking space
NUMBER_GROUPING = 3
