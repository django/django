"""
Common checksum routines.
"""

__all__ = ['luhn']

import warnings

from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning

warnings.warn(
    "django.utils.checksums will be removed in Django 2.0. The "
    "luhn() function is now included in django-localflavor 1.1+.",
    RemovedInDjango20Warning
)

LUHN_ODD_LOOKUP = (0, 2, 4, 6, 8, 1, 3, 5, 7, 9)  # sum_of_digits(index * 2)


def luhn(candidate):
    """
    Checks a candidate number for validity according to the Luhn
    algorithm (used in validation of, for example, credit cards).
    Both numeric and string candidates are accepted.
    """
    if not isinstance(candidate, six.string_types):
        candidate = str(candidate)
    try:
        evens = sum(int(c) for c in candidate[-1::-2])
        odds = sum(LUHN_ODD_LOOKUP[int(c)] for c in candidate[-2::-2])
        return ((evens + odds) % 10 == 0)
    except ValueError:  # Raised if an int conversion fails
        return False
