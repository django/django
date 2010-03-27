"""
Internationalization support.
"""
from django.conf import settings
from django.utils.encoding import force_unicode
from django.utils.functional import lazy, curry
from django.utils.translation import trans_real, trans_null


__all__ = ['gettext', 'gettext_noop', 'gettext_lazy', 'ngettext',
        'ngettext_lazy', 'string_concat', 'activate', 'deactivate',
        'get_language', 'get_language_bidi', 'get_date_formats',
        'get_partial_date_formats', 'check_for_language', 'to_locale',
        'get_language_from_request', 'templatize', 'ugettext', 'ugettext_lazy',
        'ungettext', 'deactivate_all']

# Here be dragons, so a short explanation of the logic won't hurt:
# We are trying to solve two problems: (1) access settings, in particular
# settings.USE_I18N, as late as possible, so that modules can be imported
# without having to first configure Django, and (2) if some other code creates
# a reference to one of these functions, don't break that reference when we
# replace the functions with their real counterparts (once we do access the
# settings).

def delayed_loader(real_name, *args, **kwargs):
    """
    Call the real, underlying function.  We have a level of indirection here so
    that modules can use the translation bits without actually requiring
    Django's settings bits to be configured before import.
    """
    if settings.USE_I18N:
        trans = trans_real
    else:
        trans = trans_null

    # Make the originally requested function call on the way out the door.
    return getattr(trans, real_name)(*args, **kwargs)

g = globals()
for name in __all__:
    g['real_%s' % name] = curry(delayed_loader, name)
del g, delayed_loader

def gettext_noop(message):
    return real_gettext_noop(message)

ugettext_noop = gettext_noop

def gettext(message):
    return real_gettext(message)

def ngettext(singular, plural, number):
    return real_ngettext(singular, plural, number)

def ugettext(message):
    return real_ugettext(message)

def ungettext(singular, plural, number):
    return real_ungettext(singular, plural, number)

ngettext_lazy = lazy(ngettext, str)
gettext_lazy = lazy(gettext, str)
ungettext_lazy = lazy(ungettext, unicode)
ugettext_lazy = lazy(ugettext, unicode)

def activate(language):
    return real_activate(language)

def deactivate():
    return real_deactivate()

def get_language():
    return real_get_language()

def get_language_bidi():
    return real_get_language_bidi()

def get_date_formats():
    return real_get_date_formats()

def get_partial_date_formats():
    return real_get_partial_date_formats()

def check_for_language(lang_code):
    return real_check_for_language(lang_code)

def to_locale(language):
    return real_to_locale(language)

def get_language_from_request(request):
    return real_get_language_from_request(request)

def templatize(src):
    return real_templatize(src)

def deactivate_all():
    return real_deactivate_all()

def _string_concat(*strings):
    """
    Lazy variant of string concatenation, needed for translations that are
    constructed from multiple parts.
    """
    return u''.join([force_unicode(s) for s in strings])
string_concat = lazy(_string_concat, unicode)
