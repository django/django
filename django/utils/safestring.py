"""
Functions for working with "safe strings": strings that can be displayed safely
without further escaping in HTML. Marking something as a "safe string" means
that the producer of the string has already turned characters that should not
be interpreted by the HTML engine (e.g. '<') into the appropriate entities.
"""

from functools import wraps

from django.utils.functional import keep_lazy


class SafeData:
    __slots__ = ()

    def __html__(self):
        """
        Return the html representation of a string for interoperability.

        This allows other template engines to understand Django's SafeData.
        """
        return self


class SafeString(str, SafeData):
    """
    A str subclass that has been specifically marked as "safe" for HTML output
    purposes.
    """

    __slots__ = ()

    def __add__(self, rhs):
        """
        Concatenating a safe string with another safe bytestring or
        safe string is safe. Otherwise, the result is no longer safe.
        """
        if isinstance(rhs, str):
            t = super().__add__(rhs)
            if isinstance(rhs, SafeData):
                t = SafeString(t)
            return t

        # Give the rhs object a chance to handle the addition, for example if
        # the rhs object's class implements `__radd__`. More details:
        # https://docs.python.org/3/reference/datamodel.html#object.__radd__
        return NotImplemented

    def __str__(self):
        return self


SafeText = SafeString  # For backwards compatibility since Django 2.0.


def _safety_decorator(safety_marker, func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return safety_marker(func(*args, **kwargs))

    return wrapper


@keep_lazy(SafeString)
def mark_safe(s):
    """
    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string is appropriate.

    If used on a method as a decorator, mark the returned data as safe.

    Can be called multiple times on a single string.
    """
    if hasattr(s, "__html__"):
        return s
    if callable(s):
        return _safety_decorator(mark_safe, s)
    return SafeString(s)
