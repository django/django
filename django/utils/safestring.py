"""
Functions for working with "safe strings": strings that can be displayed safely
without further escaping in HTML. Marking something as a "safe string" means
that the producer of the string has already turned characters that should not
be interpreted by the HTML engine (e.g. '<') into the appropriate entities.
"""
import warnings

from django.utils import six
from django.utils.deprecation import RemovedInDjango20Warning
from django.utils.functional import Promise, curry, wraps


class EscapeData(object):
    pass


class EscapeBytes(bytes, EscapeData):
    """
    A byte string that should be HTML-escaped when output.
    """
    pass


class EscapeText(six.text_type, EscapeData):
    """
    A unicode string object that should be HTML-escaped when output.
    """
    pass


if six.PY3:
    EscapeString = EscapeText
else:
    EscapeString = EscapeBytes
    # backwards compatibility for Python 2
    EscapeUnicode = EscapeText


class SafeData(object):
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
    """
    def __add__(self, rhs):
        """
        Concatenating a safe byte string with another safe byte string or safe
        unicode string is safe. Otherwise, the result is no longer safe.
        """
        t = super(SafeBytes, self).__add__(rhs)
        if isinstance(rhs, SafeText):
            return SafeText(t)
        elif isinstance(rhs, SafeBytes):
            return SafeBytes(t)
        return t

    def _proxy_method(self, *args, **kwargs):
        """
        Wrap a call to a normal unicode method up so that we return safe
        results. The method that is being wrapped is passed in the 'method'
        argument.
        """
        method = kwargs.pop('method')
        data = method(self, *args, **kwargs)
        if isinstance(data, bytes):
            return SafeBytes(data)
        else:
            return SafeText(data)

    decode = curry(_proxy_method, method=bytes.decode)


class SafeText(six.text_type, SafeData):
    """
    A unicode (Python 2) / str (Python 3) subclass that has been specifically
    marked as "safe" for HTML output purposes.
    """
    def __add__(self, rhs):
        """
        Concatenating a safe unicode string with another safe byte string or
        safe unicode string is safe. Otherwise, the result is no longer safe.
        """
        t = super(SafeText, self).__add__(rhs)
        if isinstance(rhs, SafeData):
            return SafeText(t)
        return t

    def _proxy_method(self, *args, **kwargs):
        """
        Wrap a call to a normal unicode method up so that we return safe
        results. The method that is being wrapped is passed in the 'method'
        argument.
        """
        method = kwargs.pop('method')
        data = method(self, *args, **kwargs)
        if isinstance(data, bytes):
            return SafeBytes(data)
        else:
            return SafeText(data)

    encode = curry(_proxy_method, method=six.text_type.encode)


if six.PY3:
    SafeString = SafeText
else:
    SafeString = SafeBytes
    # backwards compatibility for Python 2
    SafeUnicode = SafeText


def _safety_decorator(safety_marker, func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        return safety_marker(func(*args, **kwargs))
    return wrapped


def mark_safe(s):
    """
    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string or unicode object is appropriate.

    If used on a method as a decorator, mark the returned data as safe.

    Can be called multiple times on a single string.
    """
    if hasattr(s, '__html__'):
        return s
    if isinstance(s, bytes) or (isinstance(s, Promise) and s._delegate_bytes):
        return SafeBytes(s)
    if isinstance(s, (six.text_type, Promise)):
        return SafeText(s)
    if callable(s):
        return _safety_decorator(mark_safe, s)
    return SafeString(str(s))


def mark_for_escaping(s):
    """
    Explicitly mark a string as requiring HTML escaping upon output. Has no
    effect on SafeData subclasses.

    Can be called multiple times on a single string (the resulting escaping is
    only applied once).
    """
    warnings.warn('mark_for_escaping() is deprecated.', RemovedInDjango20Warning)
    if hasattr(s, '__html__') or isinstance(s, EscapeData):
        return s
    if isinstance(s, bytes) or (isinstance(s, Promise) and s._delegate_bytes):
        return EscapeBytes(s)
    if isinstance(s, (six.text_type, Promise)):
        return EscapeText(s)
    return EscapeString(str(s))
