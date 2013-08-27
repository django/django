"""
Providing iterator functions that are not in all version of Python we support.
Where possible, we try to use the system-native version and only fall back to
these implementations if necessary.
"""


def is_iterable(x):
    "A implementation independent way of checking for iterables"
    try:
        iter(x)
    except TypeError:
        return False
    else:
        return True
