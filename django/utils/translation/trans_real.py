"""Translation helper functions."""
from __future__ import unicode_literals

import locale
import os
import re
import sys
import gettext as gettext_module
from threading import local
import warnings

from django.utils.importlib import import_module
from django.utils.datastructures import SortedDict
from django.utils.encoding import force_str, force_text
from django.utils.functional import memoize
from django.utils._os import upath
from django.utils.safestring import mark_safe, SafeData
from django.utils import six
from django.utils.six import StringIO
from django.utils.translation import TranslatorCommentWarning


# Translations are cached in a dictionary for every language+app tuple.
# The active translations are stored by threadid to make them thread local.
_translations = {}
_active = local()

# The default translation is based on the settings file.
_default = None

# This is a cache for normalized accept-header languages to prevent multiple
# file lookups when checking the same locale on repeated requests.
_accepted = {}
_checked_languages = {}

# magic gettext number to separate context from message
CONTEXT_SEPARATOR = "\x04"

# Format of Accept-Language header values. From RFC 2616, section 14.4 and 3.9
# and RFC 3066, section 2.1
accept_language_re = re.compile(r'''
        ([A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*|\*)      # "en", "en-au", "x-y-z", "es-419", "*"
        (?:\s*;\s*q=(0(?:\.\d{,3})?|1(?:.0{,3})?))?   # Optional "q=1.00", "q=0.8"
        (?:\s*,\s*|$)                                 # Multiple accepts per header.
        ''', re.VERBOSE)

language_code_prefix_re = re.compile(r'^/([\w-]+)(/|$)')


def to_locale(language, to_lower=False):
    """
    Turns a language name (en-us) into a locale name (en_US). If 'to_lower' is
    True, the last component is lower-cased (en_us).
    """
    p = language.find('-')
    if p >= 0:
        if to_lower:
            return language[:p].lower()+'_'+language[p+1:].lower()
        else:
            # Get correct locale for sr-latn
            if len(language[p+1:]) > 2:
                return language[:p].lower()+'_'+language[p+1].upper()+language[p+2:].lower()
            return language[:p].lower()+'_'+language[p+1:].upper()
    else:
        return language.lower()

def to_language(locale):
    """Turns a locale name (en_US) into a language name (en-us)."""
    p = locale.find('_')
    if p >= 0:
        return locale[:p].lower()+'-'+locale[p+1:].lower()
    else:
        return locale.lower()

class DjangoTranslation(gettext_module.GNUTranslations):
    """
    This class sets up the GNUTranslations context with regard to output
    charset.
    """
    def __init__(self, *args, **kw):
        gettext_module.GNUTranslations.__init__(self, *args, **kw)
        self.set_output_charset('utf-8')
        self.__language = '??'

    def merge(self, other):
        self._catalog.update(other._catalog)

    def set_language(self, language):
        self.__language = language
        self.__to_language = to_language(language)

    def language(self):
        return self.__language

    def to_language(self):
        return self.__to_language

    def __repr__(self):
        return "<DjangoTranslation lang:%s>" % self.__language

def translation(language):
    """
    Returns a translation object.

    This translation object will be constructed out of multiple GNUTranslations
    objects by merging their catalogs. It will construct a object for the
    requested language and add a fallback to the default language, if it's
    different from the requested language.
    """
    global _translations

    t = _translations.get(language, None)
    if t is not None:
        return t

    from django.conf import settings

    globalpath = os.path.join(os.path.dirname(upath(sys.modules[settings.__module__].__file__)), 'locale')

    def _fetch(lang, fallback=None):

        global _translations

        res = _translations.get(lang, None)
        if res is not None:
            return res

        loc = to_locale(lang)

        def _translation(path):
            try:
                t = gettext_module.translation('django', path, [loc], DjangoTranslation)
                t.set_language(lang)
                return t
            except IOError:
                return None

        res = _translation(globalpath)

        # We want to ensure that, for example,  "en-gb" and "en-us" don't share
        # the same translation object (thus, merging en-us with a local update
        # doesn't affect en-gb), even though they will both use the core "en"
        # translation. So we have to subvert Python's internal gettext caching.
        base_lang = lambda x: x.split('-', 1)[0]
        if base_lang(lang) in [base_lang(trans) for trans in list(_translations)]:
            res._info = res._info.copy()
            res._catalog = res._catalog.copy()

        def _merge(path):
            t = _translation(path)
            if t is not None:
                if res is None:
                    return t
                else:
                    res.merge(t)
            return res

        for appname in reversed(settings.INSTALLED_APPS):
            app = import_module(appname)
            apppath = os.path.join(os.path.dirname(upath(app.__file__)), 'locale')

            if os.path.isdir(apppath):
                res = _merge(apppath)

        for localepath in reversed(settings.LOCALE_PATHS):
            if os.path.isdir(localepath):
                res = _merge(localepath)

        if res is None:
            if fallback is not None:
                res = fallback
            else:
                return gettext_module.NullTranslations()
        _translations[lang] = res
        return res

    default_translation = _fetch(settings.LANGUAGE_CODE)
    current_translation = _fetch(language, fallback=default_translation)

    return current_translation

