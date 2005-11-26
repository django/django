"""
>>> floatformat(7.7)
'7.7'
>>> floatformat(7.0)
'7'
>>> floatformat(0.7)
'0.7'
>>> floatformat(0.07)
'0.1'
>>> floatformat(0.007)
'0.0'
>>> floatformat(0.0)
'0'
"""

from django.core.template.defaultfilters import *

if __name__ == '__main__':
    import doctest
    doctest.testmod()
