# -*- coding: utf-8 -*-
"""
    sphinx.locale
    ~~~~~~~~~~~~~

    Locale utilities.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import gettext
import locale
import warnings
from collections import defaultdict
from gettext import NullTranslations

from six import text_type
from six.moves import UserString

from sphinx.deprecation import RemovedInSphinx30Warning

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterable, Iterator, List, Tuple, Union  # NOQA


class _TranslationProxy(UserString, object):
    """
    Class for proxy strings from gettext translations.  This is a helper for the
    lazy_* functions from this module.

    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting.

    This inherits from UserString because some docutils versions use UserString
    for their Text nodes, which then checks its argument for being either a
    basestring or UserString, otherwise calls str() -- not unicode() -- on it.
    This also inherits from object to make the __new__ method work.
    """
    __slots__ = ('_func', '_args')

    def __new__(cls, func, *args):
        # type: (Callable, unicode) -> object
        if not args:
            # not called with "function" and "arguments", but a plain string
            return text_type(func)
        return object.__new__(cls)

    def __getnewargs__(self):
        # type: () -> Tuple
        return (self._func,) + self._args  # type: ignore

    def __init__(self, func, *args):
        # type: (Callable, unicode) -> None
        self._func = func
        self._args = args

    @property
    def data(self):  # type: ignore
        # type: () -> unicode
        return self._func(*self._args)

    # replace function from UserString; it instantiates a self.__class__
    # for the encoding result

    def encode(self, encoding=None, errors=None):  # type: ignore
        # type: (unicode, unicode) -> str
        if encoding:
            if errors:
                return self.data.encode(encoding, errors)
            else:
                return self.data.encode(encoding)
        else:
            return self.data.encode()

    def __contains__(self, key):
        # type: (Any) -> bool
        return key in self.data

    def __bool__(self):
        # type: () -> bool
        return bool(self.data)
    __nonzero__ = __bool__  # for python2 compatibility

    def __dir__(self):
        # type: () -> List[str]
        return dir(text_type)

    def __iter__(self):
        # type: () -> Iterator
        return iter(self.data)

    def __len__(self):
        # type: () -> int
        return len(self.data)

    def __str__(self):
        # type: () -> str
        return str(self.data)

    def __unicode__(self):
        # type: () -> unicode
        return text_type(self.data)

    def __add__(self, other):  # type: ignore
        # type: (unicode) -> unicode
        return self.data + other

    def __radd__(self, other):  # type: ignore
        # type: (unicode) -> unicode
        return other + self.data

    def __mod__(self, other):  # type: ignore
        # type: (unicode) -> unicode
        return self.data % other

    def __rmod__(self, other):
        # type: (unicode) -> unicode
        return other % self.data

    def __mul__(self, other):  # type: ignore
        # type: (Any) -> unicode
        return self.data * other

    def __rmul__(self, other):  # type: ignore
        # type: (Any) -> unicode
        return other * self.data

    def __lt__(self, other):
        # type: (unicode) -> bool
        return self.data < other

    def __le__(self, other):
        # type: (unicode) -> bool
        return self.data <= other

    def __eq__(self, other):
        # type: (Any) -> bool
        return self.data == other

    def __ne__(self, other):
        # type: (Any) -> bool
        return self.data != other

    def __gt__(self, other):
        # type: (unicode) -> bool
        return self.data > other

    def __ge__(self, other):
        # type: (unicode) -> bool
        return self.data >= other

    def __getattr__(self, name):
        # type: (unicode) -> Any
        if name == '__members__':
            return self.__dir__()
        return getattr(self.data, name)

    def __getstate__(self):
        # type: () -> Tuple[Callable, Tuple[unicode, ...]]
        return self._func, self._args

    def __setstate__(self, tup):
        # type: (Tuple[Callable, Tuple[unicode]]) -> None
        self._func, self._args = tup

    def __getitem__(self, key):  # type: ignore
        # type: (Any) -> unicode
        return self.data[key]

    def __copy__(self):
        # type: () -> _TranslationProxy
        return self

    def __repr__(self):
        # type: () -> str
        try:
            return 'i' + repr(text_type(self.data))
        except Exception:
            return '<%s broken>' % self.__class__.__name__


def mygettext(string):
    # type: (unicode) -> unicode
    """Used instead of _ when creating TranslationProxies, because _ is
    not bound yet at that time.
    """
    warnings.warn('sphinx.locale.mygettext() is deprecated.  Please use `_()` instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return _(string)


def lazy_gettext(string):
    # type: (unicode) -> unicode
    """A lazy version of `gettext`."""
    # if isinstance(string, _TranslationProxy):
    #     return string
    warnings.warn('sphinx.locale.laxy_gettext() is deprecated.  Please use `_()` instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return _TranslationProxy(mygettext, string)  # type: ignore


translators = defaultdict(NullTranslations)  # type: Dict[Tuple[unicode, unicode], NullTranslations]  # NOQA


def init(locale_dirs, language, catalog='sphinx', namespace='general'):
    # type: (List[unicode], unicode, unicode, unicode) -> Tuple[NullTranslations, bool]
    """Look for message catalogs in `locale_dirs` and *ensure* that there is at
    least a NullTranslations catalog set in `translators`.  If called multiple
    times or if several ``.mo`` files are found, their contents are merged
    together (thus making ``init`` reentrant).
    """
    global translators
    translator = translators.get((namespace, catalog))
    # ignore previously failed attempts to find message catalogs
    if translator.__class__ is NullTranslations:
        translator = None
    # the None entry is the system's default locale path
    has_translation = True

    if language and '_' in language:
        # for language having country code (like "de_AT")
        languages = [language, language.split('_')[0]]
    else:
        languages = [language]

    # loading
    for dir_ in locale_dirs:
        try:
            trans = gettext.translation(catalog, localedir=dir_,  # type: ignore
                                        languages=languages)
            if translator is None:
                translator = trans
            else:
                translator.add_fallback(trans)
        except Exception:
            # Language couldn't be found in the specified path
            pass
    # guarantee translators[(namespace, catalog)] exists
    if translator is None:
        translator = NullTranslations()
        has_translation = False
    translators[(namespace, catalog)] = translator
    if hasattr(translator, 'ugettext'):
        translator.gettext = translator.ugettext  # type: ignore
    return translator, has_translation


def setlocale(category, value=None):
    # type: (int, Union[str, Iterable[str]]) -> None
    """Update locale settings.

    This does not throw any exception even if update fails.
    This is workaround for Python's bug.

    For more details:

    * https://github.com/sphinx-doc/sphinx/issues/5724
    * https://bugs.python.org/issue18378#msg215215

    .. note:: Only for internal use.  Please don't call this method from extensions.
              This will be removed in future.
    """
    try:
        locale.setlocale(category, value)
    except locale.Error:
        pass


def init_console(locale_dir, catalog):
    # type: (unicode, unicode) -> Tuple[NullTranslations, bool]
    """Initialize locale for console.

    .. versionadded:: 1.8
    """
    try:
        # encoding is ignored
        language, _ = locale.getlocale(locale.LC_MESSAGES)
    except AttributeError:
        # LC_MESSAGES is not always defined. Fallback to the default language
        # in case it is not.
        language = None
    return init([locale_dir], language, catalog, 'console')


def get_translator(catalog='sphinx', namespace='general'):
    # type: (unicode, unicode) -> NullTranslations
    return translators[(namespace, catalog)]


def is_translator_registered(catalog='sphinx', namespace='general'):
    # type: (unicode, unicode) -> bool
    return (namespace, catalog) in translators


def _lazy_translate(catalog, namespace, message):
    # type: (unicode, unicode, unicode) -> unicode
    """Used instead of _ when creating TranslationProxy, because _ is
    not bound yet at that time.
    """
    translator = get_translator(catalog, namespace)
    return translator.gettext(message)  # type: ignore


def get_translation(catalog, namespace='general'):
    """Get a translation function based on the *catalog* and *namespace*.

    The extension can use this API to translate the messages on the
    extension::

        import os
        from sphinx.locale import get_translation

        _ = get_translation(__name__)
        text = _('Hello Sphinx!')


        def setup(app):
            package_dir = path.abspath(path.dirname(__file__))
            locale_dir = os.path.join(package_dir, 'locales')
            app.add_message_catalog(__name__, locale_dir)

    With this code, sphinx searches a message catalog from
    ``${package_dir}/locales/${language}/LC_MESSAGES/${__name__}.mo``
    The :confval:`language` is used for the searching.

    .. versionadded:: 1.8
    """
    def gettext(message, *args):
        # type: (unicode, *Any) -> unicode
        if not is_translator_registered(catalog, namespace):
            # not initialized yet
            return _TranslationProxy(_lazy_translate, catalog, namespace, message)  # type: ignore  # NOQA
        else:
            translator = get_translator(catalog, namespace)
            if len(args) <= 1:
                return translator.gettext(message)  # type: ignore
            else:  # support pluralization
                return translator.ngettext(message, args[0], args[1])  # type: ignore

    return gettext


# A shortcut for sphinx-core
#: Translation function for messages on documentation (menu, labels, themes and so on).
#: This function follows :confval:`language` setting.
_ = get_translation('sphinx')
#: Translation function for console messages
#: This function follows locale setting (`LC_ALL`, `LC_MESSAGES` and so on).
__ = get_translation('sphinx', 'console')


def l_(*args):
    warnings.warn('sphinx.locale.l_() is deprecated.  Please use `_()` instead.',
                  RemovedInSphinx30Warning, stacklevel=2)
    return _(*args)


# labels
admonitionlabels = {
    'attention': _('Attention'),
    'caution':   _('Caution'),
    'danger':    _('Danger'),
    'error':     _('Error'),
    'hint':      _('Hint'),
    'important': _('Important'),
    'note':      _('Note'),
    'seealso':   _('See also'),
    'tip':       _('Tip'),
    'warning':   _('Warning'),
}  # type: Dict[unicode, unicode]

# Moved to sphinx.directives.other (will be overridden later)
versionlabels = {}  # type: Dict[unicode, unicode]

# Moved to sphinx.domains.python (will be overridden later)
pairindextypes = {}  # type: Dict[unicode, unicode]
