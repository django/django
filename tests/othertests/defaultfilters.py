"""
>>> floatformat(7.7, None)
'7.7'
>>> floatformat(7.0, None)
'7'
>>> floatformat(0.7, None)
'0.7'
>>> floatformat(0.07, None)
'0.1'
>>> floatformat(0.007, None)
'0.0'
>>> floatformat(0.0, None)
'0'
"""

from django.core.template.defaultfilters import *

if __name__ == '__main__':
    import doctest
    doctest.testmod()
