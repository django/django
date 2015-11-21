"""Translation helper functions."""
from __future__ import unicode_literals

import gettext as gettext_module
import os
import re
import sys
import warnings
from collections import OrderedDict
from threading import local

from django.apps import apps
from django.conf import settings
from django.conf.locale import LANG_INFO
from django.core.exceptions import AppRegistryNotReady
from django.core.signals import setting_changed
from django.dispatch import receiver
from django.utils import lru_cache, six
from django.utils._os import upath
from django.utils.encoding import force_text
from django.utils.safestring import SafeData, mark_safe
from django.utils.six import StringIO
from django.utils.translation import (
    LANGUAGE_SESSION_KEY, TranslatorCommentWarning, trim_whitespace,
)

# Translations are cached in a dictionary for every language.
# The active translations are stored by threadid to make them thread local.
_translations = {}
_active = local()

# The default translation is based on the settings file.
_default = None

# magic gettext number to separate context from message
CONTEXT_SEPARATOR = "\x04"

# Format of Accept-Language header values. From RFC 2616, section 14.4 and 3.9
# and RFC 3066, section 2.1
accept_language_re = re.compile(r'''
        ([A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)      # "en", "en-au", "x-y-z", "es-419", "*"
        (?:\s*;\s*q=(0(?:\.\d{,3})?|1(?:.0{,3})?))?   # Optional "q=1.00", "q=0.8"
        (?:\s*,\s*|$)                                 # Multiple accepts per header.
        ''', re.VERBOSE)

language_code_re = re.compile(
    r'^[a-z]{1,8}(?:-[a-z0-9]{1,8})*(?:@[a-z0-9]{1,20})?$',
    re.IGNORECASE
)

language_code_prefix_re = re.compile(r'^/([\w@-]+)(/|$)')


@receiver(setting_changed)
def reset_cache(**kwargs):
    """
    Reset global state when LANGUAGES setting has been changed, as some
    languages should no longer be accepted.
    """
    if kwargs['setting'] in ('LANGUAGES', 'LANGUAGE_CODE'):
        check_for_language.cache_clear()
        get_languages.cache_clear()
        get_supported_language_variant.cache_clear()


def to_locale(language, to_lower=False):
    """
    Turns a language name (en-us) into a locale name (en_US). If 'to_lower' is
    True, the last component is lower-cased (en_us).
    """
    p = language.find('-')
    if p >= 0:
        if to_lower:
            return language[:p].lower() + '_' + language[p + 1:].lower()
        else:
            # Get correct locale for sr-latn
            if len(language[p + 1:]) > 2:
                return language[:p].lower() + '_' + language[p + 1].upper() + language[p + 2:].lower()
            return language[:p].lower() + '_' + language[p + 1:].upper()
    else:
        return language.lower()


def to_language(locale):
    """Turns a locale name (en_US) into a language name (en-us)."""
    p = locale.find('_')
    if p >= 0:
        return locale[:p].lower() + '-' + locale[p + 1:].lower()
    else:
        return locale.lower()


