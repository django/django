# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = r"Y\k\o N j\a"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = r"Y\k\o N j\a, H:i"
YEAR_MONTH_FORMAT = r"Y\k\o F"
MONTH_DAY_FORMAT = r"F\r\e\n j\a"
SHORT_DATE_FORMAT = "Y-m-d"
SHORT_DATETIME_FORMAT = "Y-m-d H:i"
FIRST_DAY_OF_WEEK = 1  # Astelehena

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
# DATE_INPUT_FORMATS =
# TIME_INPUT_FORMATS =
# DATETIME_INPUT_FORMATS =
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
