"""Translation helper functions."""

import locale
import os
import re
import sys
import warnings
import gettext as gettext_module
from cStringIO import StringIO
from threading import local

from django.utils.importlib import import_module
from django.utils.safestring import mark_safe, SafeData


# Translations are cached in a dictionary for every language+app tuple.
# The active translations are stored by threadid to make them thread local.
_translations = {}
_active = local()

# The default translation is based on the settings file.
_default = None

# This is a cache for normalized accept-header languages to prevent multiple
# file lookups when checking the same locale on repeated requests.
_accepted = {}

# magic gettext number to separate context from message
CONTEXT_SEPARATOR = u"\x04"

# Format of Accept-Language header values. From RFC 2616, section 14.4 and 3.9.
accept_language_re = re.compile(r'''
        ([A-Za-z]{1,8}(?:-[A-Za-z]{1,8})*|\*)   # "en", "en-au", "x-y-z", "*"
        (?:;q=(0(?:\.\d{,3})?|1(?:.0{,3})?))?   # Optional "q=1.00", "q=0.8"
        (?:\s*,\s*|$)                            # Multiple accepts per header.
        ''', re.VERBOSE)

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
    charset. Django uses a defined DEFAULT_CHARSET as the output charset on
    Python 2.4.
    """
    def __init__(self, *args, **kw):
        gettext_module.GNUTranslations.__init__(self, *args, **kw)
        # Starting with Python 2.4, there's a function to define
        # the output charset. Before 2.4, the output charset is
        # identical with the translation file charset.
        try:
            self.set_output_charset('utf-8')
        except AttributeError:
            pass
        self.django_output_charset = 'utf-8'
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

    globalpath = os.path.join(os.path.dirname(sys.modules[settings.__module__].__file__), 'locale')

    if settings.SETTINGS_MODULE is not None:
        parts = settings.SETTINGS_MODULE.split('.')
        project = import_module(parts[0])
        projectpath = os.path.join(os.path.dirname(project.__file__), 'locale')
    else:
        projectpath = None

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
        if base_lang(lang) in [base_lang(trans) for trans in _translations]:
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
            apppath = os.path.join(os.path.dirname(app.__file__), 'locale')

            if os.path.isdir(apppath):
                res = _merge(apppath)

        if projectpath and os.path.isdir(projectpath) and projectpath not in settings.LOCALE_PATHS:
            res = _merge(projectpath)

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
    if isinstance(language, basestring) and language == 'no':
        warnings.warn(
            "The use of the language code 'no' is deprecated. "
            "Please use the 'nb' translation instead.",
            DeprecationWarning
        )
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

    eol_message = message.replace('\r\n', '\n').replace('\r', '\n')
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
    return do_translate(message, 'gettext')

def ugettext(message):
    return do_translate(message, 'ugettext')

def pgettext(context, message):
    result = do_translate(
        u"%s%s%s" % (context, CONTEXT_SEPARATOR, message), 'ugettext')
    if CONTEXT_SEPARATOR in result:
        # Translation not found
        result = message
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
    Returns a UTF-8 bytestring of the translation of either the singular or
    plural, based on the number.
    """
    return do_ntranslate(singular, plural, number, 'ngettext')

def ungettext(singular, plural, number):
    """
    Returns a unicode strings of the translation of either the singular or
    plural, based on the number.
    """
    return do_ntranslate(singular, plural, number, 'ungettext')

def npgettext(context, singular, plural, number):
    result = do_ntranslate(u"%s%s%s" % (context, CONTEXT_SEPARATOR, singular),
                           u"%s%s%s" % (context, CONTEXT_SEPARATOR, plural),
                           number, 'ungettext')
    if CONTEXT_SEPARATOR in result:
        # Translation not found
        result = do_ntranslate(singular, plural, number, 'ungettext')
    return result

def all_locale_paths():
    """
    Returns a list of paths to user-provides languages files.
    """
    from django.conf import settings
    globalpath = os.path.join(
        os.path.dirname(sys.modules[settings.__module__].__file__), 'locale')
    return [globalpath] + list(settings.LOCALE_PATHS)

def check_for_language(lang_code):
    """
    Checks whether there is a global language file for the given language
    code. This is used to decide whether a user-provided language is
    available. This is only used for language codes from either the cookies or
    session and during format localization.
    """
    for path in all_locale_paths():
        if gettext_module.find('django', path, [to_locale(lang_code)]) is not None:
            return True
    return False

def get_language_from_request(request):
    """
    Analyzes the request to find what language the user wants the system to
    show. Only languages listed in settings.LANGUAGES are taken into account.
    If the user requests a sublanguage where we have a main language, we send
    out the main language.
    """
    global _accepted
    from django.conf import settings
    supported = dict(settings.LANGUAGES)

    if hasattr(request, 'session'):
        lang_code = request.session.get('django_language', None)
        if lang_code in supported and lang_code is not None and check_for_language(lang_code):
            return lang_code

    lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)

    if lang_code and lang_code not in supported:
        lang_code = lang_code.split('-')[0] # e.g. if fr-ca is not supported fallback to fr

    if lang_code and lang_code in supported and check_for_language(lang_code):
        return lang_code

    accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    for accept_lang, unused in parse_accept_lang_header(accept):
        if accept_lang == '*':
            break

        # We have a very restricted form for our language files (no encoding
        # specifier, since they all must be UTF-8 and only one possible
        # language each time. So we avoid the overhead of gettext.find() and
        # work out the MO file manually.

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

        for lang, dirname in ((accept_lang, normalized),
                (accept_lang.split('-')[0], normalized.split('_')[0])):
            if lang.lower() not in supported:
                continue
            for path in all_locale_paths():
                if os.path.exists(os.path.join(path, dirname, 'LC_MESSAGES', 'django.mo')):
                    _accepted[normalized] = lang
                    return lang

    return settings.LANGUAGE_CODE

