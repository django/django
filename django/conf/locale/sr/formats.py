# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

DATE_FORMAT = 'j. F Y.'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'j. F Y. H:i'
YEAR_MONTH_FORMAT = 'F Y.'
MONTH_DAY_FORMAT = 'j. F'
SHORT_DATE_FORMAT = 'j.m.Y.'
SHORT_DATETIME_FORMAT = 'j.m.Y. H:i'
FIRST_DAY_OF_WEEK = 1
DATE_INPUT_FORMATS = (
    '%d.%m.%Y.', '%d.%m.%y.',       # '25.10.2006.', '25.10.06.'
    '%d. %m. %Y.', '%d. %m. %y.',   # '25. 10. 2006.', '25. 10. 06.'
    '%Y-%m-%d',                     # '2006-10-25'
    # '%d. %b %y.', '%d. %B %y.',     # '25. Oct 06.', '25. October 06.'
    # '%d. %b \'%y.', '%d. %B \'%y.', # '25. Oct '06.', '25. October '06.'
    # '%d. %b %Y.', '%d. %B %Y.',     # '25. Oct 2006.', '25. October 2006.'
)
TIME_INPUT_FORMATS = (
    '%H:%M:%S',     # '14:30:59'
    '%H:%M',        # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%d.%m.%Y. %H:%M:%S',     # '25.10.2006. 14:30:59'
    '%d.%m.%Y. %H:%M',        # '25.10.2006. 14:30'
    '%d.%m.%Y.',              # '25.10.2006.'
    '%d.%m.%y. %H:%M:%S',     # '25.10.06. 14:30:59'
    '%d.%m.%y. %H:%M',        # '25.10.06. 14:30'
    '%d.%m.%y.',              # '25.10.06.'
    '%d. %m. %Y. %H:%M:%S',   # '25. 10. 2006. 14:30:59'
    '%d. %m. %Y. %H:%M',      # '25. 10. 2006. 14:30'
    '%d. %m. %Y.',            # '25. 10. 2006.'
    '%d. %m. %y. %H:%M:%S',   # '25. 10. 06. 14:30:59'
    '%d. %m. %y. %H:%M',      # '25. 10. 06. 14:30'
    '%d. %m. %y.',            # '25. 10. 06.'
    '%Y-%m-%d %H:%M:%S',      # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%M',         # '2006-10-25 14:30'
    '%Y-%m-%d',               # '2006-10-25'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = '.'
NUMBER_GROUPING = 3