class DjangoTranslation(gettext_module.GNUTranslations):
    """
    This class sets up the GNUTranslations context with regard to output
    charset.

    This translation object will be constructed out of multiple GNUTranslations
    objects by merging their catalogs. It will construct an object for the
    requested language and add a fallback to the default language, if it's
    different from the requested language.
    """
    def __init__(self, language):
        """Create a GNUTranslations() using many locale directories"""
        gettext_module.GNUTranslations.__init__(self)
        self.set_output_charset('utf-8')  # For Python 2 gettext() (#25720)

        self.__language = language
        self.__to_language = to_language(language)
        self.__locale = to_locale(language)

        self._init_translation_catalog()
        self._add_installed_apps_translations()
        self._add_local_translations()
        self._add_fallback()

    def __repr__(self):
        return "<DjangoTranslation lang:%s>" % self.__language

    def _new_gnu_trans(self, localedir, use_null_fallback=True):
        """
        Returns a mergeable gettext.GNUTranslations instance.

        A convenience wrapper. By default gettext uses 'fallback=False'.
        Using param `use_null_fallback` to avoid confusion with any other
        references to 'fallback'.
        """
        translation = gettext_module.translation(
            domain='django',
            localedir=localedir,
            languages=[self.__locale],
            codeset='utf-8',
            fallback=use_null_fallback)
        if not hasattr(translation, '_catalog'):
            # provides merge support for NullTranslations()
            translation._catalog = {}
            translation._info = {}
            translation.plural = lambda n: int(n != 1)
        return translation

    def _init_translation_catalog(self):
        """Creates a base catalog using global django translations."""
        settingsfile = upath(sys.modules[settings.__module__].__file__)
        localedir = os.path.join(os.path.dirname(settingsfile), 'locale')
        use_null_fallback = True
        if self.__language == settings.LANGUAGE_CODE:
            # default lang should be present and parseable, if not
            # gettext will raise an IOError (refs #18192).
            use_null_fallback = False
        translation = self._new_gnu_trans(localedir, use_null_fallback)
        self.plural = translation.plural
        self._info = translation._info.copy()
        self._catalog = translation._catalog.copy()

    def _add_installed_apps_translations(self):
        """Merges translations from each installed app."""
        try:
            app_configs = reversed(list(apps.get_app_configs()))
        except AppRegistryNotReady:
            raise AppRegistryNotReady(
                "The translation infrastructure cannot be initialized before the "
                "apps registry is ready. Check that you don't make non-lazy "
                "gettext calls at import time.")
        for app_config in app_configs:
            localedir = os.path.join(app_config.path, 'locale')
            translation = self._new_gnu_trans(localedir)
            self.merge(translation)

    def _add_local_translations(self):
        """Merges translations defined in LOCALE_PATHS."""
        for localedir in reversed(settings.LOCALE_PATHS):
            translation = self._new_gnu_trans(localedir)
            self.merge(translation)

    def _add_fallback(self):
        """Sets the GNUTranslations() fallback with the default language."""
        # Don't set a fallback for the default language or any English variant
        # (as it's empty, so it'll ALWAYS fall back to the default language)
        if self.__language == settings.LANGUAGE_CODE or self.__language.startswith('en'):
            return
        default_translation = translation(settings.LANGUAGE_CODE)
        self.add_fallback(default_translation)

    def merge(self, other):
        """Merge another translation into this catalog."""
        self._catalog.update(other._catalog)

    def language(self):
        """Returns the translation language."""
        return self.__language

    def to_language(self):
        """Returns the translation language name."""
        return self.__to_language


def translation(language):
    """
    Returns a translation object.
    """
    global _translations
    if language not in _translations:
        _translations[language] = DjangoTranslation(language)
    return _translations[language]


def activate(language):
    """
    Fetches the translation object for a given language and installs it as the
    current translation object for the current thread.
    """
    if not language:
        return
    _active.value = translation(language)


def deactivate():
    """
    Deinstalls the currently active translation object so that further _ calls
    will resolve against the default translation object, again.
    """
    if hasattr(_active, "value"):
        del _active.value


def deactivate_all():
    """
    Makes the active translation object a NullTranslations() instance. This is
    useful when we want delayed translations to appear as the original string
    for some reason.
    """
    _active.value = gettext_module.NullTranslations()
    _active.value.to_language = lambda *args: None


def get_language():
    """Returns the currently selected language."""
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
    Returns selected language's BiDi layout.

    * False = left-to-right layout
    * True = right-to-left layout
    """
    lang = get_language()
    if lang is None:
        return False
    else:
        base_lang = get_language().split('-')[0]
        return base_lang in settings.LANGUAGES_BIDI


def catalog():
    """
    Returns the current active catalog for further processing.
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


def do_translate(message, translation_function):
    """
    Translates 'message' using the given 'translation_function' name -- which
    will be either gettext or ugettext. It uses the current thread to find the
    translation object to use. If no current translation is activated, the
    message will be run through the default translation object.
    """
    global _default

    # str() is allowing a bytestring message to remain bytestring on Python 2
    eol_message = message.replace(str('\r\n'), str('\n')).replace(str('\r'), str('\n'))

    if len(eol_message) == 0:
        # Returns an empty value of the corresponding type if an empty message
        # is given, instead of metadata, which is the default gettext behavior.
        result = type(message)("")
    else:
        _default = _default or translation(settings.LANGUAGE_CODE)
        translation_object = getattr(_active, "value", _default)

        result = getattr(translation_object, translation_function)(eol_message)

    if isinstance(message, SafeData):
        return mark_safe(result)

    return result


def gettext(message):
    """
    Returns a string of the translation of the message.

    Returns a string on Python 3 and an UTF-8-encoded bytestring on Python 2.
    """
    return do_translate(message, 'gettext')

if six.PY3:
    ugettext = gettext
