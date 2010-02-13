"""
>>> from datetime import date as original_date, datetime as original_datetime
>>> from django.utils.datetime_safe import date, datetime
>>> just_safe = (1900, 1, 1)
>>> just_unsafe = (1899, 12, 31, 23, 59, 59)
>>> really_old = (20, 1, 1)
>>> more_recent = (2006, 1, 1)

>>> original_datetime(*more_recent) == datetime(*more_recent)
True
>>> original_datetime(*really_old) == datetime(*really_old)
True
>>> original_date(*more_recent) == date(*more_recent)
True
>>> original_date(*really_old) == date(*really_old)
True

>>> original_date(*just_safe).strftime('%Y-%m-%d') == date(*just_safe).strftime('%Y-%m-%d')
True
>>> original_datetime(*just_safe).strftime('%Y-%m-%d') == datetime(*just_safe).strftime('%Y-%m-%d')
True

>>> date(*just_unsafe[:3]).strftime('%Y-%m-%d (weekday %w)')
'1899-12-31 (weekday 0)'
>>> date(*just_safe).strftime('%Y-%m-%d (weekday %w)')
'1900-01-01 (weekday 1)'

>>> datetime(*just_unsafe).strftime('%Y-%m-%d %H:%M:%S (weekday %w)')
'1899-12-31 23:59:59 (weekday 0)'
>>> datetime(*just_safe).strftime('%Y-%m-%d %H:%M:%S (weekday %w)')
'1900-01-01 00:00:00 (weekday 1)'

>>> date(*just_safe).strftime('%y')   # %y will error before this date
'00'
>>> datetime(*just_safe).strftime('%y')
'00'

>>> date(1850, 8, 2).strftime("%Y/%m/%d was a %A")
'1850/08/02 was a Friday'

# Regression for #12524 -- Check that pre-1000AD dates are padded with zeros if necessary
>>> date(1, 1, 1).strftime("%Y/%m/%d was a %A")
'0001/01/01 was a Monday'
"""
