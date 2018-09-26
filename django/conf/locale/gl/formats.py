# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = r'j \d\e F \d\e Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = r'j \d\e F \d\e Y \á\s H:i'
YEAR_MONTH_FORMAT = r'F \d\e Y'
MONTH_DAY_FORMAT = r'j \d\e F'
SHORT_DATE_FORMAT = 'd-m-Y'
SHORT_DATETIME_FORMAT = 'd-m-Y, H:i'
FIRST_DAY_OF_WEEK = 1  # Monday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
# DATE_INPUT_FORMATS =
# TIME_INPUT_FORMATS =
# DATETIME_INPUT_FORMATS =
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
# NUMBER_GROUPING =