dot_re = re.compile(r'\S')
def blankout(src, char):
    """
    Changes every non-whitespace character to the given char.
    Used in the templatize function.
    """
    return dot_re.sub(char, src)

inline_re = re.compile(r"""^\s*trans\s+((?:".*?")|(?:'.*?'))\s*""")
block_re = re.compile(r"""^\s*blocktrans(?:\s+|$)""")
endblock_re = re.compile(r"""^\s*endblocktrans$""")
plural_re = re.compile(r"""^\s*plural$""")
constant_re = re.compile(r"""_\(((?:".*?")|(?:'.*?'))\)""")

def templatize(src, origin=None):
    """
    Turns a Django template into something that is understood by xgettext. It
    does so by translating the Django translation tags into standard gettext
    function invocations.
    """
    from django.template import Lexer, TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK, TOKEN_COMMENT
    out = StringIO()
    intrans = False
    inplural = False
    singular = []
    plural = []
    incomment = False
    comment = []
    for t in Lexer(src, origin).tokenize():
        if incomment:
            if t.token_type == TOKEN_BLOCK and t.contents == 'endcomment':
                out.write(' # %s' % ''.join(comment))
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
                        out.write(' ngettext(%r,%r,count) ' % (''.join(singular), ''.join(plural)))
                        for part in singular:
                            out.write(blankout(part, 'S'))
                        for part in plural:
                            out.write(blankout(part, 'P'))
                    else:
                        out.write(' gettext(%r) ' % ''.join(singular))
                        for part in singular:
                            out.write(blankout(part, 'S'))
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
                contents = t.contents.replace('%', '%%')
                if inplural:
                    plural.append(contents)
                else:
                    singular.append(contents)
        else:
            if t.token_type == TOKEN_BLOCK:
                imatch = inline_re.match(t.contents)
                bmatch = block_re.match(t.contents)
                cmatches = constant_re.findall(t.contents)
                if imatch:
                    g = imatch.group(1)
                    if g[0] == '"': g = g.strip('"')
                    elif g[0] == "'": g = g.strip("'")
                    out.write(' gettext(%r) ' % g)
                elif bmatch:
                    for fmatch in constant_re.findall(t.contents):
                        out.write(' _(%s) ' % fmatch)
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
                out.write(' # %s' % t.contents)
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
    pieces = accept_language_re.split(lang_string)
    if pieces[-1]:
        return []
    for i in range(0, len(pieces) - 1, 3):
        first, lang, priority = pieces[i : i + 3]
        if first:
            return []
        priority = priority and float(priority) or 1.0
        result.append((lang, priority))
    result.sort(key=lambda k: k[1], reverse=True)
    return result

# get_date_formats and get_partial_date_formats aren't used anymore by Django
# and are kept for backward compatibility.
# Note, it's also important to keep format names marked for translation.
# For compatibility we still want to have formats on translation catalogs.
# That makes template code like {{ my_date|date:_('DATE_FORMAT') }} still work
def get_date_formats():
    """
    Checks whether translation files provide a translation for some technical
    message ID to store date and time formats. If it doesn't contain one, the
    formats provided in the settings will be used.
    """
    warnings.warn(
        "'django.utils.translation.get_date_formats' is deprecated. "
        "Please update your code to use the new i18n aware formatting.",
        DeprecationWarning
    )
    from django.conf import settings
    date_format = ugettext('DATE_FORMAT')
    datetime_format = ugettext('DATETIME_FORMAT')
    time_format = ugettext('TIME_FORMAT')
    if date_format == 'DATE_FORMAT':
        date_format = settings.DATE_FORMAT
    if datetime_format == 'DATETIME_FORMAT':
        datetime_format = settings.DATETIME_FORMAT
    if time_format == 'TIME_FORMAT':
        time_format = settings.TIME_FORMAT
    return date_format, datetime_format, time_format

def get_partial_date_formats():
    """
    Checks whether translation files provide a translation for some technical
    message ID to store partial date formats. If it doesn't contain one, the
    formats provided in the settings will be used.
    """
    warnings.warn(
        "'django.utils.translation.get_partial_date_formats' is deprecated. "
        "Please update your code to use the new i18n aware formatting.",
        DeprecationWarning
    )
    from django.conf import settings
    year_month_format = ugettext('YEAR_MONTH_FORMAT')
    month_day_format = ugettext('MONTH_DAY_FORMAT')
    if year_month_format == 'YEAR_MONTH_FORMAT':
        year_month_format = settings.YEAR_MONTH_FORMAT
    if month_day_format == 'MONTH_DAY_FORMAT':
        month_day_format = settings.MONTH_DAY_FORMAT
    return year_month_format, month_day_format
