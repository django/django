"translation helper functions"

import os
import re
import sys
import gettext as gettext_module
from cStringIO import StringIO

from django.utils.functional import lazy

try:
    import threading
    hasThreads = True
except ImportError:
    hasThreads = False

if hasThreads:
    currentThread = threading.currentThread
else:
    def currentThread():
        return 'no threading'

# translations are cached in a dictionary for
# every language+app tuple. The active translations
# are stored by threadid to make them thread local.
_translations = {}
_active = {}

# the default translation is based on the settings file
_default = None

# this is a cache for accept-header to translation
# object mappings to prevent the accept parser to
# run multiple times for one user
_accepted = {}

def to_locale(language):
    "turn a language name (en-us) into a locale name (en_US)"
    p = language.find('-')
    if p >= 0:
        return language[:p].lower()+'_'+language[p+1:].upper()
    else:
        return language.lower()

def to_language(locale):
    "turns a locale name (en_US) into a language name (en-us)"
    p = locale.find('_')
    if p >= 0:
        return locale[:p].lower()+'-'+locale[p+1:].lower()
    else:
        return locale.lower()

class DjangoTranslation(gettext_module.GNUTranslations):
    """
    This class sets up the GNUTranslations context with
    regard to output charset. Django uses a defined
    DEFAULT_CHARSET as the output charset on Python 2.4 -
    with Python 2.3, you need to use DjangoTranslation23.
    """

    def __init__(self, *args, **kw):
        from django.conf import settings
        gettext_module.GNUTranslations.__init__(self, *args, **kw)
        # starting with Python 2.4, there is a function to define
        # the output charset. Before 2.4, the output charset is
        # identical with the translation file charset.
        try:
            self.set_output_charset(settings.DEFAULT_CHARSET)
        except AttributeError:
            pass
        self.django_output_charset = settings.DEFAULT_CHARSET
        self.__language = '??'

    def merge(self, other):
        self._catalog.update(other._catalog)
    
    def set_language(self, language):
        self.__language = language

    def language(self):
        return self.__language
    
    def __repr__(self):
        return "<DjangoTranslation lang:%s>" % self.__language


class DjangoTranslation23(DjangoTranslation):

    """
    This is a compatibility class that is only used with Python 2.3.
    The reason is, Python 2.3 doesn't support set_output_charset on
    translation objects and so needs this wrapper class to make sure
    that input charsets from translation files are correctly translated
    to output charsets.

    With a full switch to Python 2.4, this can be removed from the source.
    """

    def gettext(self, msgid):
        res = self.ugettext(msgid)
        return res.encode(self.django_output_charset)

    def ngettext(self, msgid1, msgid2, n):
        res = self.ungettext(msgid1, msgid2, n)
        return res.encode(self.django_output_charset)

