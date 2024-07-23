"""Translation helper functions."""

import functools
import gettext as gettext_module
import os
import re
import sys
import warnings

from asgiref.local import Local

from django.apps import apps
from django.conf import settings
from django.conf.locale import LANG_INFO
from django.core.exceptions import AppRegistryNotReady
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.utils.regex_helper import _lazy_re_compile
from django.utils.safestring import SafeData, mark_safe

from . import to_language, to_locale

# Translations are cached in a dictionary for every language.
# The active translations are stored by threadid to make them thread local.
_translations = {}
_active = Local()

# The default translation is based on the settings file.
_default = None

# magic gettext number to separate context from message
CONTEXT_SEPARATOR = "\x04"

# Maximum number of characters that will be parsed from the Accept-Language
# header or cookie to prevent possible denial of service or memory exhaustion
# attacks. About 10x longer than the longest value shown on MDN’s
# Accept-Language page.
LANGUAGE_CODE_MAX_LENGTH = 500

# Format of Accept-Language header values. From RFC 9110 Sections 12.4.2 and
# 12.5.4, and RFC 5646 Section 2.1.
accept_language_re = _lazy_re_compile(
    r"""
        # "en", "en-au", "x-y-z", "es-419", "*"
        ([A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)
        # Optional "q=1.00", "q=0.8"
        (?:\s*;\s*q=(0(?:\.[0-9]{,3})?|1(?:\.0{,3})?))?
        # Multiple accepts per header.
        (?:\s*,\s*|$)
    """,
    re.VERBOSE,
)

language_code_re = _lazy_re_compile(
    r"^[a-z]{1,8}(?:-[a-z0-9]{1,8})*(?:@[a-z0-9]{1,20})?$", re.IGNORECASE
)

language_code_prefix_re = _lazy_re_compile(r"^/(\w+([@-]\w+){0,2})(/|$)")


@receiver(setting_changed)
def reset_cache(*, setting, **kwargs):
    """
    Reset global state when LANGUAGES setting has been changed, as some
    languages should no longer be accepted.
    """
    if setting in ("LANGUAGES", "LANGUAGE_CODE"):
        check_for_language.cache_clear()
        get_languages.cache_clear()
        get_supported_language_variant.cache_clear()


class TranslationCatalog:
    """
    Simulate a dict for DjangoTranslation._catalog so as multiple catalogs
    with different plural equations are kept separate.
    """

    def __init__(self, trans=None):
        self._catalogs = [trans._catalog.copy()] if trans else [{}]
        self._plurals = [trans.plural] if trans else [lambda n: int(n != 1)]

    def __getitem__(self, key):
        for cat in self._catalogs:
            try:
                return cat[key]
            except KeyError:
                pass
        raise KeyError(key)

    def __setitem__(self, key, value):
        self._catalogs[0][key] = value

    def __contains__(self, key):
        return any(key in cat for cat in self._catalogs)

    def items(self):
        for cat in self._catalogs:
            yield from cat.items()

    def keys(self):
        for cat in self._catalogs:
            yield from cat.keys()

    def update(self, trans):
        # Merge if plural function is the same, else prepend.
        for cat, plural in zip(self._catalogs, self._plurals):
            if trans.plural.__code__ == plural.__code__:
                cat.update(trans._catalog)
                break
        else:
            self._catalogs.insert(0, trans._catalog.copy())
            self._plurals.insert(0, trans.plural)

    def get(self, key, default=None):
        missing = object()
        for cat in self._catalogs:
            result = cat.get(key, missing)
            if result is not missing:
                return result
        return default

    def plural(self, msgid, num):
        for cat, plural in zip(self._catalogs, self._plurals):
            tmsg = cat.get((msgid, plural(num)))
            if tmsg is not None:
                return tmsg
        raise KeyError


