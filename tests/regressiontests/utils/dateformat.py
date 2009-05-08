"""
>>> from datetime import datetime, date
>>> from django.utils.dateformat import format
>>> from django.utils.tzinfo import FixedOffset, LocalTimezone

# date
>>> d = date(2009, 5, 16)
>>> date.fromtimestamp(int(format(d, 'U'))) == d
True

# Naive datetime
>>> dt = datetime(2009, 5, 16, 5, 30, 30)
>>> datetime.fromtimestamp(int(format(dt, 'U'))) == dt
True

# datetime with local tzinfo
>>> ltz = LocalTimezone(datetime.now())
>>> dt = datetime(2009, 5, 16, 5, 30, 30, tzinfo=ltz)
>>> datetime.fromtimestamp(int(format(dt, 'U')), ltz) == dt
True
>>> datetime.fromtimestamp(int(format(dt, 'U'))) == dt.replace(tzinfo=None)
True

# datetime with arbitrary tzinfo
>>> tz = FixedOffset(-510)
>>> ltz = LocalTimezone(datetime.now())
>>> dt = datetime(2009, 5, 16, 5, 30, 30, tzinfo=tz)
>>> datetime.fromtimestamp(int(format(dt, 'U')), tz) == dt
True
>>> datetime.fromtimestamp(int(format(dt, 'U')), ltz) == dt
True
>>> datetime.fromtimestamp(int(format(dt, 'U'))) == dt.astimezone(ltz).replace(tzinfo=None)
True
>>> datetime.fromtimestamp(int(format(dt, 'U')), tz).utctimetuple() == dt.utctimetuple()
True
>>> datetime.fromtimestamp(int(format(dt, 'U')), ltz).utctimetuple() == dt.utctimetuple()
True

# Epoch
>>> utc = FixedOffset(0)
>>> udt = datetime(1970, 1, 1, tzinfo=utc)
>>> format(udt, 'U')
u'0'
"""

if __name__ == "__main__":
    import doctest
    doctest.testmod()
