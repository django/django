"""
Providing iterator functions that are not in all version of Python we support.
Where possible, we try to use the system-native version and only fall back to
these implementations if necessary.
"""

import __builtin__
import itertools
import warnings

# Fallback for Python 2.5
def product(*args, **kwds):
    """
    Taken from http://docs.python.org/library/itertools.html#itertools.product
    """
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x+[y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)

if hasattr(itertools, 'product'):
    product = itertools.product

def is_iterable(x):
    "A implementation independent way of checking for iterables"
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True

def all(iterable):
    warnings.warn("django.utils.itercompat.all is deprecated; use the native version instead",
                  PendingDeprecationWarning)
    return __builtin__.all(iterable)

def any(iterable):
    warnings.warn("django.utils.itercompat.any is deprecated; use the native version instead",
                  PendingDeprecationWarning)
    return __builtin__.any(iterable)
