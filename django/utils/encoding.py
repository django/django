from __future__ import unicode_literals

import codecs
import datetime
from decimal import Decimal
import locale
try:
    from urllib.parse import quote
except ImportError:     # Python 2
    from urllib import quote
import warnings

from django.utils.functional import Promise
from django.utils import six

class DjangoUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))

class StrAndUnicode(object):
    """
    A class that derives __str__ from __unicode__.

    On Python 2, __str__ returns the output of __unicode__ encoded as a UTF-8
    bytestring. On Python 3, __str__ returns the output of __unicode__.

    Useful as a mix-in. If you support Python 2 and 3 with a single code base,
    you can inherit this mix-in and just define __unicode__.
    """
    def __init__(self, *args, **kwargs):
        warnings.warn("StrAndUnicode is deprecated. Define a __str__ method "
                      "and apply the @python_2_unicode_compatible decorator "
                      "instead.", PendingDeprecationWarning, stacklevel=2)
        super(StrAndUnicode, self).__init__(*args, **kwargs)

    if six.PY3:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

def python_2_unicode_compatible(klass):
    """
    A decorator that defines __unicode__ and __str__ methods under Python 2.
    Under Python 3 it does nothing.

    To support Python 2 and 3 with a single code base, define a __str__ method
    returning text and apply this decorator to the class.
    """
    if not six.PY3:
        klass.__unicode__ = klass.__str__
        klass.__str__ = lambda self: self.__unicode__().encode('utf-8')
    return klass

def smart_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a text object representing 's' -- unicode on Python 2 and str on
    Python 3. Treats bytestrings using the 'encoding' codec.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_text(s, encoding, strings_only, errors)

def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_text(strings_only=True).
    """
    return isinstance(obj, six.integer_types + (type(None), float, Decimal,
        datetime.datetime, datetime.date, datetime.time))

def force_text(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_text, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first, saves 30-40% when s is an instance of
    # six.text_type. This function gets called often in that setting.
    if isinstance(s, six.text_type):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, six.string_types):
            if hasattr(s, '__unicode__'):
                s = s.__unicode__()
            else:
                if six.PY3:
                    if isinstance(s, bytes):
                        s = six.text_type(s, encoding, errors)
                    else:
                        s = six.text_type(s)
                else:
                    s = six.text_type(bytes(s), encoding, errors)
        else:
            # Note: We use .decode() here, instead of six.text_type(s, encoding,
            # errors), so that if s is a SafeBytes, it ends up being a
            # SafeText at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError as e:
        if not isinstance(s, Exception):
            raise DjangoUnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join([force_text(arg, encoding, strings_only,
                    errors) for arg in s])
    return s

def smart_bytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call.
        return s
    return force_bytes(s, encoding, strings_only, errors)


def force_bytes(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_bytes, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if isinstance(s, bytes):
        if encoding == 'utf-8':
            return s
        else:
            return s.decode('utf-8', errors).encode(encoding, errors)
    if strings_only and (s is None or isinstance(s, int)):
        return s
    if isinstance(s, Promise):
        return six.text_type(s).encode(encoding, errors)
    if not isinstance(s, six.string_types):
        try:
            if six.PY3:
                return six.text_type(s).encode(encoding)
            else:
                return bytes(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return b' '.join([force_bytes(arg, encoding, strings_only,
                        errors) for arg in s])
            return six.text_type(s).encode(encoding, errors)
    else:
        return s.encode(encoding, errors)

if six.PY3:
    smart_str = smart_text
    force_str = force_text
else:
    smart_str = smart_bytes
    force_str = force_bytes
    # backwards compatibility for Python 2
    smart_unicode = smart_text
    force_unicode = force_text

smart_str.__doc__ = """\
Apply smart_text in Python 3 and smart_bytes in Python 2.

This is suitable for writing to sys.stdout (for instance).
"""

force_str.__doc__ = """\
Apply force_text in Python 3 and force_bytes in Python 2.
"""

def iri_to_uri(iri):
    """
    Convert an Internationalized Resource Identifier (IRI) portion to a URI
    portion that is suitable for inclusion in a URL.

    This is the algorithm from section 3.1 of RFC 3987.  However, since we are
    assuming input is either UTF-8 or unicode already, we can simplify things a
    little from the full method.

    Returns an ASCII string containing the encoded result.
    """
    # The list of safe characters here is constructed from the "reserved" and
    # "unreserved" characters specified in sections 2.2 and 2.3 of RFC 3986:
    #     reserved    = gen-delims / sub-delims
    #     gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
    #     sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
    #                   / "*" / "+" / "," / ";" / "="
    #     unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
    # Of the unreserved characters, urllib.quote already considers all but
    # the ~ safe.
    # The % character is also added to the list of safe characters here, as the
    # end of section 3.1 of RFC 3987 specifically mentions that % must not be
    # converted.
    if iri is None:
        return iri
    return quote(force_bytes(iri), safe=b"/#%[]=:;$&()+,!?*@'~")

def filepath_to_uri(path):
    """Convert a file system path to a URI portion that is suitable for
    inclusion in a URL.

    We are assuming input is either UTF-8 or unicode already.

    This method will encode certain chars that would normally be recognized as
    special chars for URIs.  Note that this method does not encode the '
    character, as it is a valid character within URIs.  See
    encodeURIComponent() JavaScript function for more details.

    Returns an ASCII string containing the encoded result.
    """
    if path is None:
        return path
    # I know about `os.sep` and `os.altsep` but I want to leave
    # some flexibility for hardcoding separators.
    return quote(force_bytes(path.replace("\\", "/")), safe=b"/~!*()'")

# The encoding of the default system locale but falls back to the
# given fallback encoding if the encoding is unsupported by python or could
# not be determined.  See tickets #10335 and #5846
try:
    DEFAULT_LOCALE_ENCODING = locale.getdefaultlocale()[1] or 'ascii'
    codecs.lookup(DEFAULT_LOCALE_ENCODING)
except:
    DEFAULT_LOCALE_ENCODING = 'ascii'
