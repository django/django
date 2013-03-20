"""
Providing iterator functions that are not in all version of Python we support.
Where possible, we try to use the system-native version and only fall back to
these implementations if necessary.
"""

import collections
import itertools
import sys
import warnings


def is_iterable(x):
    "A implementation independent way of checking for iterables"
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True

def is_iterator(x):
    """An implementation independent way of checking for iterators

    Python 2.6 has a different implementation of collections.Iterator which
    accepts anything with a `next` method. 2.7+ requires and `__iter__` method
    as well.
    """
    if sys.version_info >= (2, 7):
        return isinstance(x, collections.Iterator)
    return isinstance(x, collections.Iterator) and hasattr(x, '__iter__')

def product(*args, **kwds):
    warnings.warn("django.utils.itercompat.product is deprecated; use the native version instead",
                  PendingDeprecationWarning)
    return itertools.product(*args, **kwds)

def all(iterable):
    warnings.warn("django.utils.itercompat.all is deprecated; use the native version instead",
                  DeprecationWarning)
    return builtins.all(iterable)

def any(iterable):
    warnings.warn("django.utils.itercompat.any is deprecated; use the native version instead",
                  DeprecationWarning)
    return builtins.any(iterable)
