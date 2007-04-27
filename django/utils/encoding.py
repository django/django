import types
from django.conf import settings
from django.utils.functional import Promise

def smart_unicode(s, encoding='utf-8'):
    """
    Returns a unicode object representing 's'. Treats bytestrings using the
    'encoding' codec.
    """
    #if isinstance(s, Promise):
    #    # The input is the result of a gettext_lazy() call, or similar. It will
    #    # already be encoded in DEFAULT_CHARSET on evaluation and we don't want
    #    # to evaluate it until render time.
    #    # FIXME: This isn't totally consistent, because it eventually returns a
    #    # bytestring rather than a unicode object. It works wherever we use
    #    # smart_unicode() at the moment. Fixing this requires work in the
    #    # i18n internals.
    #    return s
    if not isinstance(s, basestring,):
        if hasattr(s, '__unicode__'):
            s = unicode(s)
        else:
            s = unicode(str(s), encoding)
    elif not isinstance(s, unicode):
        s = unicode(s, encoding)
    return s

def smart_str(s, encoding='utf-8', strings_only=False):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            return unicode(s).encode(encoding)
    elif isinstance(s, unicode):
        return s.encode(encoding)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8').encode(encoding)
    else:
        return s

class StrAndUnicode(object):
    """
    A class whose __str__ returns its __unicode__ as a UTF-8 bytestring.

    Useful as a mix-in.
    """
    def __str__(self):
        return self.__unicode__().encode('utf-8')

