"""
Internationalization support.
"""
import re
import warnings
from contextlib import ContextDecorator

from django.utils.deprecation import RemovedInDjango21Warning
from django.utils.encoding import force_text
from django.utils.functional import lazy

__all__ = [
    'activate', 'deactivate', 'override', 'deactivate_all',
    'get_language', 'get_language_from_request',
    'get_language_info', 'get_language_bidi',
    'check_for_language', 'to_locale', 'templatize', 'string_concat',
    'gettext', 'gettext_lazy', 'gettext_noop',
    'ugettext', 'ugettext_lazy', 'ugettext_noop',
    'ngettext', 'ngettext_lazy',
    'ungettext', 'ungettext_lazy',
    'pgettext', 'pgettext_lazy',
    'npgettext', 'npgettext_lazy',
    'LANGUAGE_SESSION_KEY',
]

LANGUAGE_SESSION_KEY = '_language'


class TranslatorCommentWarning(SyntaxWarning):
    pass


# Here be dragons, so a short explanation of the logic won't hurt:
# We are trying to solve two problems: (1) access settings, in particular
# settings.USE_I18N, as late as possible, so that modules can be imported
# without having to first configure Django, and (2) if some other code creates
# a reference to one of these functions, don't break that reference when we
# replace the functions with their real counterparts (once we do access the
# settings).

class Trans:
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


# An alias since Django 2.0
ugettext = gettext


def ngettext(singular, plural, number):
    return _trans.ngettext(singular, plural, number)


# An alias since Django 2.0
ungettext = ngettext


def pgettext(context, message):
    return _trans.pgettext(context, message)


def npgettext(context, singular, plural, number):
    return _trans.npgettext(context, singular, plural, number)


gettext_lazy = ugettext_lazy = lazy(gettext, str)
pgettext_lazy = lazy(pgettext, str)


def lazy_number(func, resultclass, number=None, **kwargs):
    if isinstance(number, int):
        kwargs['number'] = number
        proxy = lazy(func, resultclass)(**kwargs)
    else:
        original_kwargs = kwargs.copy()

        class NumberAwareString(resultclass):
            def __bool__(self):
                return bool(kwargs['singular'])

            def __mod__(self, rhs):
                if isinstance(rhs, dict) and number:
                    try:
                        number_value = rhs[number]
                    except KeyError:
                        raise KeyError(
                            "Your dictionary lacks key '%s\'. Please provide "
                            "it, because it is required to determine whether "
                            "string is singular or plural." % number
                        )
                else:
                    number_value = rhs
                kwargs['number'] = number_value
                translated = func(**kwargs)
                try:
                    translated = translated % rhs
                except TypeError:
                    # String doesn't contain a placeholder for the number
                    pass
                return translated

        proxy = lazy(lambda **kwargs: NumberAwareString(), NumberAwareString)(**kwargs)
        proxy.__reduce__ = lambda: (_lazy_number_unpickle, (func, resultclass, number, original_kwargs))
    return proxy


def _lazy_number_unpickle(func, resultclass, number, kwargs):
    return lazy_number(func, resultclass, number=number, **kwargs)


def ngettext_lazy(singular, plural, number=None):
    return lazy_number(ngettext, str, singular=singular, plural=plural, number=number)


# An alias since Django 2.0
ungettext_lazy = ngettext_lazy


def npgettext_lazy(context, singular, plural, number=None):
    return lazy_number(npgettext, str, context=context, singular=singular, plural=plural, number=number)


def activate(language):
    return _trans.activate(language)


def deactivate():
    return _trans.deactivate()


class override(ContextDecorator):
    def __init__(self, language, deactivate=False):
        self.language = language
        self.deactivate = deactivate

    def __enter__(self):
        self.old_language = get_language()
        if self.language is not None:
            activate(self.language)
        else:
            deactivate_all()

    def __exit__(self, exc_type, exc_value, traceback):
        if self.old_language is None:
            deactivate_all()
        elif self.deactivate:
            deactivate()
        else:
            activate(self.old_language)


def get_language():
    return _trans.get_language()


def get_language_bidi():
    return _trans.get_language_bidi()


def check_for_language(lang_code):
    return _trans.check_for_language(lang_code)


def to_locale(language):
    return _trans.to_locale(language)


def get_language_from_request(request, check_path=False):
    return _trans.get_language_from_request(request, check_path)


def get_language_from_path(path):
    return _trans.get_language_from_path(path)


def templatize(src, **kwargs):
    from .template import templatize
    return templatize(src, **kwargs)


def deactivate_all():
    return _trans.deactivate_all()


def _string_concat(*strings):
    """
    Lazy variant of string concatenation, needed for translations that are
    constructed from multiple parts.
    """
    warnings.warn(
        'django.utils.translate.string_concat() is deprecated in '
        'favor of django.utils.text.format_lazy().',
        RemovedInDjango21Warning, stacklevel=2)
    return ''.join(force_text(s) for s in strings)


string_concat = lazy(_string_concat, str)


def get_language_info(lang_code):
    from django.conf.locale import LANG_INFO
    try:
        lang_info = LANG_INFO[lang_code]
        if 'fallback' in lang_info and 'name' not in lang_info:
            info = get_language_info(lang_info['fallback'][0])
        else:
            info = lang_info
    except KeyError:
        if '-' not in lang_code:
            raise KeyError("Unknown language code %s." % lang_code)
        generic_lang_code = lang_code.split('-')[0]
        try:
            info = LANG_INFO[generic_lang_code]
        except KeyError:
            raise KeyError("Unknown language code %s and %s." % (lang_code, generic_lang_code))

    if info:
        info['name_translated'] = ugettext_lazy(info['name'])
    return info


trim_whitespace_re = re.compile(r'\s*\n\s*')


def trim_whitespace(s):
    return trim_whitespace_re.sub(' ', s.strip())
