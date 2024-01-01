"""
Internationalization support.
"""
from contextlib import ContextDecorator
from decimal import ROUND_UP, Decimal

from django.utils.autoreload import autoreload_started, file_changed
from django.utils.functional import lazy
from django.utils.regex_helper import _lazy_re_compile

__all__ = [
    "activate",
    "deactivate",
    "override",
    "deactivate_all",
    "get_language",
    "get_language_from_request",
    "get_language_info",
    "get_language_bidi",
    "check_for_language",
    "to_language",
    "to_locale",
    "templatize",
    "gettext",
    "gettext_lazy",
    "gettext_noop",
    "ngettext",
    "ngettext_lazy",
    "pgettext",
    "pgettext_lazy",
    "npgettext",
    "npgettext_lazy",
]


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
            from django.utils.translation.reloader import (
                translation_file_changed,
                watch_for_translation_changes,
            )

            autoreload_started.connect(
                watch_for_translation_changes, dispatch_uid="translation_file_changed"
            )
            file_changed.connect(
                translation_file_changed, dispatch_uid="translation_file_changed"
            )
        else:
            from django.utils.translation import trans_null as trans
        setattr(self, real_name, getattr(trans, real_name))
        return getattr(trans, real_name)


_trans = Trans()

# The Trans class is no more needed, so remove it from the namespace.
del Trans


def gettext_noop(message):
    return _trans.gettext_noop(message)


def gettext(message):
    return _trans.gettext(message)


def ngettext(singular, plural, number):
    return _trans.ngettext(singular, plural, number)


def pgettext(context, message):
    return _trans.pgettext(context, message)


def npgettext(context, singular, plural, number):
    return _trans.npgettext(context, singular, plural, number)


gettext_lazy = lazy(gettext, str)
pgettext_lazy = lazy(pgettext, str)


def lazy_number(func, resultclass, number=None, **kwargs):
    if isinstance(number, int):
        kwargs["number"] = number
        proxy = lazy(func, resultclass)(**kwargs)
    else:
        original_kwargs = kwargs.copy()

        class NumberAwareString(resultclass):
            def __bool__(self):
                return bool(kwargs["singular"])

            def _get_number_value(self, values):
                try:
                    return values[number]
                except KeyError:
                    raise KeyError(
                        "Your dictionary lacks key '%s'. Please provide "
                        "it, because it is required to determine whether "
                        "string is singular or plural." % number
                    )

            def _translate(self, number_value):
                kwargs["number"] = number_value
                return func(**kwargs)

            def format(self, *args, **kwargs):
                number_value = (
                    self._get_number_value(kwargs) if kwargs and number else args[0]
                )
                return self._translate(number_value).format(*args, **kwargs)

            def __mod__(self, rhs):
                if isinstance(rhs, dict) and number:
                    number_value = self._get_number_value(rhs)
                else:
                    number_value = rhs
                translated = self._translate(number_value)
                try:
                    translated %= rhs
                except TypeError:
                    # String doesn't contain a placeholder for the number.
                    pass
                return translated

        proxy = lazy(lambda **kwargs: NumberAwareString(), NumberAwareString)(**kwargs)
        proxy.__reduce__ = lambda: (
            _lazy_number_unpickle,
            (func, resultclass, number, original_kwargs),
        )
    return proxy


def _lazy_number_unpickle(func, resultclass, number, kwargs):
    return lazy_number(func, resultclass, number=number, **kwargs)


def ngettext_lazy(singular, plural, number=None):
    return lazy_number(ngettext, str, singular=singular, plural=plural, number=number)


def npgettext_lazy(context, singular, plural, number=None):
    return lazy_number(
        npgettext, str, context=context, singular=singular, plural=plural, number=number
    )


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


def to_language(locale):
    """Turn a locale name (en_US) into a language name (en-us)."""
    p = locale.find("_")
    if p >= 0:
        return locale[:p].lower() + "-" + locale[p + 1 :].lower()
    else:
        return locale.lower()


def to_locale(language):
    """Turn a language name (en-us) into a locale name (en_US)."""
    lang, _, country = language.lower().partition("-")
    if not country:
        return language[:3].lower() + language[3:]
    # A language with > 2 characters after the dash only has its first
    # character after the dash capitalized; e.g. sr-latn becomes sr_Latn.
    # A language with 2 characters after the dash has both characters
    # capitalized; e.g. en-us becomes en_US.
    country, _, tail = country.partition("-")
    country = country.title() if len(country) > 2 else country.upper()
    if tail:
        country += "-" + tail
    return lang + "_" + country


def get_language_from_request(request, check_path=False):
    return _trans.get_language_from_request(request, check_path)


def get_language_from_path(path):
    return _trans.get_language_from_path(path)


def get_supported_language_variant(lang_code, *, strict=False):
    return _trans.get_supported_language_variant(lang_code, strict)


def templatize(src, **kwargs):
    from .template import templatize

    return templatize(src, **kwargs)


def deactivate_all():
    return _trans.deactivate_all()


def get_language_info(lang_code):
    from django.conf.locale import LANG_INFO

    try:
        lang_info = LANG_INFO[lang_code]
        if "fallback" in lang_info and "name" not in lang_info:
            info = get_language_info(lang_info["fallback"][0])
        else:
            info = lang_info
    except KeyError:
        if "-" not in lang_code:
            raise KeyError("Unknown language code %s." % lang_code)
        generic_lang_code = lang_code.split("-")[0]
        try:
            info = LANG_INFO[generic_lang_code]
        except KeyError:
            raise KeyError(
                "Unknown language code %s and %s." % (lang_code, generic_lang_code)
            )

    if info:
        info["name_translated"] = gettext_lazy(info["name"])
    return info


trim_whitespace_re = _lazy_re_compile(r"\s*\n\s*")


def trim_whitespace(s):
    return trim_whitespace_re.sub(" ", s.strip())


def round_away_from_one(value):
    return int(Decimal(value - 1).quantize(Decimal("0"), rounding=ROUND_UP)) + 1
