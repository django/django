"""
Internationalization support.
"""
from django.utils.functional import lazy

__all__ = ['gettext', 'gettext_noop', 'gettext_lazy', 'ngettext',
        'ngettext_lazy', 'string_concat', 'activate', 'deactivate',
        'get_language', 'get_language_bidi', 'get_date_formats',
        'get_partial_date_formats', 'check_for_language', 'to_locale',
        'get_language_from_request', 'install']

# Here be dragons, so a short explanation of the logic won't hurt:
# We are trying to solve two problems: (1) access settings, in particular
# settings.USE_I18N, as late as possible, so that modules can be imported
# without having to first configure Django, and (2) if some other code creates
# a reference to one of these functions, don't break that reference when we
# replace the functions with their real counterparts (once we do access the
# settings).

def delayed_loader(*args, **kwargs):
    """
    Replace each real_* function with the corresponding function from either
    trans_real or trans_null (e.g. real_gettext is replaced with
    trans_real.gettext or trans_null.gettext). This function is run once, the
    first time any i18n method is called. It replaces all the i18n methods at
    once at that time.
    """
    import traceback
    from django.conf import settings
    if settings.USE_I18N:
        import trans_real as trans
    else:
        import trans_null as trans
    caller = traceback.extract_stack(limit=2)[0][2]
    g = globals()
    for name in __all__:
        if hasattr(trans, name):
            g['real_%s' % name] = getattr(trans, name)

    # Make the originally requested function call on the way out the door.
    return g[caller](*args, **kwargs)

g = globals()
for name in __all__:
    g['real_%s' % name] = delayed_loader
del g, delayed_loader

def gettext_noop(message):
    return real_gettext_noop(message)

def gettext(message):
    return real_gettext(message)


def ngettext(singular, plural, number):
    return real_ngettext(singular, plural, number)

def string_concat(*strings):
    return real_string_concat(*strings)

ngettext_lazy = lazy(ngettext, str, unicode)
gettext_lazy = lazy(gettext, str, unicode)
string_concat = lazy(string_concat, str, unicode)

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

def install():
    return real_install()