class DjangoTranslation(gettext_module.GNUTranslations):
    """
    Set up the GNUTranslations context with regard to output charset.

    This translation object will be constructed out of multiple GNUTranslations
    objects by merging their catalogs. It will construct an object for the
    requested language and add a fallback to the default language, if it's
    different from the requested language.
    """

    domain = "django"

    def __init__(self, language, domain=None, localedirs=None):
        """Create a GNUTranslations() using many locale directories"""
        gettext_module.GNUTranslations.__init__(self)
        if domain is not None:
            self.domain = domain

        self.__language = language
        self.__to_language = to_language(language)
        self.__locale = to_locale(language)
        self._catalog = None
        # If a language doesn't have a catalog, use the Germanic default for
        # pluralization: anything except one is pluralized.
        self.plural = lambda n: int(n != 1)

        if self.domain == "django":
            if localedirs is not None:
                # A module-level cache is used for caching 'django' translations
                warnings.warn(
                    "localedirs is ignored when domain is 'django'.", RuntimeWarning
                )
                localedirs = None
            self._init_translation_catalog()

        if localedirs:
            for localedir in localedirs:
                translation = self._new_gnu_trans(localedir)
                self.merge(translation)
        else:
            self._add_installed_apps_translations()

        self._add_local_translations()
        if (
            self.__language == settings.LANGUAGE_CODE
            and self.domain == "django"
            and self._catalog is None
        ):
            # default lang should have at least one translation file available.
            raise OSError(
                "No translation files found for default language %s."
                % settings.LANGUAGE_CODE
            )
        self._add_fallback(localedirs)
        if self._catalog is None:
            # No catalogs found for this language, set an empty catalog.
            self._catalog = TranslationCatalog()

    def __repr__(self):
        return "<DjangoTranslation lang:%s>" % self.__language

    def _new_gnu_trans(self, localedir, use_null_fallback=True):
        """
        Return a mergeable gettext.GNUTranslations instance.

        A convenience wrapper. By default gettext uses 'fallback=False'.
        Using param `use_null_fallback` to avoid confusion with any other
        references to 'fallback'.
        """
        return gettext_module.translation(
            domain=self.domain,
            localedir=localedir,
            languages=[self.__locale],
            fallback=use_null_fallback,
        )

    def _init_translation_catalog(self):
        """Create a base catalog using global django translations."""
        settingsfile = sys.modules[settings.__module__].__file__
        localedir = os.path.join(os.path.dirname(settingsfile), "locale")
        translation = self._new_gnu_trans(localedir)
        self.merge(translation)

    def _add_installed_apps_translations(self):
        """Merge translations from each installed app."""
        try:
            app_configs = reversed(apps.get_app_configs())
        except AppRegistryNotReady:
            raise AppRegistryNotReady(
                "The translation infrastructure cannot be initialized before the "
                "apps registry is ready. Check that you don't make non-lazy "
                "gettext calls at import time."
            )
        for app_config in app_configs:
            localedir = os.path.join(app_config.path, "locale")
            if os.path.exists(localedir):
                translation = self._new_gnu_trans(localedir)
                self.merge(translation)

    def _add_local_translations(self):
        """Merge translations defined in LOCALE_PATHS."""
        for localedir in reversed(settings.LOCALE_PATHS):
            translation = self._new_gnu_trans(localedir)
            self.merge(translation)

    def _add_fallback(self, localedirs=None):
        """Set the GNUTranslations() fallback with the default language."""
        # Don't set a fallback for the default language or any English variant
        # (as it's empty, so it'll ALWAYS fall back to the default language)
        if self.__language == settings.LANGUAGE_CODE or self.__language.startswith(
            "en"
        ):
            return
        if self.domain == "django":
            # Get from cache
            default_translation = translation(settings.LANGUAGE_CODE)
        else:
            default_translation = DjangoTranslation(
                settings.LANGUAGE_CODE, domain=self.domain, localedirs=localedirs
            )
        self.add_fallback(default_translation)

    def merge(self, other):
        """Merge another translation into this catalog."""
        if not getattr(other, "_catalog", None):
            return  # NullTranslations() has no _catalog
        if self._catalog is None:
            # Take plural and _info from first catalog found (generally Django's).
            self.plural = other.plural
            self._info = other._info.copy()
            self._catalog = TranslationCatalog(other)
        else:
            self._catalog.update(other)
        if other._fallback:
            self.add_fallback(other._fallback)

    def language(self):
        """Return the translation language."""
        return self.__language

    def to_language(self):
        """Return the translation language name."""
        return self.__to_language

    def ngettext(self, msgid1, msgid2, n):
        try:
            tmsg = self._catalog.plural(msgid1, n)
        except KeyError:
            if self._fallback:
                return self._fallback.ngettext(msgid1, msgid2, n)
            if n == 1:
                tmsg = msgid1
            else:
                tmsg = msgid2
        return tmsg


def translation(language):
    """
    Return a translation object in the default 'django' domain.
    """
    global _translations
    if language not in _translations:
        _translations[language] = DjangoTranslation(language)
    return _translations[language]


def activate(language):
    """
    Fetch the translation object for a given language and install it as the
    current translation object for the current thread.
    """
    if not language:
        return
    _active.value = translation(language)


def deactivate():
    """
    Uninstall the active translation object so that further _() calls resolve
    to the default translation object.
    """
    if hasattr(_active, "value"):
        del _active.value


def deactivate_all():
    """
    Make the active translation object a NullTranslations() instance. This is
    useful when we want delayed translations to appear as the original string
    for some reason.
    """
    _active.value = gettext_module.NullTranslations()
    _active.value.to_language = lambda *args: None


def get_language():
    """Return the currently selected language."""
    t = getattr(_active, "value", None)
    if t is not None:
        try:
            return t.to_language()
        except AttributeError:
            pass
    # If we don't have a real translation object, assume it's the default language.
    return settings.LANGUAGE_CODE


