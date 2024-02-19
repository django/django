"""Locale utilities."""

from __future__ import annotations

import locale
from gettext import NullTranslations, translation
from os import path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, Callable


class _TranslationProxy:
    """
    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting.
    """
    __slots__ = '_catalogue', '_namespace', '_message'

    def __init__(self, catalogue: str, namespace: str, message: str) -> None:
        self._catalogue = catalogue
        self._namespace = namespace
        self._message = message

    def __str__(self) -> str:
        try:
            return translators[self._namespace, self._catalogue].gettext(self._message)
        except KeyError:
            # NullTranslations().gettext(self._message) == self._message
            return self._message

    def __dir__(self) -> list[str]:
        return dir(str)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.__str__(), name)

    def __getstate__(self) -> tuple[str, str, str]:
        return self._catalogue, self._namespace, self._message

    def __setstate__(self, tup: tuple[str, str, str]) -> None:
        self._catalogue, self._namespace, self._message = tup

    def __copy__(self) -> _TranslationProxy:
        return _TranslationProxy(self._catalogue, self._namespace, self._message)

    def __repr__(self) -> str:
        try:
            return f'i{self.__str__()!r}'
        except Exception:
            return (self.__class__.__name__
                    + f'({self._catalogue}, {self._namespace}, {self._message})')

    def __add__(self, other: str) -> str:
        return self.__str__() + other

    def __radd__(self, other: str) -> str:
        return other + self.__str__()

    def __mod__(self, other: str) -> str:
        return self.__str__() % other

    def __rmod__(self, other: str) -> str:
        return other % self.__str__()

    def __mul__(self, other: Any) -> str:
        return self.__str__() * other

    def __rmul__(self, other: Any) -> str:
        return other * self.__str__()

    def __hash__(self):
        return hash(self.__str__())

    def __eq__(self, other):
        return self.__str__() == other

    def __lt__(self, string):
        return self.__str__() < string

    def __contains__(self, char):
        return char in self.__str__()

    def __len__(self):
        return len(self.__str__())

    def __getitem__(self, index):
        return self.__str__()[index]


translators: dict[tuple[str, str], NullTranslations] = {}


def init(
    locale_dirs: Iterable[str | None],
    language: str | None,
    catalog: str = 'sphinx',
    namespace: str = 'general',
) -> tuple[NullTranslations, bool]:
    """Look for message catalogs in `locale_dirs` and *ensure* that there is at
    least a NullTranslations catalog set in `translators`. If called multiple
    times or if several ``.mo`` files are found, their contents are merged
    together (thus making ``init`` reentrant).
    """
    translator = translators.get((namespace, catalog))
    # ignore previously failed attempts to find message catalogs
    if translator.__class__ is NullTranslations:
        translator = None

    if language:
        if '_' in language:
            # for language having country code (like "de_AT")
            languages: list[str] | None = [language, language.split('_')[0]]
        else:
            languages = [language]
    else:
        languages = None

    # loading
    # the None entry is the system's default locale path
    for dir_ in locale_dirs:
        try:
            trans = translation(catalog, localedir=dir_, languages=languages)
            if translator is None:
                translator = trans
            else:
                translator.add_fallback(trans)
        except Exception:
            # Language couldn't be found in the specified path
            pass
    if translator is not None:
        has_translation = True
    else:
        translator = NullTranslations()
        has_translation = False
    # guarantee translators[(namespace, catalog)] exists
    translators[namespace, catalog] = translator
    return translator, has_translation


_LOCALE_DIR = path.abspath(path.dirname(__file__))


def init_console(
    locale_dir: str | None = None,
    catalog: str = 'sphinx',
) -> tuple[NullTranslations, bool]:
    """Initialize locale for console.

    .. versionadded:: 1.8
    """
    if locale_dir is None:
        locale_dir = _LOCALE_DIR
    try:
        # encoding is ignored
        language, _ = locale.getlocale(locale.LC_MESSAGES)
    except AttributeError:
        # LC_MESSAGES is not always defined. Fallback to the default language
        # in case it is not.
        language = None
    return init([locale_dir], language, catalog, 'console')


def get_translator(catalog: str = 'sphinx', namespace: str = 'general') -> NullTranslations:
    return translators.get((namespace, catalog), NullTranslations())


def is_translator_registered(catalog: str = 'sphinx', namespace: str = 'general') -> bool:
    return (namespace, catalog) in translators


def get_translation(catalog: str, namespace: str = 'general') -> Callable[[str], str]:
    """Get a translation function based on the *catalog* and *namespace*.

    The extension can use this API to translate the messages on the
    extension::

        import os
        from sphinx.locale import get_translation

        MESSAGE_CATALOG_NAME = 'myextension'  # name of *.pot, *.po and *.mo files
        _ = get_translation(MESSAGE_CATALOG_NAME)
        text = _('Hello Sphinx!')


        def setup(app):
            package_dir = os.path.abspath(os.path.dirname(__file__))
            locale_dir = os.path.join(package_dir, 'locales')
            app.add_message_catalog(MESSAGE_CATALOG_NAME, locale_dir)

    With this code, sphinx searches a message catalog from
    ``${package_dir}/locales/${language}/LC_MESSAGES/myextension.mo``.
    The :confval:`language` is used for the searching.

    .. versionadded:: 1.8
    """
    def gettext(message: str) -> str:
        if not is_translator_registered(catalog, namespace):
            # not initialized yet
            return _TranslationProxy(catalog, namespace, message)  # type: ignore[return-value]  # noqa: E501
        else:
            translator = get_translator(catalog, namespace)
            return translator.gettext(message)

    return gettext


# A shortcut for sphinx-core
#: Translation function for messages on documentation (menu, labels, themes and so on).
#: This function follows :confval:`language` setting.
_ = get_translation('sphinx')
#: Translation function for console messages
#: This function follows locale setting (`LC_ALL`, `LC_MESSAGES` and so on).
__ = get_translation('sphinx', 'console')


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
}