def activate(language):
    """
    Fetches the translation object for a given tuple of application name and
    language and installs it as the current translation object for the current
    thread.
    """
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

def get_language():
    """Returns the currently selected language."""
    t = getattr(_active, "value", None)
    if t is not None:
        try:
            return t.to_language()
        except AttributeError:
            pass
    # If we don't have a real translation object, assume it's the default language.
    from django.conf import settings
    return settings.LANGUAGE_CODE

def get_language_bidi():
    """
    Returns selected language's BiDi layout.

    * False = left-to-right layout
    * True = right-to-left layout
    """
    from django.conf import settings

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
        from django.conf import settings
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
    t = getattr(_active, "value", None)
    if t is not None:
        result = getattr(t, translation_function)(eol_message)
    else:
        if _default is None:
            from django.conf import settings
            _default = translation(settings.LANGUAGE_CODE)
        result = getattr(_default, translation_function)(eol_message)
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
        from django.conf import settings
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
    from django.conf import settings
    globalpath = os.path.join(
        os.path.dirname(upath(sys.modules[settings.__module__].__file__)), 'locale')
    return [globalpath] + list(settings.LOCALE_PATHS)

def check_for_language(lang_code):
    """
    Checks whether there is a global language file for the given language
    code. This is used to decide whether a user-provided language is
    available. This is only used for language codes from either the cookies
    or session and during format localization.
    """
    for path in all_locale_paths():
        if gettext_module.find('django', path, [to_locale(lang_code)]) is not None:
            return True
    return False
check_for_language = memoize(check_for_language, _checked_languages, 1)

def get_supported_language_variant(lang_code, supported=None, strict=False):
    """
    Returns the language-code that's listed in supported languages, possibly
    selecting a more generic variant. Raises LookupError if nothing found.

    If `strict` is False (the default), the function will look for an alternative
    country-specific variant when the currently checked is not found.
    """
    if supported is None:
        from django.conf import settings
        supported = SortedDict(settings.LANGUAGES)
    if lang_code:
        # if fr-CA is not supported, try fr-ca; if that fails, fallback to fr.
        generic_lang_code = lang_code.split('-')[0]
        variants = (lang_code, lang_code.lower(), generic_lang_code,
                    generic_lang_code.lower())
        for code in variants:
            if code in supported and check_for_language(code):
                return code
        if not strict:
            # if fr-fr is not supported, try fr-ca.
            for supported_code in supported:
                if supported_code.startswith((generic_lang_code + '-',
                                              generic_lang_code.lower() + '-')):
                    return supported_code
    raise LookupError(lang_code)

