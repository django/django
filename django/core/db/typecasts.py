import datetime

###############################################
# Converters from database (string) to Python #
###############################################

def typecast_date(s):
    return s and datetime.date(*map(int, s.split('-'))) # returns None if s is null

def typecast_time(s): # does NOT store time zone information
    if not s: return None
    hour, minutes, seconds = s.split(':')
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.time(int(hour), int(minutes), int(seconds), int(microseconds))

def typecast_timestamp(s): # does NOT store time zone information
    # "2005-07-29 15:48:00.590358-05"
    # "2005-07-29 09:56:00-05"
    if not s: return None
    d, t = s.split()
    if t[-3] in ('-', '+'):
        t = t[:-3] # Remove the time-zone information, if it exists.
    dates = d.split('-')
    times = t.split(':')
    seconds = times[2]
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.datetime(int(dates[0]), int(dates[1]), int(dates[2]),
        int(times[0]), int(times[1]), int(seconds), int(microseconds))

def typecast_boolean(s):
    if s is None: return None
    return str(s)[0].lower() == 't'

###############################################
# Converters from Python to database (string) #
###############################################

def rev_typecast_boolean(obj, d):
    return obj and '1' or '0'
