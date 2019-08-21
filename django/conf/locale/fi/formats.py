# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = 'j. E Y'
TIME_FORMAT = 'G.i'
DATETIME_FORMAT = r'j. E Y \k\e\l\l\o G.i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j. F'
SHORT_DATE_FORMAT = 'j.n.Y'
SHORT_DATETIME_FORMAT = 'j.n.Y G.i'
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    '%d.%m.%Y',  # '20.3.2014'
    '%d.%m.%y',  # '20.3.14'
]
DATETIME_INPUT_FORMATS = [
    '%d.%m.%Y %H.%M.%S',     # '20.3.2014 14.30.59'
    '%d.%m.%Y %H.%M.%S.%f',  # '20.3.2014 14.30.59.000200'
    '%d.%m.%Y %H.%M',        # '20.3.2014 14.30'
    '%d.%m.%Y',              # '20.3.2014'

    '%d.%m.%y %H.%M.%S',     # '20.3.14 14.30.59'
    '%d.%m.%y %H.%M.%S.%f',  # '20.3.14 14.30.59.000200'
    '%d.%m.%y %H.%M',        # '20.3.14 14.30'
    '%d.%m.%y',              # '20.3.14'
]
TIME_INPUT_FORMATS = [
    '%H.%M.%S',     # '14.30.59'
    '%H.%M.%S.%f',  # '14.30.59.000200'
    '%H.%M',        # '14.30'
]

DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '\xa0'  # Non-breaking space
NUMBER_GROUPING = 3