def get_language_bidi():
    """
    Return selected language's BiDi layout.

    * False = left-to-right layout
    * True = right-to-left layout
    """
    lang = get_language()
    if lang is None:
        return False
    else:
        base_lang = get_language().split("-")[0]
        return base_lang in settings.LANGUAGES_BIDI


def catalog():
    """
    Return the current active catalog for further processing.
    This can be used if you need to modify the catalog or want to access the
    whole message catalog instead of just translating one string.
    """
    global _default

    t = getattr(_active, "value", None)
    if t is not None:
        return t
    if _default is None:
        _default = translation(settings.LANGUAGE_CODE)
    return _default


def gettext(message):
    """
    Translate the 'message' string. It uses the current thread to find the
    translation object to use. If no current translation is activated, the
    message will be run through the default translation object.
    """
    global _default

    eol_message = message.replace("\r\n", "\n").replace("\r", "\n")

    if eol_message:
        _default = _default or translation(settings.LANGUAGE_CODE)
        translation_object = getattr(_active, "value", _default)

        result = translation_object.gettext(eol_message)
    else:
        # Return an empty value of the corresponding type if an empty message
        # is given, instead of metadata, which is the default gettext behavior.
        result = type(message)("")

    if isinstance(message, SafeData):
        return mark_safe(result)

    return result


def pgettext(context, message):
    msg_with_ctxt = "%s%s%s" % (context, CONTEXT_SEPARATOR, message)
    result = gettext(msg_with_ctxt)
    if CONTEXT_SEPARATOR in result:
        # Translation not found
        result = message
    elif isinstance(message, SafeData):
        result = mark_safe(result)
    return result


def gettext_noop(message):
    """
    Mark strings for translation but don't translate them now. This can be
    used to store strings in global variables that should stay in the base
    language (because they might be used externally) and will be translated
    later.
    """
    return message


def do_ntranslate(singular, plural, number, translation_function):
    global _default

    t = getattr(_active, "value", None)
    if t is not None:
        return getattr(t, translation_function)(singular, plural, number)
    if _default is None:
        _default = translation(settings.LANGUAGE_CODE)
    return getattr(_default, translation_function)(singular, plural, number)


def ngettext(singular, plural, number):
    """
    Return a string of the translation of either the singular or plural,
    based on the number.
    """
    return do_ntranslate(singular, plural, number, "ngettext")


def npgettext(context, singular, plural, number):
    msgs_with_ctxt = (
        "%s%s%s" % (context, CONTEXT_SEPARATOR, singular),
        "%s%s%s" % (context, CONTEXT_SEPARATOR, plural),
        number,
    )
    result = ngettext(*msgs_with_ctxt)
    if CONTEXT_SEPARATOR in result:
        # Translation not found
        result = ngettext(singular, plural, number)
    return result


def all_locale_paths():
    """
    Return a list of paths to user-provides languages files.
    """
    globalpath = os.path.join(
        os.path.dirname(sys.modules[settings.__module__].__file__), "locale"
    )
    app_paths = []
    for app_config in apps.get_app_configs():
        locale_path = os.path.join(app_config.path, "locale")
        if os.path.exists(locale_path):
            app_paths.append(locale_path)
    return [globalpath, *settings.LOCALE_PATHS, *app_paths]


@functools.lru_cache(maxsize=1000)
def check_for_language(lang_code):
    """
    Check whether there is a global language file for the given language
    code. This is used to decide whether a user-provided language is
    available.

    lru_cache should have a maxsize to prevent from memory exhaustion attacks,
    as the provided language codes are taken from the HTTP request. See also
    <https://www.djangoproject.com/weblog/2007/oct/26/security-fix/>.
    """
    # First, a quick check to make sure lang_code is well-formed (#21458)
    if lang_code is None or not language_code_re.search(lang_code):
        return False
    return any(
        gettext_module.find("django", path, [to_locale(lang_code)]) is not None
        for path in all_locale_paths()
    )


@functools.lru_cache
def get_languages():
    """
    Cache of settings.LANGUAGES in a dictionary for easy lookups by key.
    Convert keys to lowercase as they should be treated as case-insensitive.
    """
    return {key.lower(): value for key, value in dict(settings.LANGUAGES).items()}


