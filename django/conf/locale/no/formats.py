DATE_FORMAT = 'j. F Y'
TIME_FORMAT = 'H:i'
DATETIME_FORMAT = 'j. F Y H:i'
YEAR_MONTH_FORMAT = 'F Y'
MONTH_DAY_FORMAT = 'j. F'
SHORT_DATE_FORMAT = 'd.m.Y'
SHORT_DATETIME_FORMAT = 'd.m.Y H:i'
FIRST_DAY_OF_WEEK = 1 # Monday
DATE_INPUT_FORMATS = (
    '%Y-%m-%d', '%j.%m.%Y', '%j.%m.%y', # '2006-10-25', '25.10.2006', '25.10.06'
    '%Y-%m-%j',                         # '2006-10-25', 
    '%j. %b %Y', '%j %b %Y',            # '25. okt 2006', '25 okt 2006'
    '%j. %b. %Y', '%j %b. %Y',          # '25. okt. 2006', '25 okt. 2006'
    '%j. %B %Y', '%j %B %Y',            # '25. oktober 2006', '25 oktober 2006'
)
TIME_INPUT_FORMATS = (
    '%H:%i:%S',     # '14:30:59'
    '%H:%i',     # '14:30'
)
DATETIME_INPUT_FORMATS = (
    '%Y-%m-%d %H:%i:%S',     # '2006-10-25 14:30:59'
    '%Y-%m-%d %H:%i',        # '2006-10-25 14:30'
    '%Y-%m-%d',              # '2006-10-25'
    '%Y-%m-%j',              # '2006-10-25'
    '%j.%m.%Y %H:%i:%S',     # '25.10.2006 14:30:59'
    '%j.%m.%Y %H:%i',        # '25.10.2006 14:30'
    '%j.%m.%Y',              # '25.10.2006'
    '%j.%m.%y %H:%i:%S',     # '25.10.06 14:30:59'
    '%j.%m.%y %H:%i',        # '25.10.06 14:30'
    '%j.%m.%y',              # '25.10.06'
)
DECIMAL_SEPARATOR = ','
THOUSAND_SEPARATOR = ' '
NUMBER_GROUPING = 3
