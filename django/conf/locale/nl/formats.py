# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'j F Y'                   # '20 januari 2009'
TIME_FORMAT = 'H:i'                     # '15:23'
DATETIME_FORMAT = 'j F Y H:i'           # '20 januari 2009 15:23'
YEAR_MONTH_FORMAT = 'F Y'               # 'januari 2009'
MONTH_DAY_FORMAT = 'j F'                # '20 januari'
SHORT_DATE_FORMAT = 'j-n-Y'             # '20-1-2009'
SHORT_DATETIME_FORMAT = 'j-n-Y H:i'     # '20-1-2009 15:23'
FIRST_DAY_OF_WEEK = 1                   # Monday (in Dutch 'maandag')
DATE_INPUT_FORMATS = (
    '%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d', # '20-01-2009', '20-01-09', '2009-01-20'
    # '%d %b %Y', '%d %b %y',             # '20 jan 2009', '20 jan 09'
    # '%d %B %Y', '%d %B %y',             # '20 januari 2009', '20 januari 09'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',                         # '15:23:35'
    '%H.%M:%S',                         # '15.23:35'
    '%H.%M',                            # '15.23'
    '%H:%M',                            # '15:23'
)
DATETIME_INPUT_FORMATS = (
    # With time in %H:%M:%S :
    '%d-%m-%Y %H:%M:%S', '%d-%m-%y %H:%M:%S', '%Y-%m-%d %H:%M:%S',  # '20-01-2009 15:23:35', '20-01-09 15:23:35', '2009-01-20 15:23:35'
    # '%d %b %Y %H:%M:%S', '%d %b %y %H:%M:%S',   # '20 jan 2009 15:23:35', '20 jan 09 15:23:35'
    # '%d %B %Y %H:%M:%S', '%d %B %y %H:%M:%S',   # '20 januari 2009 15:23:35', '20 januari 2009 15:23:35'
    # With time in %H.%M:%S :
    '%d-%m-%Y %H.%M:%S', '%d-%m-%y %H.%M:%S',   # '20-01-2009 15.23:35', '20-01-09 15.23:35'
    # '%d %b %Y %H.%M:%S', '%d %b %y %H.%M:%S',   # '20 jan 2009 15.23:35', '20 jan 09 15.23:35'
    # '%d %B %Y %H.%M:%S', '%d %B %y %H.%M:%S',   # '20 januari 2009 15.23:35', '20 januari 2009 15.23:35'
    # With time in %H:%M :
    '%d-%m-%Y %H:%M', '%d-%m-%y %H:%M', '%Y-%m-%d %H:%M',   # '20-01-2009 15:23', '20-01-09 15:23', '2009-01-20 15:23'
    # '%d %b %Y %H:%M', '%d %b %y %H:%M',         # '20 jan 2009 15:23', '20 jan 09 15:23'
    # '%d %B %Y %H:%M', '%d %B %y %H:%M',         # '20 januari 2009 15:23', '20 januari 2009 15:23'
    # With time in %H.%M :
    '%d-%m-%Y %H.%M', '%d-%m-%y %H.%M',         # '20-01-2009 15.23', '20-01-09 15.23'
    # '%d %b %Y %H.%M', '%d %b %y %H.%M',         # '20 jan 2009 15.23', '20 jan 09 15.23'
    # '%d %B %Y %H.%M', '%d %B %y %H.%M',         # '20 januari 2009 15.23', '20 januari 2009 15.23'
    # Without time :
    '%d-%m-%Y', '%d-%m-%y', '%Y-%m-%d',         # '20-01-2009', '20-01-09', '2009-01-20'
    # '%d %b %Y', '%d %b %y',                     # '20 jan 2009', '20 jan 09'
    # '%d %B %Y', '%d %B %y',                     # '20 januari 2009', '20 januari 2009'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
