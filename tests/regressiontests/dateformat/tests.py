r"""
>>> format(my_birthday, '')
u''
>>> format(my_birthday, 'a')
u'p.m.'
>>> format(my_birthday, 'A')
u'PM'
>>> format(my_birthday, 'd')
u'08'
>>> format(my_birthday, 'j')
u'8'
>>> format(my_birthday, 'l')
u'Sunday'
>>> format(my_birthday, 'L')
u'False'
>>> format(my_birthday, 'm')
u'07'
>>> format(my_birthday, 'M')
u'Jul'
>>> format(my_birthday, 'b')
u'jul'
>>> format(my_birthday, 'n')
u'7'
>>> format(my_birthday, 'N')
u'July'
>>> no_tz or format(my_birthday, 'O') == '+0100'
True
>>> format(my_birthday, 'P')
u'10 p.m.'
>>> no_tz or format(my_birthday, 'r') == 'Sun, 8 Jul 1979 22:00:00 +0100'
True
>>> format(my_birthday, 's')
u'00'
>>> format(my_birthday, 'S')
u'th'
>>> format(my_birthday, 't')
u'31'
>>> no_tz or format(my_birthday, 'T') == 'CET'
True
>>> no_tz or format(my_birthday, 'U') == '300531600'
True
>>> format(my_birthday, 'w')
u'0'
>>> format(my_birthday, 'W')
u'27'
>>> format(my_birthday, 'y')
u'79'
>>> format(my_birthday, 'Y')
u'1979'
>>> format(my_birthday, 'z')
u'189'
>>> no_tz or format(my_birthday, 'Z') == '3600'
True

>>> no_tz or format(summertime, 'I') == '1'
True
>>> no_tz or format(summertime, 'O') == '+0200'
True
>>> no_tz or format(wintertime, 'I') == '0'
True
>>> no_tz or format(wintertime, 'O') == '+0100'
True

>>> format(my_birthday, r'Y z \C\E\T')
u'1979 189 CET'

>>> format(my_birthday, r'jS o\f F')
u'8th of July'
"""

from django.utils import dateformat, translation
import datetime, os, time

format = dateformat.format
os.environ['TZ'] = 'Europe/Copenhagen'
translation.activate('en-us')

try:
    time.tzset()
    no_tz = False
except AttributeError:
    no_tz = True

my_birthday = datetime.datetime(1979, 7, 8, 22, 00)
summertime = datetime.datetime(2005, 10, 30, 1, 00)
wintertime = datetime.datetime(2005, 10, 30, 4, 00)
