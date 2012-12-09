"""
Functions for working with "safe strings": strings that can be displayed safely
without further escaping in HTML. Marking something as a "safe string" means
that the producer of the string has already turned characters that should not
be interpreted by the HTML engine (e.g. '<') into the appropriate entities.
"""
from django.utils.functional import curry, Promise
from django.utils import six

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
    pass

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

def mark_safe(s):
    """
    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string or unicode object is appropriate.

    Can be called multiple times on a single string.
    """
    if isinstance(s, SafeData):
        return s
    if isinstance(s, bytes) or (isinstance(s, Promise) and s._delegate_bytes):
        return SafeBytes(s)
    if isinstance(s, (six.text_type, Promise)):
        return SafeText(s)
    return SafeString(str(s))

def mark_for_escaping(s):
    """
    Explicitly mark a string as requiring HTML escaping upon output. Has no
    effect on SafeData subclasses.

    Can be called multiple times on a single string (the resulting escaping is
    only applied once).
    """
    if isinstance(s, (SafeData, EscapeData)):
        return s
    if isinstance(s, bytes) or (isinstance(s, Promise) and s._delegate_bytes):
        return EscapeBytes(s)
    if isinstance(s, (six.text_type, Promise)):
        return EscapeText(s)
    return EscapeBytes(bytes(s))

