import datetime

###############################################
# Converters from database (string) to Python #
###############################################

def typecast_date(s):
    return s and datetime.date(*map(int, s.split('-'))) # returns None if s is null

def typecast_time(s): # does NOT store time zone information
    if not s: return None
    bits = s.split(':')
    if len(bits[2].split('.')) > 1: # if there is a decimal (e.g. '11:16:36.181305')
        return datetime.time(int(bits[0]), int(bits[1]), int(bits[2].split('.')[0]),
            int(bits[2].split('.')[1].split('-')[0]))
    else: # no decimal was found (e.g. '12:30:00')
        return datetime.time(int(bits[0]), int(bits[1]), int(bits[2].split('.')[0]), 0)

def typecast_timestamp(s): # does NOT store time zone information
    if not s: return None
    d, t = s.split()
    dates = d.split('-')
    times = t.split(':')
    seconds = times[2]
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.datetime(int(dates[0]), int(dates[1]), int(dates[2]),
        int(times[0]), int(times[1]), int(seconds.split('-')[0]),
        int(microseconds.split('-')[0]))

def typecast_boolean(s):
    if s is None: return None
    return str(s)[0].lower() == 't'

###############################################
# Converters from Python to database (string) #
###############################################

def rev_typecast_boolean(obj, d):
    return obj and '1' or '0'
