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


class BaseEscapeDataPromise(Promise, EscapeData):
    def _text_cast(self):
        text = super(BaseEscapeDataPromise, self)._text_cast()
        return EscapeText(text)

    def _bytes_cast(self):
        bytes = super(BaseEscapeDataPromise, self)._bytes_cast()
        return EscapeBytes(bytes)


class SafeData(object):
    def __html__(self):
        """
        Returns the html representation of a string.

        Allows interoperability with other template engines.
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


class BaseSafeDataPromise(Promise, SafeData):
    def _text_cast(self):
        text = super(BaseSafeDataPromise, self)._text_cast()
        return SafeText(text)

    def _bytes_cast(self):
        bytes = super(BaseSafeDataPromise, self)._bytes_cast()
        return SafeBytes(bytes)

    def __add__(self, rhs):
        if isinstance(rhs, Promise):
            rhs = rhs._cast()
        t = self._cast() + rhs
        if not isinstance(rhs, SafeData):
            return t
        if self._delegate_bytes:
            return SafeBytes(t)
        return SafeText(t)


def mark_safe(s):
    """
    Explicitly mark a string as safe for (HTML) output purposes. The returned
    object can be used everywhere a string or unicode object is appropriate.

    Can be called multiple times on a single string.
    """
    if isinstance(s, SafeData):
        return s
    if isinstance(s, bytes):
        return SafeBytes(s)
    if isinstance(s, six.text_type):
        return SafeText(s)
    if isinstance(s, Promise):
        attrs = {'_func': staticmethod(s._func), '_resultclasses': s._resultclasses}
        promise_cls = type('SafeDataPromise', (BaseSafeDataPromise,), attrs)
        return promise_cls(s._args, s._kwargs)
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
    if isinstance(s, bytes):
        return EscapeBytes(s)
    if isinstance(s, six.text_type):
        return EscapeText(s)
    if isinstance(s, Promise):
        attrs = {'_func': staticmethod(s._func), '_resultclasses': s._resultclasses}
        promise_cls = type('EscapeDataPromise', (BaseEscapeDataPromise,), attrs)
        return promise_cls(s._args, s._kwargs)
    return EscapeBytes(bytes(s))
