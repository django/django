"""
Providing iterator functions that are not in all version of Python we support.
Where possible, we try to use the system-native version and only fall back to
these implementations if necessary.
"""

import __builtin__
import itertools
import warnings

def is_iterable(x):
    "A implementation independent way of checking for iterables"
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True

def product(*args, **kwds):
    # PendingDeprecationWarning in 1.5, remove this comment when the Deprecations
    # will have been advanced for 1.5
    warnings.warn("django.utils.itercompat.product is deprecated; use the native version instead",
                  PendingDeprecationWarning)
    return itertools.product(*args, **kwds)

def all(iterable):
    warnings.warn("django.utils.itercompat.all is deprecated; use the native version instead",
                  PendingDeprecationWarning)
    return __builtin__.all(iterable)

def any(iterable):
    warnings.warn("django.utils.itercompat.any is deprecated; use the native version instead",
                  PendingDeprecationWarning)
    return __builtin__.any(iterable)
