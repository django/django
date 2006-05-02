r"""
>>> format(my_birthday, '')
''
>>> format(my_birthday, 'a')
'p.m.'
>>> format(my_birthday, 'A')
'PM'
>>> format(my_birthday, 'd')
'08'
>>> format(my_birthday, 'j')
'8'
>>> format(my_birthday, 'l')
'Sunday'
>>> format(my_birthday, 'L')
'False'
>>> format(my_birthday, 'm')
'07'
>>> format(my_birthday, 'M')
'Jul'
>>> format(my_birthday, 'n')
'7'
>>> format(my_birthday, 'N')
'July'
>>> format(my_birthday, 'O')
'+0100'
>>> format(my_birthday, 'P')
'10 p.m.'
>>> format(my_birthday, 'r')
'Sun, 8 Jul 1979 22:00:00 +0100'
>>> format(my_birthday, 's')
'00'
>>> format(my_birthday, 'S')
'th'
>>> format(my_birthday, 't')
'31'
>>> format(my_birthday, 'T')
'CET'
>>> format(my_birthday, 'U')
'300531600'
>>> format(my_birthday, 'w')
'0'
>>> format(my_birthday, 'W')
'27'
>>> format(my_birthday, 'y')
'79'
>>> format(my_birthday, 'Y')
'1979'
>>> format(my_birthday, 'z')
'189'
>>> format(my_birthday, 'Z')
'3600'

>>> format(summertime, 'I')
'1'
>>> format(summertime, 'O')
'+0200'
>>> format(wintertime, 'I')
'0'
>>> format(wintertime, 'O')
'+0100'

>>> format(my_birthday, r'Y z \C\E\T')
'1979 189 CET'

>>> format(my_birthday, r'jS o\f F')
'8th of July'
"""

from django.utils import dateformat, translation
import datetime, os, time

format = dateformat.format
os.environ['TZ'] = 'Europe/Copenhagen'
translation.activate('en-us')

time.tzset()

my_birthday = datetime.datetime(1979, 7, 8, 22, 00)
summertime = datetime.datetime(2005, 10, 30, 1, 00)
wintertime = datetime.datetime(2005, 10, 30, 4, 00)
