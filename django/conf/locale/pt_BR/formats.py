# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = r"j \d\e F \d\e Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = r"j \d\e F \d\e Y à\s H:i"
YEAR_MONTH_FORMAT = r"F \d\e Y"
MONTH_DAY_FORMAT = r"j \d\e F"
SHORT_DATE_FORMAT = "d/m/Y"
SHORT_DATETIME_FORMAT = "d/m/Y H:i"
FIRST_DAY_OF_WEEK = 0  # Sunday

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    "%d/%m/%Y",  # '25/10/2006'
    "%d/%m/%y",  # '25/10/06'
    # "%d de %b de %Y",  # '24 de Out de 2006'
    # "%d de %b, %Y",  # '25 Out, 2006'
    # "%d de %B de %Y",  # '25 de Outubro de 2006'
    # "%d de %B, %Y",  # '25 de Outubro, 2006'
]
DATETIME_INPUT_FORMATS = [
    "%d/%m/%Y %H:%M:%S",  # '25/10/2006 14:30:59'
    "%d/%m/%Y %H:%M:%S.%f",  # '25/10/2006 14:30:59.000200'
    "%d/%m/%Y %H:%M",  # '25/10/2006 14:30'
    "%d/%m/%y %H:%M:%S",  # '25/10/06 14:30:59'
    "%d/%m/%y %H:%M:%S.%f",  # '25/10/06 14:30:59.000200'
    "%d/%m/%y %H:%M",  # '25/10/06 14:30'
]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
