"translation helper functions"

import os
import sys
import gettext as gettext_module

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
        self.__app = '?.?.?'
        self.__language = '??'
    
    def set_app_and_language(self, app, language):
        self.__app = app
        self.__language = language

    def language(self):
        return self.__language
    
    def __repr__(self):
        return "<DjangoTranslation app:%s lang:%s>" % (self.__app, self.__language)


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
        res = DjangoTranslation.gettext(self, msgid)
        if self.charset() != self.django_output_charset:
            res = res.decode(self.charset()).encode(self.django_output_charset)
        return res

    def ngettext(self, msgid1, msgid2, n):
        res = DjangoTranslation.ngettext(self, msgid1, msgid2, n)
        if self.charset() != self.django_output_charset:
            res = res.decode(self.charset()).encode(self.django_output_charset)
        return res

def translation(appname, language):
    """
    This function returns a translation object.
    app must be the fully qualified name of the
    application.

    This function will first look into the app
    messages directory for the django message file,
    then in the project messages directory for the
    django message file and last in the global
    messages directory for the django message file.
    """

    t = _translations.get((appname, language), None)
    if t is not None:
        return t
    
    from django.conf import settings

    # set up the right translation class
    klass = DjangoTranslation
    if sys.version_info < (2, 4):
        klass = DjangoTranslation23

    globalpath = os.path.join(os.path.dirname(settings.__file__), 'locale')

    try:
        t = gettext_module.translation('django', globalpath, [language, settings.LANGUAGE_CODE], klass)
        t.set_app_and_language(appname, language)
    except IOError: t = gettext_module.NullTranslations()
    _translations[(appname, language)] = t

    if hasattr(settings, 'LOCALE_PATHS'):
        for localepath in settings.LOCALE_PATHS:
            try:
                t = gettext_module.translation('django', localepath, [language, settings.LANGUAGE_CODE], klass)
                t.set_app_and_language(appname, language)
            except IOError: t = None
            if t is not None:
                t.add_fallback(_translations[(appname, language)])
                _translations[(appname, language)] = t

    parts = os.environ['DJANGO_SETTINGS_MODULE'].split('.')
    project = __import__(parts[0], {}, {}, [])

    projectpath = os.path.join(os.path.dirname(project.__file__), 'locale')

    try:
        t = gettext_module.translation('django', projectpath, [language, settings.LANGUAGE_CODE], klass)
        t.set_app_and_language(appname, language)
    except IOError: t = None
    if t is not None:
        t.add_fallback(_translations[(appname, language)])
        _translations[(appname, language)] = t

    if appname != '*':
        app = __import__(appname, {}, {}, ['views'])

        apppath = os.path.join(os.path.dirname(app.__file__), 'locale')

        try:
            t = gettext_module.translation('django', apppath, [language, settings.LANGUAGE_CODE], klass)
            t.set_app_and_language(appname, language)
        except IOError: t = None
        if t is not None:
            t.add_fallback(_translations[(appname, language)])
            _translations[(appname, language)] = t

    return _translations[(appname, language)]

def activate(appname, language):
    """
    This function fetches the translation object for a given
    tuple of application name and language and installs it as
    the current translation object for the current thread.
    """
    t = translation(appname, language)
    _active[currentThread()] = t

def deactivate():
    """
    This function deinstalls the currently active translation
    object so that further _ calls will resolve against the
    default translation object, again.
    """
    del _active[currentThread()]

def get_language():
    """
    This function returns the currently selected language.
    """
    t = _active.get(currentThread(), None)
    if t is not None:
        try:
            return t.language()
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
        _default = translation('*', settings.LANGUAGE_CODE)
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

def get_language_from_request(request):
    """
    analyze the request to find what language the user
    wants the system to show.
    """
    global _accepted

    from django.conf import settings
    globalpath = os.path.join(os.path.dirname(settings.__file__), 'locale')

    if request.GET or request.POST:
        lang_code = request.GET.get('django_language', None) or request.POST.get('django_language', None)
        if lang_code is not None:
            lang = gettext_module.find('django', globalpath, [lang_code])
            if lang is not None:
                if hasattr(request, 'session'):
                    request.session['django_language'] = lang_code
                else:
                    request.set_cookie('django_language', lang_code)
                return lang_code

    if hasattr(request, 'session'):
        lang_code = request.session.get('django_language', None)
        if lang_code is not None:
            lang = gettext_module.find('django', globalpath, [lang_code])
            if lang is not None:
                return lang_code
    
    lang_code = request.COOKIES.get('django_language', None)
    if lang_code is not None:
        lang = gettext_module.find('django', globalpath, [lang_code])
        if lang is not None:
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
            if lang == 'en' or lang.startswith('en_'):
                # special casing for language en and derivates, because we don't
                # have an english language file available, but just fallback
                # to NullTranslation on those languages (as the source itself
                # is in english)
                _accepted[accept] = lang
                return lang
            else:
                langfile = gettext_module.find('django', globalpath, [lang])
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

