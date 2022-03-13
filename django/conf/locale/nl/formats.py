# This file is distributed under the same license as the Django package.
#
# The *_FORMAT strings use the Django date format syntax,
# see https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
DATE_FORMAT = "j F Y"  # '20 januari 2009'
TIME_FORMAT = "H:i"  # '15:23'
DATETIME_FORMAT = "j F Y H:i"  # '20 januari 2009 15:23'
YEAR_MONTH_FORMAT = "F Y"  # 'januari 2009'
MONTH_DAY_FORMAT = "j F"  # '20 januari'
SHORT_DATE_FORMAT = "j-n-Y"  # '20-1-2009'
SHORT_DATETIME_FORMAT = "j-n-Y H:i"  # '20-1-2009 15:23'
FIRST_DAY_OF_WEEK = 1  # Monday (in Dutch 'maandag')

# The *_INPUT_FORMATS strings use the Python strftime format syntax,
# see https://docs.python.org/library/datetime.html#strftime-strptime-behavior
DATE_INPUT_FORMATS = [
    "%d-%m-%Y",  # '20-01-2009'
    "%d-%m-%y",  # '20-01-09'
    "%d/%m/%Y",  # '20/01/2009'
    "%d/%m/%y",  # '20/01/09'
    "%Y/%m/%d",  # '2009/01/20'
    # "%d %b %Y",  # '20 jan 2009'
    # "%d %b %y",  # '20 jan 09'
    # "%d %B %Y",  # '20 januari 2009'
    # "%d %B %y",  # '20 januari 09'
]
# Kept ISO formats as one is in first position
TIME_INPUT_FORMATS = [
    "%H:%M:%S",  # '15:23:35'
    "%H:%M:%S.%f",  # '15:23:35.000200'
    "%H.%M:%S",  # '15.23:35'
    "%H.%M:%S.%f",  # '15.23:35.000200'
    "%H.%M",  # '15.23'
    "%H:%M",  # '15:23'
]
DATETIME_INPUT_FORMATS = [
    # With time in %H:%M:%S :
    "%d-%m-%Y %H:%M:%S",  # '20-01-2009 15:23:35'
    "%d-%m-%y %H:%M:%S",  # '20-01-09 15:23:35'
    "%Y-%m-%d %H:%M:%S",  # '2009-01-20 15:23:35'
    "%d/%m/%Y %H:%M:%S",  # '20/01/2009 15:23:35'
    "%d/%m/%y %H:%M:%S",  # '20/01/09 15:23:35'
    "%Y/%m/%d %H:%M:%S",  # '2009/01/20 15:23:35'
    # "%d %b %Y %H:%M:%S",  # '20 jan 2009 15:23:35'
    # "%d %b %y %H:%M:%S",  # '20 jan 09 15:23:35'
    # "%d %B %Y %H:%M:%S",  # '20 januari 2009 15:23:35'
    # "%d %B %y %H:%M:%S",  # '20 januari 2009 15:23:35'
    # With time in %H:%M:%S.%f :
    "%d-%m-%Y %H:%M:%S.%f",  # '20-01-2009 15:23:35.000200'
    "%d-%m-%y %H:%M:%S.%f",  # '20-01-09 15:23:35.000200'
    "%Y-%m-%d %H:%M:%S.%f",  # '2009-01-20 15:23:35.000200'
    "%d/%m/%Y %H:%M:%S.%f",  # '20/01/2009 15:23:35.000200'
    "%d/%m/%y %H:%M:%S.%f",  # '20/01/09 15:23:35.000200'
    "%Y/%m/%d %H:%M:%S.%f",  # '2009/01/20 15:23:35.000200'
    # With time in %H.%M:%S :
    "%d-%m-%Y %H.%M:%S",  # '20-01-2009 15.23:35'
    "%d-%m-%y %H.%M:%S",  # '20-01-09 15.23:35'
    "%d/%m/%Y %H.%M:%S",  # '20/01/2009 15.23:35'
    "%d/%m/%y %H.%M:%S",  # '20/01/09 15.23:35'
    # "%d %b %Y %H.%M:%S",  # '20 jan 2009 15.23:35'
    # "%d %b %y %H.%M:%S",  # '20 jan 09 15.23:35'
    # "%d %B %Y %H.%M:%S",  # '20 januari 2009 15.23:35'
    # "%d %B %y %H.%M:%S",  # '20 januari 2009 15.23:35'
    # With time in %H.%M:%S.%f :
    "%d-%m-%Y %H.%M:%S.%f",  # '20-01-2009 15.23:35.000200'
    "%d-%m-%y %H.%M:%S.%f",  # '20-01-09 15.23:35.000200'
    "%d/%m/%Y %H.%M:%S.%f",  # '20/01/2009 15.23:35.000200'
    "%d/%m/%y %H.%M:%S.%f",  # '20/01/09 15.23:35.000200'
    # With time in %H:%M :
    "%d-%m-%Y %H:%M",  # '20-01-2009 15:23'
    "%d-%m-%y %H:%M",  # '20-01-09 15:23'
    "%Y-%m-%d %H:%M",  # '2009-01-20 15:23'
    "%d/%m/%Y %H:%M",  # '20/01/2009 15:23'
    "%d/%m/%y %H:%M",  # '20/01/09 15:23'
    "%Y/%m/%d %H:%M",  # '2009/01/20 15:23'
    # "%d %b %Y %H:%M",  # '20 jan 2009 15:23'
    # "%d %b %y %H:%M",  # '20 jan 09 15:23'
    # "%d %B %Y %H:%M",  # '20 januari 2009 15:23'
    # "%d %B %y %H:%M",  # '20 januari 2009 15:23'
    # With time in %H.%M :
    "%d-%m-%Y %H.%M",  # '20-01-2009 15.23'
    "%d-%m-%y %H.%M",  # '20-01-09 15.23'
    "%d/%m/%Y %H.%M",  # '20/01/2009 15.23'
    "%d/%m/%y %H.%M",  # '20/01/09 15.23'
    # "%d %b %Y %H.%M",  # '20 jan 2009 15.23'
    # "%d %b %y %H.%M",  # '20 jan 09 15.23'
    # "%d %B %Y %H.%M",  # '20 januari 2009 15.23'
    # "%d %B %y %H.%M",  # '20 januari 2009 15.23'
]
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3
