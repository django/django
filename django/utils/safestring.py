"""
Functions for working with "safe strings": strings that can be displayed safely
without further escaping in HTML. Marking something as a "safe string" means
that the producer of the string has already turned characters that should not
be interpreted by the HTML engine (e.g. '<') into the appropriate entities.
"""

from django.utils.functional import Promise, wraps


class SafeData:
    def __html__(self):
        """
        Returns the html representation of a string for interoperability.

        This allows other template engines to understand Django's SafeData.
        """
        return self


class SafeBytes(bytes, SafeData):
    """
    A bytes subclass that has been specifically marked as "safe" (requires no
    further escaping) for HTML output purposes.

    Kept in Django 2.0 for usage by apps supporting Python 2. Shouldn't be used
    in Django anymore.
    """
    def __add__(self, rhs):
        """
        Concatenating a safe byte string with another safe byte string or safe
        string is safe. Otherwise, the result is no longer safe.
        """
        t = super().__add__(rhs)
        if isinstance(rhs, SafeText):
            return SafeText(t)
        elif isinstance(rhs, SafeBytes):
            return SafeBytes(t)
        return t


class SafeText(str, SafeData):
    """
    A str subclass that has been specifically marked as "safe" for HTML output
    purposes.
    """
    def __add__(self, rhs):
        """
        Concatenating a safe string with another safe byte string or
        safe string is safe. Otherwise, the result is no longer safe.
        """
        t = super().__add__(rhs)
        if isinstance(rhs, SafeData):
            return SafeText(t)
        return t


SafeString = SafeText


def _safety_decorator(safety_marker, func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        return safety_marker(func(*args, **kwargs))
    return wrapped


def mark_safe(s):
    """
    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string is appropriate.

    If used on a method as a decorator, mark the returned data as safe.

    Can be called multiple times on a single string.
    """
    if hasattr(s, '__html__'):
        return s
    if isinstance(s, (str, Promise)):
        return SafeText(s)
    if callable(s):
        return _safety_decorator(mark_safe, s)
    return SafeText(str(s))