else:
    def ugettext(message):
        return do_translate(message, 'ugettext')


def pgettext(context, message):
    msg_with_ctxt = "%s%s%s" % (context, CONTEXT_SEPARATOR, message)
    result = ugettext(msg_with_ctxt)
    if CONTEXT_SEPARATOR in result:
        # Translation not found
        # force unicode, because lazy version expects unicode
        result = force_text(message)
    return result


def gettext_noop(message):
    """
    Marks strings for translation but doesn't translate them now. This can be
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
    Returns a string of the translation of either the singular or plural,
    based on the number.

    Returns a string on Python 3 and an UTF-8-encoded bytestring on Python 2.
    """
    return do_ntranslate(singular, plural, number, 'ngettext')

if six.PY3:
    ungettext = ngettext
else:
    def ungettext(singular, plural, number):
        """
        Returns a unicode strings of the translation of either the singular or
        plural, based on the number.
        """
        return do_ntranslate(singular, plural, number, 'ungettext')


def npgettext(context, singular, plural, number):
    msgs_with_ctxt = ("%s%s%s" % (context, CONTEXT_SEPARATOR, singular),
                      "%s%s%s" % (context, CONTEXT_SEPARATOR, plural),
                      number)
    result = ungettext(*msgs_with_ctxt)
    if CONTEXT_SEPARATOR in result:
        # Translation not found
        result = ungettext(singular, plural, number)
    return result


def all_locale_paths():
    """
    Returns a list of paths to user-provides languages files.
    """
    globalpath = os.path.join(
        os.path.dirname(upath(sys.modules[settings.__module__].__file__)), 'locale')
    return [globalpath] + list(settings.LOCALE_PATHS)


@lru_cache.lru_cache(maxsize=1000)
def check_for_language(lang_code):
    """
    Checks whether there is a global language file for the given language
    code. This is used to decide whether a user-provided language is
    available.

    lru_cache should have a maxsize to prevent from memory exhaustion attacks,
    as the provided language codes are taken from the HTTP request. See also
    <https://www.djangoproject.com/weblog/2007/oct/26/security-fix/>.
    """
    # First, a quick check to make sure lang_code is well-formed (#21458)
    if lang_code is None or not language_code_re.search(lang_code):
        return False
    for path in all_locale_paths():
        if gettext_module.find('django', path, [to_locale(lang_code)]) is not None:
            return True
    return False


@lru_cache.lru_cache()
def get_languages():
    """
    Cache of settings.LANGUAGES in an OrderedDict for easy lookups by key.
    """
    return OrderedDict(settings.LANGUAGES)


@lru_cache.lru_cache(maxsize=1000)
def get_supported_language_variant(lang_code, strict=False):
    """
    Returns the language-code that's listed in supported languages, possibly
    selecting a more generic variant. Raises LookupError if nothing found.

    If `strict` is False (the default), the function will look for an alternative
    country-specific variant when the currently checked is not found.

    lru_cache should have a maxsize to prevent from memory exhaustion attacks,
    as the provided language codes are taken from the HTTP request. See also
    <https://www.djangoproject.com/weblog/2007/oct/26/security-fix/>.
    """
    if lang_code:
        # If 'fr-ca' is not supported, try special fallback or language-only 'fr'.
        possible_lang_codes = [lang_code]
        try:
            possible_lang_codes.extend(LANG_INFO[lang_code]['fallback'])
        except KeyError:
            pass
        generic_lang_code = lang_code.split('-')[0]
        possible_lang_codes.append(generic_lang_code)
        supported_lang_codes = get_languages()

        for code in possible_lang_codes:
            if code in supported_lang_codes and check_for_language(code):
                return code
        if not strict:
            # if fr-fr is not supported, try fr-ca.
            for supported_code in supported_lang_codes:
                if supported_code.startswith(generic_lang_code + '-'):
                    return supported_code
    raise LookupError(lang_code)


def get_language_from_path(path, strict=False):
    """
    Returns the language-code if there is a valid language-code
    found in the `path`.

    If `strict` is False (the default), the function will look for an alternative
    country-specific variant when the currently checked is not found.
    """
    regex_match = language_code_prefix_re.match(path)
    if not regex_match:
        return None
    lang_code = regex_match.group(1)
    try:
        return get_supported_language_variant(lang_code, strict=strict)
    except LookupError:
        return None


