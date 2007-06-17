from django.conf import settings
from django.utils.functional import Promise

def smart_unicode(s):
    if isinstance(s, Promise):
        # The input is the result of a gettext_lazy() call, or similar. It will
        # already be encoded in DEFAULT_CHARSET on evaluation and we don't want
        # to evaluate it until render time.
        # FIXME: This isn't totally consistent, because it eventually returns a
        # bytestring rather than a unicode object. It works wherever we use
        # smart_unicode() at the moment. Fixing this requires work in the
        # i18n internals.
        return s
    if not isinstance(s, basestring,):
        if hasattr(s, '__unicode__'):
            s = unicode(s)
        else:
            s = unicode(str(s), settings.DEFAULT_CHARSET)
    elif not isinstance(s, unicode):
        s = unicode(s, settings.DEFAULT_CHARSET)
    return s

class StrAndUnicode(object):
    """
    A class whose __str__ returns its __unicode__ as a bytestring
    according to settings.DEFAULT_CHARSET.

    Useful as a mix-in.
    """
    def __str__(self):
        return self.__unicode__().encode(settings.DEFAULT_CHARSET)

