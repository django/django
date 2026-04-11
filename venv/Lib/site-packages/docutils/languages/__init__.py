# $Id: __init__.py 10046 2025-03-09 01:45:28Z aa-turner $
# Author: David Goodger <goodger@python.org>
# Copyright: This module has been placed in the public domain.

# Internationalization details are documented in
# <https://docutils.sourceforge.io/docs/howto/i18n.html>.

"""
This package contains modules for language-dependent features of Docutils.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from importlib import import_module

from docutils.utils import normalize_language_tag

TYPE_CHECKING = False
if TYPE_CHECKING:
    import types
    from typing import NoReturn, Protocol, TypeVar, overload

    from docutils.utils import Reporter

    class LanguageModule(Protocol):
        __name__: str

        labels: dict[str, str]
        bibliographic_fields: dict[str, str]
        author_separators: list[str]

    LanguageModuleT = TypeVar('LanguageModuleT')
else:
    from docutils.utils._typing import overload


class LanguageImporter:
    """Import language modules.

    When called with a BCP 47 language tag, instances return a module
    with localisations from `docutils.languages` or the PYTHONPATH.

    If there is no matching module, warn (if a `reporter` is passed)
    and fall back to English.
    """
    packages = ('docutils.languages.', '')
    warn_msg = ('Language "%s" not supported: '
                'Docutils-generated text will be in English.')
    fallback = 'en'
    # TODO: use a dummy module returning empty strings?, configurable?

    def __init__(self) -> None:
        self.cache: dict[str, LanguageModuleT] = {}

    def import_from_packages(self, name: str, reporter: Reporter = None
                             ) -> LanguageModuleT:
        """Try loading module `name` from `self.packages`."""
        module = None
        for package in self.packages:
            try:
                module = import_module(package + name)
                self.check_content(module)
            except (ImportError, AttributeError):
                if reporter and module:
                    reporter.info(f'{module} is no complete '
                                  'Docutils language module.')
                elif reporter:
                    reporter.info(f'Module "{package+name}" not found.')
                continue
            break
        return module

    @overload
    def check_content(self, module: LanguageModule) -> None:
        ...

    @overload
    def check_content(self, module: types.ModuleType) -> NoReturn:
        ...

    def check_content(self, module: LanguageModule | types.ModuleType) -> None:
        """Check if we got a Docutils language module."""
        if not (
            isinstance(module.labels, dict)
            and isinstance(module.bibliographic_fields, dict)
            and isinstance(module.author_separators, list)
        ):
            raise ImportError

    def __call__(self, language_code: str, reporter: Reporter = None
                 ) -> LanguageModuleT:
        try:
            return self.cache[language_code]
        except KeyError:
            pass
        for tag in normalize_language_tag(language_code):
            tag = tag.replace('-', '_')  # '-' not valid in module names
            module = self.import_from_packages(tag, reporter)
            if module is not None:
                break
        else:
            if reporter:
                reporter.warning(self.warn_msg % language_code)
            if self.fallback:
                module = self.import_from_packages(self.fallback)
        if reporter and (language_code != 'en'):
            reporter.info(f'Using {module} for language "{language_code}".')
        self.cache[language_code] = module
        return module

    def __class_getitem__(cls, name):
        return cls


get_language: LanguageImporter[LanguageModule] = LanguageImporter()