def get_language_from_request(request, check_path=False):
    """
    Analyzes the request to find what language the user wants the system to
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

    supported_lang_codes = get_languages()

    if hasattr(request, 'session'):
        lang_code = request.session.get(LANGUAGE_SESSION_KEY)
        if lang_code in supported_lang_codes and lang_code is not None and check_for_language(lang_code):
            return lang_code

    lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

    try:
        return get_supported_language_variant(lang_code)
    except LookupError:
        pass

    accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    for accept_lang, unused in parse_accept_lang_header(accept):
        if accept_lang == '*':
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

dot_re = re.compile(r'\S')


def blankout(src, char):
    """
    Changes every non-whitespace character to the given char.
    Used in the templatize function.
    """
    return dot_re.sub(char, src)


context_re = re.compile(r"""^\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?'))\s*""")
inline_re = re.compile(
    # Match the trans 'some text' part
    r"""^\s*trans\s+((?:"[^"]*?")|(?:'[^']*?'))"""
    # Match and ignore optional filters
    r"""(?:\s*\|\s*[^\s:]+(?::(?:[^\s'":]+|(?:"[^"]*?")|(?:'[^']*?')))?)*"""
    # Match the optional context part
    r"""(\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?')))?\s*"""
)
block_re = re.compile(r"""^\s*blocktrans(\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?')))?(?:\s+|$)""")
endblock_re = re.compile(r"""^\s*endblocktrans$""")
plural_re = re.compile(r"""^\s*plural$""")
constant_re = re.compile(r"""_\(((?:".*?")|(?:'.*?'))\)""")