def translation(language):
    """
    This function returns a translation object.  app must be the fully
    qualified name of the application.

    This translation object will be constructed out of multiple GNUTranslations
    objects by merging their catalogs. It will construct a object for the requested
    language and add a fallback to the default language, if that is different
    from the requested language.
    """
    global _translations

    t = _translations.get(language, None)
    if t is not None:
        return t
    
    from django.conf import settings

    # set up the right translation class
    klass = DjangoTranslation
    if sys.version_info < (2, 4):
        klass = DjangoTranslation23

    globalpath = os.path.join(os.path.dirname(settings.__file__), 'locale')

    parts = os.environ['DJANGO_SETTINGS_MODULE'].split('.')
    project = __import__(parts[0], {}, {}, [])
    projectpath = os.path.join(os.path.dirname(project.__file__), 'locale')

    def _fetch(lang, fallback=None):

        global _translations

        loc = to_locale(lang)

        res = _translations.get(lang, None)
        if res is not None:
            return res

        def _translation(path):
            try:
                t = gettext_module.translation('django', path, [loc], klass)
                t.set_language(lang)
                return t
            except IOError, e:
                return None
    
        res = _translation(globalpath)

        def _merge(path):
            t = _translation(path)
            if t is not None:
                if res is None:
                    return t
                else:
                    res.merge(t)
            return res

        if hasattr(settings, 'LOCALE_PATHS'):
            for localepath in settings.LOCALE_PATHS:
                if os.path.isdir(localepath):
                    res = _merge(localepath)

        if os.path.isdir(projectpath):
            res = _merge(projectpath)

        for appname in settings.INSTALLED_APPS:
            p = appname.rfind('.')
            if p >= 0:
                app = getattr(__import__(appname[:p], {}, {}, [appname[p+1:]]), appname[p+1:])
            else:
                app = __import__(appname, {}, {}, [])

            apppath = os.path.join(os.path.dirname(app.__file__), 'locale')

            if os.path.isdir(apppath):
                res = _merge(apppath)
  
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
    This function fetches the translation object for a given
    tuple of application name and language and installs it as
    the current translation object for the current thread.
    """
    _active[currentThread()] = translation(language)

def deactivate():
    """
    This function deinstalls the currently active translation
    object so that further _ calls will resolve against the
    default translation object, again.
    """
    global _active

    if _active.has_key(currentThread()):
        del _active[currentThread()]

def get_language():
    """
    This function returns the currently selected language.
    """
    t = _active.get(currentThread(), None)
    if t is not None:
        try:
            return to_language(t.language())
        except AttributeError:
            pass
    # if we don't have a real translation object, we assume
    # it's the default language.
    from django.conf.settings import LANGUAGE_CODE
    return LANGUAGE_CODE

def gettext(message):
    """
    This function will be patched into the builtins module to
    provide the _ helper function. It will use the current
    thread as a discriminator to find the translation object
    to use. If no current translation is activated, the
    message will be run through the default translation
    object.
    """
    global _default, _active

    t = _active.get(currentThread(), None)
    if t is not None:
        return t.gettext(message)
    if _default is None:
        from django.conf import settings
        _default = translation(settings.LANGUAGE_CODE)
    return _default.gettext(message)

def gettext_noop(message):
    """
    This function is used to just mark strings for translation
    but to not translate them now. This can be used to store
    strings in global variables that should stay in the base
    language (because they might be used externally) and will
    be translated later on.
    """
    return message

def ngettext(singular, plural, number):
    """
    This function returns the translation of either the singular
    or plural, based on the number.
    """
    global _default, _active

    t = _active.get(currentThread(), None)
    if t is not None:
        return t.ngettext(singular, plural, number)
    if _default is None:
        from django.conf import settings
        _default = translation('*', settings.LANGUAGE_CODE)
    return _default.ngettext(singular, plural, number)

gettext_lazy = lazy(gettext, str)
ngettext_lazy = lazy(ngettext, str)

def check_for_language(lang_code):
    """
    This function checks wether there is a global language
    file for the given language code. This is used to decide
    wether a user-provided language is available.
    """
    from django.conf import settings
    globalpath = os.path.join(os.path.dirname(settings.__file__), 'locale')
    if gettext_module.find('django', globalpath, [to_locale(lang_code)]) is not None:
        return True
    else:
        return False

def get_language_from_request(request):
    """
    analyze the request to find what language the user
    wants the system to show.
    """
    global _accepted

    from django.conf import settings
    globalpath = os.path.join(os.path.dirname(settings.__file__), 'locale')

    if hasattr(request, 'session'):
        lang_code = request.session.get('django_language', None)
        if lang_code is not None and check_for_language(lang_code):
            return lang_code
    
    lang_code = request.COOKIES.get('django_language', None)
    if lang_code is not None and check_for_language(lang_code):
        return lang_code
    
    accept = request.META.get('HTTP_ACCEPT_LANGUAGE', None)
    if accept is not None:

        t = _accepted.get(accept, None)
        if t is not None:
            return t

        def _parsed(el):
            p = el.find(';q=')
            if p >= 0:
                lang = el[:p].strip()
                order = int(float(el[p+3:].strip())*100)
            else:
                lang = el
                order = 100
            if lang.find('-') >= 0:
                (lang, sublang) = lang.split('-')
                lang = lang.lower() + '_' + sublang.upper()
            return (lang, order)

        langs = [_parsed(el) for el in accept.split(',')]
        langs.sort(lambda a,b: -1*cmp(a[1], b[1]))

        for lang, order in langs:
            langfile = gettext_module.find('django', globalpath, [to_locale(lang)])
            if langfile:
                # reconstruct the actual language from the language
                # filename, because otherwise we might incorrectly
                # report de_DE if we only have de available, but
                # did find de_DE because of language normalization
                lang = langfile[len(globalpath):].split('/')[1]
                _accepted[accept] = lang
                return lang
    
    return settings.LANGUAGE_CODE

def install():
    """
    This installs the gettext function as the default
    translation function under the name _.
    """
    __builtins__['_'] = gettext


dot_re = re.compile(r'\S')
def blankout(src, char):
    """
    This is used in the templateize function and changes every
    non-whitespace character to the given char.
    """
    return dot_re.sub(char, src)

inline_re = re.compile(r"""^\s*trans\s+((?:".*?")|(?:'.*?'))\s*""")
block_re = re.compile(r"""^\s*blocktrans(?:\s+|$)""")
endblock_re = re.compile(r"""^\s*endblocktrans$""")
plural_re = re.compile(r"""^\s*plural$""")
constant_re = re.compile(r"""_\(((?:".*?")|(?:'.*?'))\)""")
def templateize(src):
    from django.core.template import Lexer, TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK
    """
    This function turns a django template into something that is
    understood by xgettext. It does so by translating the django
    translation tags into standard gettext function invocations.
    """
    out = StringIO()
    intrans = False
    inplural = False
    singular = []
    plural = []
    for t in Lexer(src, None).tokenize():
        if intrans:
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
                    raise SyntaxError, "translation blocks must not include other block tags: %s" % t.contents
            elif t.token_type == TOKEN_VAR:
                if inplural:
                    plural.append('%%(%s)s' % t.contents)
                else:
                    singular.append('%%(%s)s' % t.contents)
            elif t.token_type == TOKEN_TEXT:
                if inplural:
                    plural.append(t.contents)
                else:
                    singular.append(t.contents)
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
                    intrans = True
                    inplural = False
                    singular = []
                    plural = []
                elif cmatches:
                    for cmatch in cmatches:
                        out.write(' _(%s) ' % cmatch)
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
            else:
                out.write(blankout(t.contents, 'X'))
    return out.getvalue()