def get_language_from_path(path, supported=None, strict=False):
    """
    Returns the language-code if there is a valid language-code
    found in the `path`.

    If `strict` is False (the default), the function will look for an alternative
    country-specific variant when the currently checked is not found.
    """
    if supported is None:
        from django.conf import settings
        supported = SortedDict(settings.LANGUAGES)
    regex_match = language_code_prefix_re.match(path)
    if not regex_match:
        return None
    lang_code = regex_match.group(1)
    try:
        return get_supported_language_variant(lang_code, supported, strict=strict)
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
    global _accepted
    from django.conf import settings
    supported = SortedDict(settings.LANGUAGES)

    if check_path:
        lang_code = get_language_from_path(request.path_info, supported)
        if lang_code is not None:
            return lang_code

    if hasattr(request, 'session'):
        lang_code = request.session.get('django_language', None)
        if lang_code in supported and lang_code is not None and check_for_language(lang_code):
            return lang_code

    lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

    try:
        return get_supported_language_variant(lang_code, supported)
    except LookupError:
        pass

    accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    for accept_lang, unused in parse_accept_lang_header(accept):
        if accept_lang == '*':
            break

        # 'normalized' is the root name of the locale in POSIX format (which is
        # the format used for the directories holding the MO files).
        normalized = locale.locale_alias.get(to_locale(accept_lang, True))
        if not normalized:
            continue
        # Remove the default encoding from locale_alias.
        normalized = normalized.split('.')[0]

        if normalized in _accepted:
            # We've seen this locale before and have an MO file for it, so no
            # need to check again.
            return _accepted[normalized]

        try:
            accept_lang = get_supported_language_variant(accept_lang, supported)
        except LookupError:
            continue
        else:
            _accepted[normalized] = accept_lang
            return accept_lang

    try:
        return get_supported_language_variant(settings.LANGUAGE_CODE, supported)
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
inline_re = re.compile(r"""^\s*trans\s+((?:"[^"]*?")|(?:'[^']*?'))(\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?')))?\s*""")
block_re = re.compile(r"""^\s*blocktrans(\s+.*context\s+((?:"[^"]*?")|(?:'[^']*?')))?(?:\s+|$)""")
endblock_re = re.compile(r"""^\s*endblocktrans$""")
plural_re = re.compile(r"""^\s*plural$""")
constant_re = re.compile(r"""_\(((?:".*?")|(?:'.*?'))\)""")
one_percent_re = re.compile(r"""(?<!%)%(?!%)""")


def templatize(src, origin=None):
    """
    Turns a Django template into something that is understood by xgettext. It
    does so by translating the Django translation tags into standard gettext
    function invocations.
    """
    from django.conf import settings
    from django.template import (Lexer, TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK,
            TOKEN_COMMENT, TRANSLATOR_COMMENT_MARK)
    src = force_text(src, settings.FILE_CHARSET)
    out = StringIO()
    message_context = None
    intrans = False
    inplural = False
    singular = []
    plural = []
    incomment = False
    comment = []
    lineno_comment_map = {}
    comment_lineno_cache = None

    for t in Lexer(src, origin).tokenize():
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
                            out.write(' npgettext(%r, %r, %r,count) ' % (message_context, ''.join(singular), ''.join(plural)))
                        else:
                            out.write(' ngettext(%r, %r, count) ' % (''.join(singular), ''.join(plural)))
                        for part in singular:
                            out.write(blankout(part, 'S'))
                        for part in plural:
                            out.write(blankout(part, 'P'))
                    else:
                        if message_context:
                            out.write(' pgettext(%r, %r) ' % (message_context, ''.join(singular)))
                        else:
                            out.write(' gettext(%r) ' % ''.join(singular))
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
                    raise SyntaxError("Translation blocks must not include other block tags: %s (%sline %d)" % (t.contents, filemsg, t.lineno))
            elif t.token_type == TOKEN_VAR:
                if inplural:
                    plural.append('%%(%s)s' % t.contents)
                else:
                    singular.append('%%(%s)s' % t.contents)
            elif t.token_type == TOKEN_TEXT:
                contents = one_percent_re.sub('%%', t.contents)
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
                    g = one_percent_re.sub('%%', g)
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
                        out.write(' %s ' % p.split(':',1)[1])
                    else:
                        out.write(blankout(p, 'F'))
            elif t.token_type == TOKEN_COMMENT:
                if t.contents.lstrip().startswith(TRANSLATOR_COMMENT_MARK):
                    lineno_comment_map.setdefault(t.lineno,
                                                  []).append(t.contents)
                    comment_lineno_cache = t.lineno
            else:
                out.write(blankout(t.contents, 'X'))
    return force_str(out.getvalue())

def parse_accept_lang_header(lang_string):
    """
    Parses the lang_string, which is the body of an HTTP Accept-Language
    header, and returns a list of (lang, q-value), ordered by 'q' values.

    Any format errors in lang_string results in an empty list being returned.
    """
    result = []
    pieces = accept_language_re.split(lang_string)
    if pieces[-1]:
        return []
    for i in range(0, len(pieces) - 1, 3):
        first, lang, priority = pieces[i : i + 3]
        if first:
            return []
        if priority:
            priority = float(priority)
        if not priority:        # if priority is 0.0 at this point make it 1.0
             priority = 1.0
        result.append((lang, priority))
    result.sort(key=lambda k: k[1], reverse=True)
    return result