def templatize(src, origin=None):
    """
    Turns a Django template into something that is understood by xgettext. It
    does so by translating the Django translation tags into standard gettext
    function invocations.
    """
    from django.template.base import (Lexer, TOKEN_TEXT, TOKEN_VAR,
        TOKEN_BLOCK, TOKEN_COMMENT, TRANSLATOR_COMMENT_MARK)
    src = force_text(src, settings.FILE_CHARSET)
    out = StringIO('')
    message_context = None
    intrans = False
    inplural = False
    trimmed = False
    singular = []
    plural = []
    incomment = False
    comment = []
    lineno_comment_map = {}
    comment_lineno_cache = None

    def join_tokens(tokens, trim=False):
        message = ''.join(tokens)
        if trim:
            message = trim_whitespace(message)
        return message

    for t in Lexer(src).tokenize():
        if incomment:
            if t.token_type == TOKEN_BLOCK and t.contents == 'endcomment':
                content = ''.join(comment)
                translators_comment_start = None
                for lineno, line in enumerate(content.splitlines(True)):
                    if line.lstrip().startswith(TRANSLATOR_COMMENT_MARK):
                        translators_comment_start = lineno
                for lineno, line in enumerate(content.splitlines(True)):
                    if translators_comment_start is not None and lineno >= translators_comment_start:
                        out.write(' # %s' % line)
                    else:
                        out.write(' #\n')
                incomment = False
                comment = []
            else:
                comment.append(t.contents)
        elif intrans:
            if t.token_type == TOKEN_BLOCK:
                endbmatch = endblock_re.match(t.contents)
                pluralmatch = plural_re.match(t.contents)
                if endbmatch:
                    if inplural:
                        if message_context:
                            out.write(' npgettext(%r, %r, %r,count) ' % (
                                message_context,
                                join_tokens(singular, trimmed),
                                join_tokens(plural, trimmed)))
                        else:
                            out.write(' ngettext(%r, %r, count) ' % (
                                join_tokens(singular, trimmed),
                                join_tokens(plural, trimmed)))
                        for part in singular:
                            out.write(blankout(part, 'S'))
                        for part in plural:
                            out.write(blankout(part, 'P'))
                    else:
                        if message_context:
                            out.write(' pgettext(%r, %r) ' % (
                                message_context,
                                join_tokens(singular, trimmed)))
                        else:
                            out.write(' gettext(%r) ' % join_tokens(singular,
                                                                    trimmed))
                        for part in singular:
                            out.write(blankout(part, 'S'))
                    message_context = None
                    intrans = False
                    inplural = False
                    singular = []
                    plural = []
                elif pluralmatch:
                    inplural = True
                else:
                    filemsg = ''
                    if origin:
                        filemsg = 'file %s, ' % origin
                    raise SyntaxError(
                        "Translation blocks must not include other block tags: "
                        "%s (%sline %d)" % (t.contents, filemsg, t.lineno)
                    )
            elif t.token_type == TOKEN_VAR:
                if inplural:
                    plural.append('%%(%s)s' % t.contents)
                else:
                    singular.append('%%(%s)s' % t.contents)
            elif t.token_type == TOKEN_TEXT:
                contents = t.contents.replace('%', '%%')
                if inplural:
                    plural.append(contents)
                else:
                    singular.append(contents)

        else:
            # Handle comment tokens (`{# ... #}`) plus other constructs on
            # the same line:
            if comment_lineno_cache is not None:
                cur_lineno = t.lineno + t.contents.count('\n')
                if comment_lineno_cache == cur_lineno:
                    if t.token_type != TOKEN_COMMENT:
                        for c in lineno_comment_map[comment_lineno_cache]:
                            filemsg = ''
                            if origin:
                                filemsg = 'file %s, ' % origin
                            warn_msg = ("The translator-targeted comment '%s' "
                                "(%sline %d) was ignored, because it wasn't the last item "
                                "on the line.") % (c, filemsg, comment_lineno_cache)
                            warnings.warn(warn_msg, TranslatorCommentWarning)
                        lineno_comment_map[comment_lineno_cache] = []
                else:
                    out.write('# %s' % ' | '.join(lineno_comment_map[comment_lineno_cache]))
                comment_lineno_cache = None

            if t.token_type == TOKEN_BLOCK:
                imatch = inline_re.match(t.contents)
                bmatch = block_re.match(t.contents)
                cmatches = constant_re.findall(t.contents)
                if imatch:
                    g = imatch.group(1)
                    if g[0] == '"':
                        g = g.strip('"')
                    elif g[0] == "'":
                        g = g.strip("'")
                    g = g.replace('%', '%%')
                    if imatch.group(2):
                        # A context is provided
                        context_match = context_re.match(imatch.group(2))
                        message_context = context_match.group(1)
                        if message_context[0] == '"':
                            message_context = message_context.strip('"')
                        elif message_context[0] == "'":
                            message_context = message_context.strip("'")
                        out.write(' pgettext(%r, %r) ' % (message_context, g))
                        message_context = None
                    else:
                        out.write(' gettext(%r) ' % g)
                elif bmatch:
                    for fmatch in constant_re.findall(t.contents):
                        out.write(' _(%s) ' % fmatch)
                    if bmatch.group(1):
                        # A context is provided
                        context_match = context_re.match(bmatch.group(1))
                        message_context = context_match.group(1)
                        if message_context[0] == '"':
                            message_context = message_context.strip('"')
                        elif message_context[0] == "'":
                            message_context = message_context.strip("'")
                    intrans = True
                    inplural = False
                    trimmed = 'trimmed' in t.split_contents()
                    singular = []
                    plural = []
                elif cmatches:
                    for cmatch in cmatches:
                        out.write(' _(%s) ' % cmatch)
                elif t.contents == 'comment':
                    incomment = True
                else:
                    out.write(blankout(t.contents, 'B'))
            elif t.token_type == TOKEN_VAR:
                parts = t.contents.split('|')
                cmatch = constant_re.match(parts[0])
                if cmatch:
                    out.write(' _(%s) ' % cmatch.group(1))
                for p in parts[1:]:
                    if p.find(':_(') >= 0:
                        out.write(' %s ' % p.split(':', 1)[1])
                    else:
                        out.write(blankout(p, 'F'))
            elif t.token_type == TOKEN_COMMENT:
                if t.contents.lstrip().startswith(TRANSLATOR_COMMENT_MARK):
                    lineno_comment_map.setdefault(t.lineno,
                                                  []).append(t.contents)
                    comment_lineno_cache = t.lineno
            else:
                out.write(blankout(t.contents, 'X'))
    return out.getvalue()


def parse_accept_lang_header(lang_string):
    """
    Parses the lang_string, which is the body of an HTTP Accept-Language
    header, and returns a list of (lang, q-value), ordered by 'q' values.

    Any format errors in lang_string results in an empty list being returned.
    """
    result = []
    pieces = accept_language_re.split(lang_string.lower())
    if pieces[-1]:
        return []
    for i in range(0, len(pieces) - 1, 3):
        first, lang, priority = pieces[i:i + 3]
        if first:
            return []
        if priority:
            try:
                priority = float(priority)
            except ValueError:
                return []
        if not priority:        # if priority is 0.0 at this point make it 1.0
            priority = 1.0
        result.append((lang, priority))
    result.sort(key=lambda k: k[1], reverse=True)
    return result
