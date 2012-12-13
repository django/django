"""
Functions for working with "safe strings": strings that can be displayed safely
without further escaping in HTML. Marking something as a "safe string" means
that the producer of the string has already turned characters that should not
be interpreted by the HTML engine (e.g. '<') into the appropriate entities.
"""
from django.utils.functional import curry, Promise

class EscapeData(object):
    pass

class EscapeString(str, EscapeData):
    """
    A string that should be HTML-escaped when output.
    """
    pass

class EscapeUnicode(unicode, EscapeData):
    """
    A unicode object that should be HTML-escaped when output.
    """
    pass

class SafeData(object):
    pass

class SafeString(str, SafeData):
    """
    A string subclass that has been specifically marked as "safe" (requires no
    further escaping) for HTML output purposes.
    """
    def __add__(self, rhs):
        """
        Concatenating a safe string with another safe string or safe unicode
        object is safe. Otherwise, the result is no longer safe.
        """
        t = super(SafeString, self).__add__(rhs)
        if isinstance(rhs, SafeUnicode):
            return SafeUnicode(t)
        elif isinstance(rhs, SafeString):
            return SafeString(t)
        return t
        
    def _proxy_method(self, *args, **kwargs):
        """
        Wrap a call to a normal unicode method up so that we return safe
        results. The method that is being wrapped is passed in the 'method'
        argument.
        """
        method = kwargs.pop('method')
        data = method(self, *args, **kwargs)
        if isinstance(data, str):
            return SafeString(data)
        else:
            return SafeUnicode(data)

    decode = curry(_proxy_method, method = str.decode)

class SafeUnicode(unicode, SafeData):
    """
    A unicode subclass that has been specifically marked as "safe" for HTML
    output purposes.
    """
    def __add__(self, rhs):
        """
        Concatenating a safe unicode object with another safe string or safe
        unicode object is safe. Otherwise, the result is no longer safe.
        """
        t = super(SafeUnicode, self).__add__(rhs)
        if isinstance(rhs, SafeData):
            return SafeUnicode(t)
        return t
    
    def _proxy_method(self, *args, **kwargs):
        """
        Wrap a call to a normal unicode method up so that we return safe
        results. The method that is being wrapped is passed in the 'method'
        argument.
        """
        method = kwargs.pop('method')
        data = method(self, *args, **kwargs)
        if isinstance(data, str):
            return SafeString(data)
        else:
            return SafeUnicode(data)

    encode = curry(_proxy_method, method = unicode.encode)

def mark_safe(s):
    """
    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string or unicode object is appropriate.

    Can be called multiple times on a single string.
    """
    if isinstance(s, SafeData):
        return s
    if isinstance(s, str) or (isinstance(s, Promise) and s._delegate_str):
        return SafeString(s)
    if isinstance(s, (unicode, Promise)):
        return SafeUnicode(s)
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
    if isinstance(s, str) or (isinstance(s, Promise) and s._delegate_str):
        return EscapeString(s)
    if isinstance(s, (unicode, Promise)):
        return EscapeUnicode(s)
    return EscapeString(str(s))

# Forwards compatibility with Django 1.5

EscapeBytes = EscapeString
EscapeText = EscapeUnicode
SafeBytes = SafeString
SafeText = SafeUnicode
