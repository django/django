"""
Internationalization support.
"""
import warnings
from os import path

from django.utils.encoding import force_unicode
from django.utils.functional import lazy
from django.utils.importlib import import_module


__all__ = ['gettext', 'gettext_noop', 'gettext_lazy', 'ngettext',
        'ngettext_lazy', 'string_concat', 'activate', 'deactivate',
        'get_language', 'get_language_bidi', 'get_date_formats',
        'get_partial_date_formats', 'check_for_language', 'to_locale',
        'get_language_from_request', 'templatize', 'ugettext', 'ugettext_lazy',
        'ungettext', 'ungettext_lazy', 'pgettext', 'pgettext_lazy',
        'npgettext', 'npgettext_lazy', 'deactivate_all', 'get_language_info']

# Here be dragons, so a short explanation of the logic won't hurt:
# We are trying to solve two problems: (1) access settings, in particular
# settings.USE_I18N, as late as possible, so that modules can be imported
# without having to first configure Django, and (2) if some other code creates
# a reference to one of these functions, don't break that reference when we
# replace the functions with their real counterparts (once we do access the
# settings).

class Trans(object):
    """
    The purpose of this class is to store the actual translation function upon
    receiving the first call to that function. After this is done, changes to
    USE_I18N will have no effect to which function is served upon request. If
    your tests rely on changing USE_I18N, you can delete all the functions
    from _trans.__dict__.

    Note that storing the function with setattr will have a noticeable
    performance effect, as access to the function goes the normal path,
    instead of using __getattr__.
    """

    def __getattr__(self, real_name):
        from django.conf import settings
        if settings.USE_I18N:
            from django.utils.translation import trans_real as trans
            # Make sure the project's locale dir isn't in LOCALE_PATHS
            if settings.SETTINGS_MODULE is not None:
                parts = settings.SETTINGS_MODULE.split('.')
                project = import_module(parts[0])
                project_locale_path = path.normpath(
                    path.join(path.dirname(project.__file__), 'locale'))
                normalized_locale_paths = [path.normpath(locale_path)
                    for locale_path in settings.LOCALE_PATHS]
                if (path.isdir(project_locale_path) and
                        not project_locale_path in normalized_locale_paths):
                    warnings.warn("Translations in the project directory "
                                  "aren't supported anymore. Use the "
                                  "LOCALE_PATHS setting instead.",
                                  PendingDeprecationWarning)
        else:
            from django.utils.translation import trans_null as trans
        setattr(self, real_name, getattr(trans, real_name))
        return getattr(trans, real_name)

_trans = Trans()

# The Trans class is no more needed, so remove it from the namespace.
del Trans

def gettext_noop(message):
    return _trans.gettext_noop(message)

ugettext_noop = gettext_noop

def gettext(message):
    return _trans.gettext(message)

def ngettext(singular, plural, number):
    return _trans.ngettext(singular, plural, number)

def ugettext(message):
    return _trans.ugettext(message)

def ungettext(singular, plural, number):
    return _trans.ungettext(singular, plural, number)

def pgettext(context, message):
    return _trans.pgettext(context, message)

def npgettext(context, singular, plural, number):
    return _trans.npgettext(context, singular, plural, number)

ngettext_lazy = lazy(ngettext, str)
gettext_lazy = lazy(gettext, str)
ungettext_lazy = lazy(ungettext, unicode)
ugettext_lazy = lazy(ugettext, unicode)
pgettext_lazy = lazy(pgettext, unicode)
npgettext_lazy = lazy(npgettext, unicode)

def activate(language):
    return _trans.activate(language)

def deactivate():
    return _trans.deactivate()

def get_language():
    return _trans.get_language()

def get_language_bidi():
    return _trans.get_language_bidi()

def get_date_formats():
    return _trans.get_date_formats()

def get_partial_date_formats():
    return _trans.get_partial_date_formats()

def check_for_language(lang_code):
    return _trans.check_for_language(lang_code)

def to_locale(language):
    return _trans.to_locale(language)

def get_language_from_request(request):
    return _trans.get_language_from_request(request)

def templatize(src, origin=None):
    return _trans.templatize(src, origin)

def deactivate_all():
    return _trans.deactivate_all()

def _string_concat(*strings):
    """
    Lazy variant of string concatenation, needed for translations that are
    constructed from multiple parts.
    """
    return u''.join([force_unicode(s) for s in strings])
string_concat = lazy(_string_concat, unicode)

def get_language_info(lang_code):
    from django.conf.locale import LANG_INFO
    try:
        return LANG_INFO[lang_code]
    except KeyError:
        raise KeyError("Unknown language code %r." % lang_code)