@functools.lru_cache(maxsize=1000)
def get_supported_language_variant(lang_code, strict=False):
    """
    Return the language code that's listed in supported languages, possibly
    selecting a more generic variant. Raise LookupError if nothing is found.

    If `strict` is False (the default), look for a country-specific variant
    when neither the language code nor its generic variant is found.

    The language code is truncated to a maximum length to avoid potential
    denial of service attacks.

    lru_cache should have a maxsize to prevent from memory exhaustion attacks,
    as the provided language codes are taken from the HTTP request. See also
    <https://www.djangoproject.com/weblog/2007/oct/26/security-fix/>.
    """
    if lang_code:
        # Truncate the language code to a maximum length to avoid potential
        # denial of service attacks.
        if len(lang_code) > LANGUAGE_CODE_MAX_LENGTH:
            if (
                not strict
                and (index := lang_code.rfind("-", 0, LANGUAGE_CODE_MAX_LENGTH)) > 0
            ):
                # There is a generic variant under the maximum length accepted length.
                lang_code = lang_code[:index]
            else:
                raise LookupError(lang_code)
        # If 'zh-hant-tw' is not supported, try special fallback or subsequent
        # language codes i.e. 'zh-hant' and 'zh'.
        possible_lang_codes = [lang_code]
        try:
            possible_lang_codes.extend(LANG_INFO[lang_code]["fallback"])
        except KeyError:
            pass
        i = None
        while (i := lang_code.rfind("-", 0, i)) > -1:
            possible_lang_codes.append(lang_code[:i])
        generic_lang_code = possible_lang_codes[-1]
        supported_lang_codes = get_languages()

        for code in possible_lang_codes:
            if code.lower() in supported_lang_codes and check_for_language(code):
                return code
        if not strict:
            # if fr-fr is not supported, try fr-ca.
            for supported_code in supported_lang_codes:
                if supported_code.startswith(generic_lang_code + "-"):
                    return supported_code
    raise LookupError(lang_code)


def get_language_from_path(path, strict=False):
    """
    Return the language code if there's a valid language code found in `path`.

    If `strict` is False (the default), look for a country-specific variant
    when neither the language code nor its generic variant is found.
    """
    regex_match = language_code_prefix_re.match(path)
    if not regex_match:
        return None
    lang_code = regex_match[1]
    try:
        return get_supported_language_variant(lang_code, strict=strict)
    except LookupError:
        return None


def get_language_from_request(request, check_path=False):
    """
    Analyze the request to find what language the user wants the system to
    show. Only languages listed in settings.LANGUAGES are taken into account.
    If the user requests a sublanguage where we have a main language, we send
    out the main language.

    If check_path is True, the URL path prefix will be checked for a language
    code, otherwise this is skipped for backwards compatibility.
    """
    if check_path:
        lang_code = get_language_from_path(request.path_info)
        if lang_code is not None:
            return lang_code

    lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if (
        lang_code is not None
        and lang_code in get_languages()
        and check_for_language(lang_code)
    ):
        return lang_code

    try:
        return get_supported_language_variant(lang_code)
    except LookupError:
        pass

    accept = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
    for accept_lang, unused in parse_accept_lang_header(accept):
        if accept_lang == "*":
            break

        if not language_code_re.search(accept_lang):
            continue

        try:
            return get_supported_language_variant(accept_lang)
        except LookupError:
            continue

    try:
        return get_supported_language_variant(settings.LANGUAGE_CODE)
    except LookupError:
        return settings.LANGUAGE_CODE


@functools.lru_cache(maxsize=1000)
def _parse_accept_lang_header(lang_string):
    """
    Parse the lang_string, which is the body of an HTTP Accept-Language
    header, and return a tuple of (lang, q-value), ordered by 'q' values.

    Return an empty tuple if there are any format errors in lang_string.
    """
    result = []
    pieces = accept_language_re.split(lang_string.lower())
    if pieces[-1]:
        return ()
    for i in range(0, len(pieces) - 1, 3):
        first, lang, priority = pieces[i : i + 3]
        if first:
            return ()
        if priority:
            priority = float(priority)
        else:
            priority = 1.0
        result.append((lang, priority))
    result.sort(key=lambda k: k[1], reverse=True)
    return tuple(result)


def parse_accept_lang_header(lang_string):
    """
    Parse the value of the Accept-Language header up to a maximum length.

    The value of the header is truncated to a maximum length to avoid potential
    denial of service and memory exhaustion attacks. Excessive memory could be
    used if the raw value is very large as it would be cached due to the use of
    functools.lru_cache() to avoid repetitive parsing of common header values.
    """
    # If the header value doesn't exceed the maximum allowed length, parse it.
    if len(lang_string) <= LANGUAGE_CODE_MAX_LENGTH:
        return _parse_accept_lang_header(lang_string)

    # If there is at least one comma in the value, parse up to the last comma
    # before the max length, skipping any truncated parts at the end of the
    # header value.
    if (index := lang_string.rfind(",", 0, LANGUAGE_CODE_MAX_LENGTH)) > 0:
        return _parse_accept_lang_header(lang_string[:index])

    # Don't attempt to parse if there is only one language-range value which is
    # longer than the maximum allowed length and so truncated.
    return ()
